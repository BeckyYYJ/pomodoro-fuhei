from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)
from PySide6.QtGui import QFont

import database
import sound
from timer_logic import PomodoroTimer
from ui_settings import SettingsWidget
from ui_sidebar import SidebarWidget
from ui_stats import StatsWidget
from ui_timer import TimerWidget
from ui_workspace import ProjectWorkspace
from ui_theme import apply_theme, stylesheet

FUNCTION_INDEX = {"timer": 0, "stats": 1, "settings": 2}
WORKSPACE_INDEX = 3

THEME_STYLE = stylesheet("dark")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("番茄钟")
        self.resize(1180, 760)
        self.setMinimumSize(950, 620)
        self._pending_record_id = None

        self._timer = PomodoroTimer(database.get_settings, self)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)
        self._central_layout = layout

        self.sidebar = SidebarWidget()
        self.sidebar.function_selected.connect(self._on_function_selected)
        self.sidebar.project_selected.connect(self._on_project_selected)
        self.sidebar.projects_changed.connect(self._on_projects_changed)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()

        self.timer_widget = TimerWidget(self._timer)
        self.timer_widget.work_started.connect(self._on_work_started)
        self.timer_widget.work_completed.connect(self._on_work_completed)
        self.timer_widget.work_skipped.connect(self._on_work_skipped)
        self.timer_widget.stopwatch_stopped.connect(self._on_stopwatch_stopped)
        self.timer_widget.refresh_today.connect(self._refresh_today)
        self.timer_widget.new_project_requested.connect(self._on_new_project_requested)
        self.stack.addWidget(self.timer_widget)

        self.stats_widget = StatsWidget()
        self.stack.addWidget(self.stats_widget)

        self.settings_widget = SettingsWidget()
        self.settings_widget.saved.connect(self._on_settings_saved)
        self.settings_widget.projects_changed.connect(self._on_projects_changed)
        self.stack.addWidget(self.settings_widget)

        self.workspace = ProjectWorkspace()
        self.workspace.timer_widget.work_started.connect(self._on_work_started)
        self.workspace.timer_widget.work_completed.connect(self._on_work_completed)
        self.workspace.timer_widget.work_skipped.connect(self._on_work_skipped)
        self.workspace.timer_widget.stopwatch_stopped.connect(self._on_stopwatch_stopped)
        self.stack.addWidget(self.workspace)

        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.stack.currentChanged.connect(self._on_page_changed)
        self.refresh_projects()
        self._refresh_today()
        self._apply_ui_margin()
        self._apply_ui_font()
        self._apply_theme()

    def refresh_projects(self):
        projects = database.list_projects()
        self.sidebar.set_projects(projects)
        self.timer_widget.set_projects(projects)
        self.stats_widget.set_projects(projects)
        self.settings_widget.set_projects(projects)
        self.workspace.refresh_projects(projects)
        if self.workspace._project_id not in {p["id"] for p in projects}:
            self.workspace.set_project(database.DEFAULT_PROJECT_ID)

    def _on_function_selected(self, key):
        self.stack.setCurrentIndex(FUNCTION_INDEX[key])

    def _on_project_selected(self, project_id):
        self.workspace.set_project(project_id)
        self.stack.setCurrentWidget(self.workspace)
        self.workspace.on_shown()

    def _on_projects_changed(self):
        self.refresh_projects()

    def _on_page_changed(self, index):
        widget = self.stack.widget(index)
        if widget is self.stats_widget:
            self.stats_widget.refresh()
            self.statusBar().showMessage("统计已刷新", 2000)
        elif widget is self.workspace:
            self.workspace.on_shown()

    def _on_new_project_requested(self):
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称：")
        if ok and name.strip():
            pid = database.create_project(name.strip())
            if pid is None:
                QMessageBox.warning(self, "提示", "项目名称已存在")
            else:
                self.refresh_projects()
                self.timer_widget.select_project(pid)

    def _on_work_started(self, planned_minutes, mode, project_id):
        if self._pending_record_id is None:
            self._pending_record_id = database.start_record(
                planned_minutes, mode, project_id
            )

    def _on_work_completed(self):
        if self._pending_record_id is not None:
            database.complete_record(self._pending_record_id)
            self._pending_record_id = None
        self.statusBar().showMessage("番茄完成！休息一下", 4000)
        sound.play(database.get_settings()["sound_effect"])

    def _on_work_skipped(self):
        if self._pending_record_id is not None:
            database.finish_record(self._pending_record_id)
            self._pending_record_id = None
        self.statusBar().showMessage("已跳过本轮", 3000)

    def _on_stopwatch_stopped(self, elapsed):
        if self._pending_record_id is not None:
            database.complete_record(self._pending_record_id)
            self._pending_record_id = None
        self.statusBar().showMessage(
            f"正计时结束，用时 {elapsed // 60} 分 {elapsed % 60} 秒", 4000
        )
        sound.play(database.get_settings()["sound_effect"])

    def _on_settings_saved(self):
        self._timer.apply_settings()
        if self._timer.is_countdown():
            self.timer_widget._on_phase(self._timer.phase)
        self.workspace.apply_settings()
        self._apply_ui_margin()
        self._apply_ui_font()
        self._apply_theme()

    def _apply_theme(self):
        apply_theme(QApplication.instance(), database.get_settings().get("ui_theme", "dark"))
        self.stats_widget.apply_theme()
        self.workspace.stats.apply_theme()

    def _apply_ui_margin(self):
        margin = int(database.get_settings().get("ui_margin", 16))
        self._central_layout.setContentsMargins(margin, margin, margin, margin)

    def _apply_ui_font(self):
        size = int(database.get_settings().get("ui_font_size", 14))
        QApplication.instance().setFont(QFont("Microsoft YaHei UI", size))

    def _refresh_today(self):
        today = database.summary(1)
        self.timer_widget.today_label.setText(
            f"今日已完成 {today['count']} 个番茄 · 共 {today['minutes']} 分钟"
        )

    def closeEvent(self, event):
        if self._pending_record_id is not None:
            database.finish_record(self._pending_record_id)
            self._pending_record_id = None
        super().closeEvent(event)


def main():
    database.init_db()
    app = QApplication([])
    app.setApplicationName("番茄钟")
    app.setFont(QFont("Microsoft YaHei UI", 14))
    app.setStyle("Fusion")
    apply_theme(app, database.get_settings().get("ui_theme", "dark"))
    window = MainWindow()
    window.show()
    app.exec()
