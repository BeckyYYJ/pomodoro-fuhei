from PySide6.QtCore import QObject, QTimer, Signal

PHASE_WORK = "work"
PHASE_SHORT = "short"
PHASE_LONG = "long"

MODE_COUNTDOWN = "countdown"
MODE_STOPWATCH = "stopwatch"

PHASE_NAMES = {PHASE_WORK: "专注", PHASE_SHORT: "短休息", PHASE_LONG: "长休息"}
PHASE_COLORS = {PHASE_WORK: "#E74C3C", PHASE_SHORT: "#27AE60", PHASE_LONG: "#2980B9"}


class PomodoroTimer(QObject):
    tick = Signal(int, int)
    phase_changed = Signal(str)
    work_completed = Signal(int)
    work_skipped = Signal()
    stopwatch_finished = Signal(int)

    def __init__(self, get_settings, parent=None):
        super().__init__(parent)
        self._get_settings = get_settings
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self.phase = PHASE_WORK
        self.mode = MODE_COUNTDOWN
        self.remaining = 0
        self.total = 0
        self.elapsed = 0
        self.running = False
        self.completed_in_cycle = 0
        self._reset_duration()

    def is_countdown(self):
        return self.mode == MODE_COUNTDOWN

    def _duration(self, phase):
        settings = self._get_settings()
        if phase == PHASE_WORK:
            return int(settings["work_minutes"]) * 60
        if phase == PHASE_SHORT:
            return int(settings["short_minutes"]) * 60
        return int(settings["long_minutes"]) * 60

    def _reset_duration(self):
        self.remaining = self._duration(self.phase)
        self.total = self.remaining

    def _current(self):
        return self.remaining if self.is_countdown() else self.elapsed

    def _total(self):
        return self.total if self.is_countdown() else 0

    def set_mode(self, mode):
        if self.running or mode == self.mode:
            return mode == self.mode
        self.mode = mode
        self._timer.stop()
        if self.is_countdown():
            self._reset_duration()
        else:
            self.elapsed = 0
        self.tick.emit(self._current(), self._total())
        self.phase_changed.emit(self.phase)
        return True

    def start(self):
        if self.running:
            return
        if self.is_countdown() and self.remaining == 0:
            self._reset_duration()
        self.running = True
        self._timer.start(1000)
        self.tick.emit(self._current(), self._total())

    def pause(self):
        self.running = False
        self._timer.stop()

    def reset(self):
        self.running = False
        self._timer.stop()
        if self.is_countdown():
            self._reset_duration()
        else:
            self.elapsed = 0
        self.tick.emit(self._current(), self._total())
        self.phase_changed.emit(self.phase)

    def skip(self):
        self.running = False
        self._timer.stop()
        if self.is_countdown():
            self._advance(completed_work=self.phase == PHASE_WORK)
        else:
            self.elapsed = 0
            self.tick.emit(0, 0)

    def stop_stopwatch(self):
        if not self.is_countdown() and self.running:
            if self.elapsed > 0:
                self.stopwatch_finished.emit(self.elapsed)
            self.running = False
            self._timer.stop()
            self.elapsed = 0
            self.tick.emit(0, 0)

    def apply_settings(self):
        if not self.running and self.is_countdown():
            self._reset_duration()
            self.tick.emit(self.remaining, self.total)

    def _on_tick(self):
        if self.is_countdown():
            self.remaining -= 1
            self.tick.emit(self.remaining, self.total)
            if self.remaining <= 0:
                self.running = False
                self._timer.stop()
                self._advance(completed_work=True)
        else:
            self.elapsed += 1
            self.tick.emit(self.elapsed, 0)

    def _advance(self, completed_work):
        if self.phase == PHASE_WORK:
            if completed_work:
                self.completed_in_cycle += 1
                self.work_completed.emit(self.completed_in_cycle)
            else:
                self.work_skipped.emit()
            settings = self._get_settings()
            if self.completed_in_cycle % int(settings["long_every"]) == 0:
                self.phase = PHASE_LONG
            else:
                self.phase = PHASE_SHORT
        else:
            self.phase = PHASE_WORK
        self._reset_duration()
        self.tick.emit(self.remaining, self.total)
        self.phase_changed.emit(self.phase)