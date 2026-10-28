from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from ui_theme import palette_for

CELL = 13
GAP = 3
LEFT = 34
TOP = 20
LEGEND_H = 22
COLORS = ["#EBEDF0", "#F8C9C5", "#F1948A", "#E74C3C", "#922B21"]


def _level(count):
    if count <= 0:
        return 0
    if count <= 1:
        return 1
    if count <= 3:
        return 2
    if count <= 5:
        return 3
    return 4


class HeatmapWidget(QWidget):
    def __init__(self, days=112, parent=None):
        super().__init__(parent)
        self._days = days
        self._data = {}
        self.setFixedHeight(TOP + 7 * CELL + 6 * GAP + LEGEND_H + 6)

    def set_data(self, counts):
        self._data = {day: count for day, count in counts}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        theme = QApplication.instance().property("ui_theme") or "dark"
        p = palette_for(theme)
        colors = ([p["border"]] + COLORS[1:]) if theme == "dark" else COLORS
        today = date.today()
        start = today - timedelta(days=self._days - 1)
        start -= timedelta(days=start.weekday())
        columns = (today - start).days // 7 + 1

        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)
        for col in range(columns):
            day = start + timedelta(days=col * 7)
            if day.day <= 7:
                painter.setPen(QColor(p["muted"]))
                painter.drawText(LEFT + col * (CELL + GAP), 12, f"{day.month}月")

        painter.setPen(Qt.NoPen)
        for col in range(columns):
            for row in range(7):
                day = start + timedelta(days=col * 7 + row)
                count = self._data.get(day.isoformat(), 0)
                painter.setBrush(QColor(colors[_level(count)]))
                painter.drawRoundedRect(
                    LEFT + col * (CELL + GAP),
                    TOP + row * (CELL + GAP),
                    CELL,
                    CELL,
                    3,
                    3,
                )

        legend_y = TOP + 7 * CELL + 6 * GAP
        painter.setPen(QColor(p["muted"]))
        painter.drawText(self.width() - 160, legend_y + 13, "少")
        x = self.width() - 144
        for level in range(5):
            painter.setBrush(QColor(colors[level]))
            painter.drawRoundedRect(x, legend_y + 2, 10, 10, 2, 2)
            x += 14
        painter.drawText(x + 2, legend_y + 13, "多")
        painter.end()
