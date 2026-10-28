from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

import database
from timer_logic import PomodoroTimer
from ui_board import BoardWidget
from ui_stats import StatsWidget
from ui_timer import TimerWidget
from ui_todo import TodoWidget


class ProjectWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_id = database.DEFAULT_PROJECT_ID
        self._timer = PomodoroTimer(database.get_settings, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._name_label = QLabel("")
        self._name_label.setStyleSheet(
            "font-size: 22px; font-weight: bold;"
        )
        header.addWidget(self._name_label)
        badge = QLabel("项目工作区")
        badge.setProperty("role", "badge")
        header.addWidget(badge)
        header.addStretch(1)
        layout.addLayout(header)

        self.tabs = QTabWidget()

        self.board = BoardWidget()
        self.tabs.addTab(self.board, "看板")

        self.todo = TodoWidget(self._project_id)
        self.tabs.addTab(self.todo, "待办")

        self.timer_widget = TimerWidget(self._timer)
        self.timer_widget.refresh_today.connect(self._refresh_today)
        self.tabs.addTab(self.timer_widget, "计时")

        self.stats = StatsWidget()
        self.tabs.addTab(self.stats, "统计")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)

        self.set_project(self._project_id)

    def set_project(self, project_id):
        self._project_id = project_id
        name = "默认"
        for project in database.list_projects():
            if project["id"] == project_id:
                name = project["name"]
                break
        self._name_label.setText(name)
        self.board.set_locked_project(project_id)
        self.todo.set_project(project_id)
        self.timer_widget.lock_project(project_id)
        self.stats.lock_project(project_id)
        self._refresh_today()

    def refresh_projects(self, projects):
        self.timer_widget.set_projects(projects)
        self.stats.set_projects(projects)
        self.board.refresh_projects()

    def on_shown(self):
        widget = self.tabs.currentWidget()
        if widget is self.stats:
            self.stats.refresh()
        elif widget is self.board:
            self.board.refresh_projects()
        elif widget is self.todo:
            self.todo.refresh()

    def apply_settings(self):
        self._timer.apply_settings()
        if self._timer.is_countdown():
            self.timer_widget._on_phase(self._timer.phase)

    def _on_tab_changed(self, index):
        self.on_shown()

    def _refresh_today(self):
        today = database.summary(1, self._project_id)
        self.timer_widget.today_label.setText(
            f"今日已完成 {today['count']} 个番茄 · 共 {today['minutes']} 分钟"
        )
