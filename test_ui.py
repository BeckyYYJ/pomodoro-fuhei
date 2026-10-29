"""Run with .venv/Scripts/python.exe -m unittest test_ui -v."""
import gc
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QMimeData, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFontDatabase, QFontMetrics, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QMessageBox

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

    def test_card_click_and_keyboard_toggle_steps_without_editing(self):
        database.add_item(self.card_id, "具体步骤内容")
        frame = CardFrame(self.card())
        frame.resize(300, 160)
        frame.show()
        opened = []
        frame.opened.connect(opened.append)
        QTest.mouseClick(frame, Qt.LeftButton)
        self.assertTrue(frame._steps_panel.isVisible())
        self.assertTrue(any("具体步骤内容" in label.text() for label in frame._steps_panel.findChildren(QLabel)))
        QTest.keyClick(frame, Qt.Key_Return)
        self.assertFalse(frame._steps_panel.isVisible())
        self.assertEqual(opened, [])
        edit = next(b for b in frame.findChildren(QPushButton) if b.text() == "edit")
        QTest.mouseClick(edit, Qt.LeftButton)
        self.assertEqual(opened, [self.card_id])
        self.assertFalse(frame._steps_panel.isVisible())

    def test_passive_sidebar_row_change_after_drop_does_not_navigate(self):
        window = MainWindow()
        window.show()
        APP.processEvents()
        window.sidebar.select_project(self.pid)
        board = window.workspace.board
        APP.processEvents()
        frame = next(frame for frame in board.findChildren(CardFrame) if frame.isVisible())
        frame.setFocus()
        board._on_card_dropped(self.card_id, database.STATUS_DONE)
        QTest.qWait(5)
        APP.sendPostedEvents(None, QEvent.DeferredDelete)
        # QAbstractItemView may select its first row when drag focus returns.
        # Such passive selection must not be interpreted as a user navigation.
        window.sidebar.function_list.setCurrentRow(0)
        self.assertEqual(window.stack.currentWidget(), window.workspace)
        self.assertEqual(window.workspace.tabs.currentWidget(), board)

    def test_expanded_steps_survive_drop_and_edit_button_only_opens_editor(self):
        database.add_item(self.card_id, "展开后保留的步骤")
        window = MainWindow()
        window.show()
        APP.processEvents()
        window.sidebar.select_project(self.pid)
        board = window.workspace.board
        APP.processEvents()
        frame = next(frame for frame in board.findChildren(CardFrame) if frame.isVisible())
        QTest.mouseClick(frame, Qt.LeftButton)
        self.assertTrue(frame._steps_panel.isVisible())
        board._on_card_dropped(self.card_id, database.STATUS_DONE)
        QTest.qWait(50)
        APP.processEvents()
        frame = next(frame for frame in board.findChildren(CardFrame) if frame.isVisible())
        self.assertTrue(frame._steps_panel.isVisible())
        self.assertEqual(window.stack.currentWidget(), window.workspace)
        def edit(dialog):
            dialog._title.setText("只通过 edit 编辑")
            return 1
        with patch.object(CardDialog, "exec", edit):
            QTest.mouseClick(frame._edit_button, Qt.LeftButton)
        APP.processEvents()
        self.assertEqual(self.card()["title"], "只通过 edit 编辑")
        active = next(frame for frame in board.findChildren(CardFrame) if frame.isVisible())
        self.assertTrue(active._steps_panel.isVisible())

    def test_drag_gesture_does_not_expand_steps(self):
        frame = CardFrame(self.card())
        frame.resize(350, 250)
        frame.show()
        with patch("ui_board.QDrag") as drag:
            QTest.mousePress(frame, Qt.LeftButton, pos=frame.rect().center())
            QTest.mouseMove(frame, frame.rect().center() + frame.rect().topRight() / 3)
            QTest.mouseRelease(frame, Qt.LeftButton, pos=frame.rect().center())
            drag.return_value.exec.assert_called_once()
        self.assertFalse(frame._steps_panel.isVisible())

    def test_all_card_text_tracks_font_setting_without_recreating_cards(self):
        database.add_item(self.card_id, "步骤字号也要变化")
        window = MainWindow()
        database.set_card_status(self.card_id, database.STATUS_DONE)
        frame = CardFrame(self.card())
        frame.show()
        QTest.mouseClick(frame, Qt.LeftButton)
        labels = frame.findChildren(QLabel)
        settings = window.settings_widget
        settings._font_size.setCurrentIndex(settings._font_size.findData(12))
        settings.save()
        APP.processEvents()
        small = [QFontMetrics(label.font()).height() for label in labels]
        settings._font_size.setCurrentIndex(settings._font_size.findData(16))
        settings.save()
        APP.processEvents()
        large = [QFontMetrics(label.font()).height() for label in labels]
        self.assertTrue(all(big > little for little, big in zip(small, large)), (small, large))

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
            self.assertEqual(window.workspace.tabs.count(), 5)

    def test_card_context_actions_archive_only_done_and_delete_after_confirmation(self):
        frame = next(f for f in self.board.findChildren(CardFrame) if f.isVisible())
        menu = frame.create_context_menu()
        self.assertEqual([a.text() for a in menu.actions()], ["删除", "编辑"])
        database.set_card_status(self.card_id, database.STATUS_DONE)
        self.board._refresh_board()
        APP.processEvents()
        frame = next(f for f in self.board.findChildren(CardFrame) if f.isVisible())
        menu = frame.create_context_menu()
        self.assertEqual([a.text() for a in menu.actions()], ["归档", "删除", "编辑"])
        menu.actions()[0].trigger()
        self.assertEqual(database.list_cards(self.pid), [])
        from ui_archive import ArchiveWidget
        archive = ArchiveWidget(self.pid)
        archive.show()
        APP.processEvents()
        frame = next(f for f in archive.findChildren(CardFrame) if f.isVisible())
        menu = frame.create_context_menu()
        self.assertEqual([a.text() for a in menu.actions()], ["删除"])
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            menu.actions()[0].trigger()
        self.assertEqual(len(database.list_cards(None, archived=True)), 1)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            menu.actions()[0].trigger()
        self.assertEqual(database.list_cards(None, archived=True), [])

    def test_bulk_archive_ignores_filters_and_all_project_search_scope(self):
        database.set_card_status(self.card_id, database.STATUS_DONE)
        second = database.add_card(self.sid, "被筛选隐藏的完成", status=database.STATUS_DONE)
        other_sid = database.add_section(1, "其他")
        other = database.add_card(other_sid, "其他完成", status=database.STATUS_DONE)
        self.board._scope.setCurrentIndex(1)
        self.board._search.setText("其他完成")
        self.board._refresh_board()
        button = self.board._columns[2]._archive_button
        self.assertTrue(button.isEnabled())
        QTest.mouseClick(button, Qt.LeftButton)
        self.assertEqual({c["id"] for c in database.list_cards(self.pid, archived=True)},
                         {self.card_id, second})
        self.assertEqual([c["id"] for c in database.list_cards(1)], [other])
        self.assertFalse(button.isEnabled())

    def test_archive_project_and_global_navigation_grid_filters_and_readonly(self):
        ids = []
        for title in ("Echo", "Delta", "Charlie", "Bravo", "Alpha"):
            card = database.add_card(self.sid, title, status=database.STATUS_DONE,
                                     tags=["交付"], priority=2)
            database.archive_card(card)
            ids.append(card)
        other_sid = database.add_section(1, "其他")
        other = database.add_card(other_sid, "Zulu", status=database.STATUS_DONE, tags=["文档"])
        database.archive_card(other)
        window = MainWindow()
        window.resize(1500, 900)
        window.show()
        window.sidebar.select_project(self.pid)
        page = window.workspace.archive
        window.workspace.tabs.setCurrentWidget(page)
        APP.processEvents()
        frames = [f for f in page.findChildren(CardFrame) if f.isVisible()]
        self.assertEqual({f._card_id for f in frames}, set(ids))
        positions = [page._grid.getItemPosition(i)[:2] for i in range(page._grid.count())]
        self.assertEqual(positions, [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0)])
        frame = frames[0]
        self.assertFalse(frame.acceptDrops())
        self.assertFalse(frame._edit_button.isVisible())
        database.add_item(self.card_id, "其他活动卡片步骤")
        with patch("ui_board.QDrag") as drag:
            QTest.mousePress(frame, Qt.LeftButton, pos=frame.rect().center())
            QTest.mouseMove(frame, frame.rect().center() + QPointF(60, 0).toPoint())
            QTest.mouseRelease(frame, Qt.LeftButton)
            drag.assert_not_called()
        window.sidebar.select_function("archive")
        APP.processEvents()
        self.assertEqual(window.stack.currentWidget(), window.archive_widget)
        page = window.archive_widget
        self.assertEqual(len([f for f in page.findChildren(CardFrame) if f.isVisible()]), 6)
        page._tag_filter.setCurrentIndex(page._tag_filter.findData("交付"))
        page._sort.setCurrentIndex(page._sort.findData("title"))
        APP.processEvents()
        self.assertEqual([page._grid.itemAt(i).widget()._card_id for i in range(page._grid.count())],
                         list(reversed(ids)))
        page._search.setText("Bravo")
        QTest.qWait(220)
        self.assertEqual(page._grid.count(), 1)
        window.sidebar.select_project(1)
        self.assertEqual(window.workspace.archive._project_id, 1)
        self.assertEqual(window.workspace.archive._grid.count(), 1)

    def test_global_archive_refreshes_after_project_deletion_and_rename(self):
        database.set_card_status(self.card_id, database.STATUS_DONE)
        database.archive_card(self.card_id)
        window = MainWindow()
        window.show()
        window.sidebar.select_project(self.pid)
        window.workspace.tabs.setCurrentWidget(window.workspace.archive)
        window.sidebar.select_function("archive")
        APP.processEvents()
        self.assertEqual(window.archive_widget._grid.count(), 1)
        with database._conn() as conn:
            conn.execute("UPDATE projects SET name = '更名项目' WHERE id = ?", (self.pid,))
        window._on_projects_changed()
        self.assertTrue(any("更名项目" in l.text() for l in
                            window.archive_widget._grid.itemAt(0).widget().findChildren(QLabel)))
        self.assertTrue(any("更名项目" in l.text() for l in
                            window.workspace.archive._grid.itemAt(0).widget().findChildren(QLabel)))
        database.delete_project(self.pid)
        window._on_projects_changed()
        self.assertEqual(window.archive_widget._grid.count(), 0)

    def test_archive_grid_keeps_wrapped_text_and_expanded_steps_unclipped(self):
        database.update_card(self.card_id, note="保留需求说明与交付记录，便于后续查阅。")
        database.add_item(self.card_id, "核对界面与交互细节，并完成所有验收步骤")
        database.set_card_status(self.card_id, database.STATUS_DONE)
        database.archive_card(self.card_id)
        window = MainWindow()
        window.resize(1180, 760)
        window.show()
        window.sidebar.select_project(self.pid)
        page = window.workspace.archive
        window.workspace.tabs.setCurrentWidget(page)
        APP.processEvents()
        frame = page._grid.itemAt(0).widget()
        QTest.mouseClick(frame, Qt.LeftButton)
        for size in (12, 16, 14):
            settings = window.settings_widget
            settings._font_size.setCurrentIndex(settings._font_size.findData(size))
            settings.save()
            APP.processEvents()
            self.assertGreaterEqual(frame.height(), frame.heightForWidth(frame.width()))
            for label in frame.findChildren(QLabel):
                if label.isVisible() and label.wordWrap():
                    self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()), label.text())

    def test_sidebar_can_return_to_same_function_after_project(self):
        window = MainWindow()
        window.show()
        APP.processEvents()
        window.sidebar.select_project(self.pid)
        self.assertEqual(window.stack.currentWidget(), window.workspace)
        nav = window.sidebar.function_list
        QTest.mouseClick(nav.viewport(), Qt.LeftButton, pos=nav.visualItemRect(nav.item(0)).center())
        self.assertEqual(window.stack.currentWidget(), window.timer_widget)
        window.sidebar.select_project(self.pid)
        self.assertEqual(window.stack.currentWidget(), window.workspace)
        QTest.mouseClick(nav.viewport(), Qt.LeftButton, pos=nav.visualItemRect(nav.item(0)).center())
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
