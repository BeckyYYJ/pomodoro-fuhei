from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from timer_logic import (
    MODE_COUNTDOWN,
    MODE_STOPWATCH,
    PHASE_COLORS,
    PHASE_NAMES,
    PHASE_WORK,
)


def format_time(seconds):
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class TimerWidget(QWidget):
    work_started = Signal(int, str, int)
    work_completed = Signal()
    work_skipped = Signal()
    stopwatch_stopped = Signal(int)
    refresh_today = Signal()
    new_project_requested = Signal()

    def __init__(self, timer, parent=None):
        super().__init__(parent)
        self._timer = timer
        self._locked_project_id = None
        self._stopwatch_started = False
        self._timer.tick.connect(self._on_tick)
        self._timer.phase_changed.connect(self._on_phase)
        self._timer.work_completed.connect(self._on_work_completed)
        self._timer.work_skipped.connect(self.work_skipped)
        self._timer.stopwatch_finished.connect(self._on_stopwatch_finished)
        self._build_ui()
        self._update_mode_ui()
        self._on_tick(self._timer._current(), self._timer._total())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("倒计时", MODE_COUNTDOWN)
        self.mode_combo.addItem("正计时", MODE_STOPWATCH)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        top_row.addWidget(self.mode_combo)

        self.project_combo = QComboBox()
        top_row.addWidget(self.project_combo, 1)

        self.new_project_button = QPushButton("新建项目")
        self.new_project_button.clicked.connect(self.new_project_requested)
        top_row.addWidget(self.new_project_button)
        layout.addLayout(top_row)

        self.phase_label = QLabel(alignment=Qt.AlignCenter)
        self.phase_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(self.phase_label)

        self.time_label = QLabel(alignment=Qt.AlignCenter)
        self.time_label.setStyleSheet(
            "font-size: 96px; font-weight: bold; font-family: Consolas; color: #F4F6F8;"
        )
        layout.addWidget(self.time_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        layout.addWidget(self.progress)

        self.cycle_label = QLabel(alignment=Qt.AlignCenter)
        self.cycle_label.setStyleSheet("font-size: 15px; color: #929AA6;")
        layout.addWidget(self.cycle_label)

        self.today_label = QLabel(alignment=Qt.AlignCenter)
        self.today_label.setStyleSheet("font-size: 15px; color: #929AA6;")
        layout.addWidget(self.today_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.start_button = QPushButton("开始")
        self.start_button.setFixedHeight(40)
        self.start_button.clicked.connect(self._toggle)
        buttons.addWidget(self.start_button)

        self.reset_button = QPushButton("重置")
        self.reset_button.setFixedHeight(40)
        self.reset_button.setStyleSheet(_plain_button_style())
        self.reset_button.clicked.connect(self._on_reset)
        buttons.addWidget(self.reset_button)

        self.skip_button = QPushButton("跳过")
        self.skip_button.setFixedHeight(40)
        self.skip_button.setStyleSheet(_plain_button_style())
        self.skip_button.clicked.connect(self._on_skip)
        buttons.addWidget(self.skip_button)

        self.stop_button = QPushButton("停止")
        self.stop_button.setFixedHeight(40)
        self.stop_button.setStyleSheet(_plain_button_style())
        self.stop_button.clicked.connect(self._timer.stop_stopwatch)
        buttons.addWidget(self.stop_button)

        layout.addLayout(buttons)
        layout.addStretch(1)

    def _project_id(self):
        if self._locked_project_id is not None:
            return self._locked_project_id
        pid = self.project_combo.currentData()
        return pid if pid is not None else 1

    def lock_project(self, project_id):
        self._locked_project_id = project_id
        self.select_project(project_id)
        self.project_combo.setVisible(False)
        self.new_project_button.setVisible(False)

    def set_projects(self, projects):
        current = self.project_combo.currentData()
        self.project_combo.clear()
        for project in projects:
            self.project_combo.addItem(project["name"], project["id"])
        index = self.project_combo.findData(current)
        self.project_combo.setCurrentIndex(max(0, index))

    def select_project(self, project_id):
        index = self.project_combo.findData(project_id)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)

    def _on_mode_changed(self, index):
        mode = self.mode_combo.itemData(index)
        if not self._timer.set_mode(mode):
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(
                0 if self._timer.is_countdown() else 1
            )
            self.mode_combo.blockSignals(False)
            return
        self._stopwatch_started = False
        self._update_mode_ui()
        self._on_tick(self._timer._current(), self._timer._total())

    def _update_mode_ui(self):
        stopwatch = not self._timer.is_countdown()
        self.progress.setVisible(not stopwatch)
        self.cycle_label.setVisible(not stopwatch)
        self.skip_button.setVisible(not stopwatch)
        self.stop_button.setVisible(stopwatch)
        if stopwatch:
            self.phase_label.setText("正计时")
            self.phase_label.setStyleSheet(
                "font-size: 22px; font-weight: bold; color: #E67E22;"
            )
            self.progress.setStyleSheet(
                "QProgressBar { background: #ECF0F1; border-radius: 5px; }"
                "QProgressBar::chunk { background: #E67E22; border-radius: 5px; }"
            )
            self.start_button.setStyleSheet(_accent_button_style("#E67E22"))
            self._stopwatch_started = False
        else:
            self._on_phase(self._timer.phase)

    def _toggle(self):
        if self._timer.running:
            self._timer.pause()
        else:
            if self._timer.is_countdown():
                if self._timer.phase == PHASE_WORK:
                    self.work_started.emit(
                        max(1, round(self._timer.remaining / 60)),
                        MODE_COUNTDOWN,
                        self._project_id(),
                    )
            else:
                if not self._stopwatch_started:
                    self._stopwatch_started = True
                    self.work_started.emit(0, MODE_STOPWATCH, self._project_id())
            self._timer.start()

    def _on_reset(self):
        self._stopwatch_started = False
        self._timer.reset()

    def _on_skip(self):
        self._stopwatch_started = False
        self._timer.skip()

    def _on_tick(self, current, total):
        self.time_label.setText(format_time(current))
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(total - current)
        self.start_button.setText("暂停" if self._timer.running else "开始")

    def _on_phase(self, phase):
        color = PHASE_COLORS[phase]
        self.phase_label.setText(PHASE_NAMES[phase])
        self.phase_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {color};"
        )
        self.progress.setStyleSheet(
            "QProgressBar { background: #ECF0F1; border-radius: 5px; }"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}"
        )
        self.start_button.setStyleSheet(_accent_button_style(color))
        settings = self._timer._get_settings()
        self.cycle_label.setText(
            f"本轮已完成 {self._timer.completed_in_cycle}/{settings['long_every']} 个番茄"
        )

    def _on_work_completed(self, count):
        self.work_completed.emit()
        self.cycle_label.setText(f"本轮已完成 {count} 个番茄，休息一下吧")
        self.refresh_today.emit()

    def _on_stopwatch_finished(self, elapsed):
        self._stopwatch_started = False
        self.stopwatch_stopped.emit(elapsed)
        self.refresh_today.emit()


def _accent_button_style(color):
    return (
        "QPushButton { font-size: 16px; font-weight: bold;"
        f" background: {color}; color: white; border-radius: 8px; padding: 0 30px; }}"
        f"QPushButton:hover {{ background: {color}; }}"
    )


def _plain_button_style():
    return (
        "QPushButton { font-size: 15px; background: #1D2127; color: #F4F6F8;"
        " border-radius: 8px; padding: 0 20px; }"
        "QPushButton:hover { background: #30353D; }"
    )
