import gc
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import database


class KanbanDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = database.DB_PATH
        database.DB_PATH = os.path.join(self.temp.name, "board.db")
        database.init_db()
        self.project = database.create_project("界面改版")
        self.section = database.add_section(self.project, "设计")
        self.card = database.add_card(self.section, "看板样式")

    def tearDown(self):
        database.DB_PATH = self.old_path
        gc.collect()
        self.temp.cleanup()

    def card_row(self):
        return next(c for c in database.list_cards(self.project) if c["id"] == self.card)

    def test_done_time_is_recorded_preserved_cleared_and_recorded_again(self):
        self.assertIn("done_at", self.card_row().keys())
        self.assertIsNone(self.card_row()["done_at"])
        with patch.object(database, "datetime_now", return_value="2026-10-28T11:02:03"):
            database.set_card_status(self.card, database.STATUS_DONE)
        self.assertEqual(self.card_row()["done_at"], "2026-10-28T11:02:03")
        with patch.object(database, "datetime_now", return_value="2026-10-28T11:05:00"):
            database.set_card_status(self.card, database.STATUS_DONE)
            database.update_card(self.card, title="新标题")
        self.assertEqual(self.card_row()["done_at"], "2026-10-28T11:02:03")
        database.init_db()
        self.assertEqual(self.card_row()["done_at"], "2026-10-28T11:02:03")
        for status in (database.STATUS_TODO, database.STATUS_DOING):
            database.set_card_status(self.card, status)
            self.assertIsNone(self.card_row()["done_at"])
            with patch.object(database, "datetime_now", return_value="2026-10-28T12:00:01"):
                database.set_card_status(self.card, database.STATUS_DONE)
            self.assertEqual(self.card_row()["done_at"], "2026-10-28T12:00:01")

    def test_existing_schema_migrates_without_inventing_completion_times(self):
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("DROP TABLE cards")
            conn.execute("CREATE TABLE cards (id INTEGER PRIMARY KEY, section_id INTEGER, "
                         "title TEXT, note TEXT DEFAULT '', status INTEGER DEFAULT 0, "
                         "priority INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT)")
            conn.execute("INSERT INTO cards (id, section_id, title, status) VALUES (1, ?, '旧任务', 2)",
                         (self.section,))
        database.init_db()
        database.init_db()
        row = database.list_cards(self.project)[0]
        self.assertIn("done_at", row.keys())
        self.assertIsNone(row["done_at"])
        self.assertEqual(json.loads(row["tags"]), [])
        self.assertIsNone(row["archived_at"])
        self.assertTrue(database.archive_card(row["id"]))
        self.assertIsNone(database.list_cards(self.project, archived=True)[0]["done_at"])

    def test_search_filter_sort_and_all_project_scope(self):
        database.update_card(self.card, tags="UI, 重要, UI", priority=database.PRIORITY_HIGH)
        other = database.add_card(self.section, "修正文档", note="Layout review", tags=["文档"])
        self.assertEqual(json.loads(self.card_row()["tags"]), ["UI", "重要"])
        self.assertEqual([c["id"] for c in database.list_cards(self.project, search="layout")], [other])
        self.assertEqual([c["id"] for c in database.list_cards(self.project, tag="ui")], [self.card])
        self.assertEqual(len(database.list_cards(self.project, search="设计")), 2)
        self.assertEqual(len(database.list_cards(self.project, priority=database.PRIORITY_LOW)), 0)
        default_section = database.add_section(1, "个人")
        cross = database.add_card(default_section, "跨项目搜索目标")
        self.assertEqual([c["id"] for c in database.list_cards(None, search="跨项目")], [cross])
        self.assertEqual(database.list_cards(self.project)[0]["id"], self.card)
        self.assertEqual(database.list_cards(self.project, sort="created")[0]["id"], other)
        self.assertEqual(database.list_tags(self.project), ["UI", "文档", "重要"])

    def test_create_directly_in_done_and_update_category(self):
        with patch.object(database, "datetime_now", return_value="2026-10-28T12:30:01"):
            card = database.add_card(self.section, "已交付", status=database.STATUS_DONE)
        row = next(c for c in database.list_cards(self.project) if c["id"] == card)
        self.assertEqual(row["done_at"], "2026-10-28T12:30:01")
        target = database.add_section(self.project, "开发")
        database.update_card(self.card, section_id=target)
        self.assertEqual(self.card_row()["section_name"], "开发")

    def test_theme_setting_survives_database_initialization(self):
        self.assertEqual(database.get_settings().get("ui_theme"), "dark")
        database.save_settings({"ui_theme": "light"})
        database.init_db()
        self.assertEqual(database.get_settings()["ui_theme"], "light")

    def test_only_done_cards_archive_and_keep_completion_steps_and_tags(self):
        for status in (database.STATUS_TODO, database.STATUS_DOING):
            database.set_card_status(self.card, status)
            self.assertFalse(database.archive_card(self.card))
        step = database.add_item(self.card, "保留的步骤")
        database.set_item_status(step, database.STATUS_DONE)
        database.update_card(self.card, tags=["归档专属"])
        with patch.object(database, "datetime_now", return_value="2026-10-29T09:45:57"):
            database.set_card_status(self.card, database.STATUS_DONE)
        with patch.object(database, "datetime_now", return_value="2026-10-29T12:00:00"):
            self.assertTrue(database.archive_card(self.card))
        self.assertFalse(database.archive_card(self.card))
        self.assertFalse(database.archive_card(-1))
        self.assertEqual(database.list_cards(self.project), [])
        self.assertEqual(database.list_tags(self.project), [])
        archived = database.list_cards(self.project, archived=True)[0]
        self.assertEqual(archived["done_at"], "2026-10-29T09:45:57")
        self.assertEqual(archived["archived_at"], "2026-10-29T12:00:00")
        self.assertEqual(database.list_items(self.card)[0]["content"], "保留的步骤")
        self.assertEqual(database.list_tags(self.project, archived=True), ["归档专属"])
        database.init_db()
        self.assertEqual(len(database.list_cards(None, archived=True)), 1)

    def test_bulk_archive_covers_all_sections_but_only_done_in_selected_project(self):
        database.set_card_status(self.card, database.STATUS_DONE)
        second = database.add_section(self.project, "开发")
        done = database.add_card(second, "完成二", status=database.STATUS_DONE, tags=["交付"])
        doing = database.add_card(second, "正在做", status=database.STATUS_DOING)
        other_section = database.add_section(1, "个人")
        other = database.add_card(other_section, "其他项目已完成", status=database.STATUS_DONE)
        self.assertEqual(database.archive_done_cards(self.project), 2)
        self.assertEqual(database.archive_done_cards(self.project), 0)
        self.assertEqual([c["id"] for c in database.list_cards(self.project)], [doing])
        self.assertEqual([c["id"] for c in database.list_cards(1)], [other])
        self.assertEqual([c["id"] for c in database.list_cards(None, archived=True,
                         search="完成二", tag="交付", priority=1)], [done])

    def test_archived_cards_resist_stale_editor_and_drop_changes_then_delete_cascades(self):
        step = database.add_item(self.card, "冻结的步骤")
        database.set_card_status(self.card, database.STATUS_DONE)
        database.archive_card(self.card)
        before = dict(database.list_cards(self.project, archived=True)[0])
        database.update_card(self.card, title="不应保存", section_id=database.add_section(1, "其他"))
        database.set_card_status(self.card, database.STATUS_TODO)
        database.add_item(self.card, "不应添加")
        database.set_item_status(step, database.STATUS_DONE)
        database.set_item_priority(step, database.PRIORITY_HIGH)
        database.delete_item(step)
        self.assertEqual(dict(database.list_cards(self.project, archived=True)[0]), before)
        items = database.list_items(self.card)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], 0)
        self.assertEqual(items[0]["priority"], 1)
        database.delete_card(self.card)
        self.assertEqual(database.list_cards(None, archived=True), [])
        self.assertEqual(database.list_items(self.card), [])


if __name__ == "__main__":
    unittest.main()
