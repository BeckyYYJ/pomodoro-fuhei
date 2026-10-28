"""Run with .venv/Scripts/python.exe -m unittest test_ui -v."""
import gc
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QMimeData, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFontDatabase, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

import database
from ui_board import BoardWidget, CardFrame, CARD_MIME
from ui_card_dialog import CardDialog
from ui_main import MainWindow
from ui_theme import apply_theme, palette_for

APP = QApplication.instance() or QApplication([])
APP.setStyle("Fusion")
# The offscreen platform doesn't discover Windows fonts automatically.
for font in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "consola.ttf"):
    path = Path("C:/Windows/Fonts") / font
    if path.exists():
        QFontDatabase.addApplicationFont(str(path))


class KanbanUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.previous_path = database.DB_PATH
        database.DB_PATH = str(Path(self.temp.name) / "ui.db")
        database.init_db()
        self.pid = database.create_project("项目界面")
        self.sid = database.add_section(self.pid, "设计")
        self.card_id = database.add_card(self.sid, "界面任务", tags=["UI"])
        self.board = BoardWidget()
        self.board.set_locked_project(self.pid)
        self.board.resize(1050, 700)
        self.board.show()
        APP.processEvents()

    def tearDown(self):
        for widget in APP.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        APP.processEvents()
        database.DB_PATH = self.previous_path
        gc.collect()
        self.temp.cleanup()

    def card(self):
        return next(c for c in database.list_cards(self.pid) if c["id"] == self.card_id)

    def test_real_drop_event_records_and_clears_time(self):
        mime = QMimeData()
        mime.setData(CARD_MIME, str(self.card_id).encode())
        for status in (database.STATUS_DONE, database.STATUS_TODO, database.STATUS_DONE):
            target = self.board._columns[status]
            enter = QDragEnterEvent(target.rect().center(), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
            APP.sendEvent(target, enter)
            drop = QDropEvent(QPointF(target.rect().center()), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
            APP.sendEvent(target, drop)
            QTest.qWait(1)
            self.assertEqual(self.card()["status"], status)
            self.assertEqual(bool(self.card()["done_at"]), status == database.STATUS_DONE)
        labels = [l.text() for l in self.board._columns[2].findChildren(QLabel)]
        self.assertTrue(any("完成于 " in text and ":" in text for text in labels))

    def test_card_click_and_keyboard_open(self):
        frame = CardFrame(self.card())
        frame.resize(300, 160)
        frame.show()
        opened = []
        frame.opened.connect(opened.append)
        QTest.mouseClick(frame, Qt.LeftButton)
        QTest.keyClick(frame, Qt.Key_Return)
        self.assertEqual(opened, [self.card_id, self.card_id])

    def test_dialog_create_steps_tags_and_edit(self):
        dialog = CardDialog(project_id=self.pid, status=database.STATUS_DONE)
        dialog._title.setText("新任务")
        dialog._tags.setText("设计, 文档")
        dialog._step_input.setText("确认内容")
        dialog._add_step()
        created = dialog.save_card()
        row = next(c for c in database.list_cards(self.pid) if c["id"] == created)
        self.assertEqual(database.card_tags(row), ["设计", "文档"])
        self.assertEqual(row["total"], 1)
        self.assertIsNotNone(row["done_at"])
        editing = CardDialog(row)
        editing._steps[0]["status"] = database.STATUS_DONE
        editing._note.setPlainText("编辑后的说明")
        editing.save_card()
        row_after = next(c for c in database.list_cards(self.pid) if c["id"] == created)
        self.assertEqual(row_after["done"], 1)
        self.assertEqual(row_after["done_at"], row["done_at"])

    def test_cancel_does_not_change_card_or_steps(self):
        item = database.add_item(self.card_id, "原步骤")
        dialog = CardDialog(self.card())
        dialog._title.setText("不应保存")
        dialog._remove_step(dialog._steps[0])
        dialog.reject()
        self.assertEqual(self.card()["title"], "界面任务")
        self.assertEqual(database.list_items(self.card_id)[0]["id"], item)

    def test_first_card_in_empty_project_creates_category_only_on_save(self):
        dialog = CardDialog(project_id=1)
        dialog._title.setText("未分类任务")
        self.assertEqual(database.list_sections(1), [])
        dialog.save_card()
        self.assertEqual(database.list_sections(1)[0]["name"], "未分类")

    def test_board_add_and_open_actions_save_dialog(self):
        def fill(dialog):
            dialog._title.setText("直接从列新增")
            return 1
        with patch.object(CardDialog, "exec", fill):
            self.board._on_add_card(database.STATUS_DOING)
        row = next(c for c in database.list_cards(self.pid) if c["title"] == "直接从列新增")
        self.assertEqual(row["status"], database.STATUS_DOING)
        def edit(dialog):
            dialog._title.setText("看板编辑成功")
            return 1
        with patch.object(CardDialog, "exec", edit):
            self.board._on_open_card(row["id"])
        self.assertTrue(any(c["title"] == "看板编辑成功" for c in database.list_cards(self.pid)))

    def test_board_search_scope_filter_and_sort_controls(self):
        sid = database.add_section(1, "工作")
        database.add_card(sid, "跨项目任务", priority=database.PRIORITY_HIGH, tags=["紧急"])
        self.board._scope.setCurrentIndex(1)
        self.board._search.setText("跨项目")
        QTest.qWait(220)
        self.assertEqual(self.board._summary_label.text(), "1 个任务")
        self.board._priority_filter.setCurrentIndex(self.board._priority_filter.findData(0))
        self.assertEqual(self.board._summary_label.text(), "0 个任务")
        self.board._clear_filters()
        self.assertEqual(self.board._summary_label.text(), "1 个任务")

    def test_settings_switch_both_themes_preserve_timers_and_selected_project(self):
        window = MainWindow()
        window.sidebar.select_project(self.pid)
        window.refresh_projects()
        self.assertEqual(window.sidebar.project_list.currentItem().data(Qt.UserRole), self.pid)
        for theme in ("light", "dark"):
            settings = window.settings_widget
            settings._theme.setCurrentIndex(settings._theme.findData(theme))
            settings.save()
            self.assertEqual(database.get_settings()["ui_theme"], theme)
            self.assertEqual(APP.palette().color(QPalette.Window).name(), palette_for(theme)["bg"].lower())
            self.assertEqual(window.timer_widget.mode_combo.count(), 2)
            self.assertEqual(window.workspace.timer_widget.mode_combo.count(), 2)
            self.assertEqual(window.workspace.tabs.count(), 4)

    def test_sidebar_can_return_to_same_function_after_project(self):
        window = MainWindow()
        window.sidebar.select_project(self.pid)
        self.assertEqual(window.stack.currentWidget(), window.workspace)
        window.sidebar.function_list.setCurrentRow(0)
        self.assertEqual(window.stack.currentWidget(), window.timer_widget)
        window.sidebar.select_project(self.pid)
        self.assertEqual(window.stack.currentWidget(), window.workspace)
        window.sidebar.function_list.setCurrentRow(0)
        self.assertEqual(window.stack.currentWidget(), window.timer_widget)

    def test_todo_titles_use_theme_text_instead_of_badge_background_colors(self):
        from ui_todo import TodoWidget
        todo = TodoWidget(self.pid)
        todo._section_list.setCurrentRow(0)
        item = todo._card_list.item(0)
        self.assertEqual(item.foreground().style(), Qt.NoBrush)
        self.assertIn("中优先级", item.text())

    def test_saving_theme_preserves_running_stopwatch_mode_and_label(self):
        window = MainWindow()
        for widget in (window.timer_widget, window.workspace.timer_widget):
            widget.mode_combo.setCurrentIndex(1)
            widget._toggle()
        settings = window.settings_widget
        settings._theme.setCurrentIndex(settings._theme.findData("light"))
        settings.save()
        for widget in (window.timer_widget, window.workspace.timer_widget):
            self.assertEqual(widget.phase_label.text(), "正计时")
            self.assertTrue(widget._timer.running)
            self.assertFalse(widget._timer.is_countdown())

    def test_closing_settings_after_save_does_not_call_deleted_button(self):
        from ui_settings import SettingsWidget
        settings = SettingsWidget()
        with patch("sys.excepthook") as exceptions:
            settings.save()
            settings.deleteLater()
            APP.sendPostedEvents(None, QEvent.DeferredDelete)
            QTest.qWait(1550)
            exceptions.assert_not_called()


if __name__ == "__main__":
    unittest.main()
