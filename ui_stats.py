from datetime import datetime

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import database
from heatmap import HeatmapWidget


class StatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._locked_project_id = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._filter_label = QLabel("项目：")
        filter_row.addWidget(self._filter_label)
        self.project_filter = QComboBox()
        self.project_filter.currentIndexChanged.connect(lambda _: self.refresh())
        filter_row.addWidget(self.project_filter)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self._card_labels = []
        cards = QHBoxLayout()
        cards.setSpacing(14)
        for caption, color in [
            ("今日番茄", "#E74C3C"),
            ("今日时长(分)", "#E67E22"),
            ("本周番茄", "#27AE60"),
            ("累计番茄", "#8E44AD"),
            ("累计时长(分)", "#55A7FF"),
            ("完成率", "#2980B9"),
        ]:
            label = QLabel("-", alignment=Qt.AlignCenter)
            label.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color};")
            self._card_labels.append(label)
            card = QWidget()
            inner = QVBoxLayout(card)
            inner.setContentsMargins(0, 6, 0, 6)
            inner.setSpacing(2)
            inner.addWidget(label)
            cap = QLabel(caption, alignment=Qt.AlignCenter)
            cap.setStyleSheet("font-size: 13px; color: #929AA6;")
            inner.addWidget(cap)
            cards.addWidget(card, 1)
        layout.addLayout(cards)

        self._heatmap = HeatmapWidget(112)
        layout.addWidget(self._heatmap)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(16)
        self._chart, self._series, self._axis_x, self._axis_y, view = self._make_chart("最近 7 天番茄数", "#FF806B")
        chart_row.addWidget(view, 1)
        self._time_chart, self._time_series, self._time_axis_x, self._time_axis_y, time_view = self._make_chart("最近 7 天时间记录（分钟）", "#55A7FF")
        chart_row.addWidget(time_view, 1)
        layout.addLayout(chart_row, 1)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["开始时间", "时长(分)", "项目", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setMaximumHeight(200)
        layout.addWidget(self._table)

    def _make_chart(self, title, color):
        chart = QChart()
        chart.setTheme(QChart.ChartThemeDark)
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(False)
        series = QBarSeries()
        series.setLabelsVisible(True)
        series.setLabelsPosition(QBarSeries.LabelsOutsideEnd)
        chart.addSeries(series)
        axis_x = QBarCategoryAxis()
        axis_y = QValueAxis()
        axis_y.setRange(0, 10)
        axis_y.setLabelFormat("%d")
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(180)
        view.setStyleSheet("background: #171A20; border: 1px solid #2D333C; border-radius: 8px;")
        view._bar_color = color
        return chart, series, axis_x, axis_y, view

    def set_projects(self, projects):
        current = self.project_filter.currentData()
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItem("全部项目", None)
        for project in projects:
            self.project_filter.addItem(project["name"], project["id"])
        index = self.project_filter.findData(current)
        self.project_filter.setCurrentIndex(max(0, index))
        self.project_filter.blockSignals(False)

    def lock_project(self, project_id):
        self._locked_project_id = project_id
        index = self.project_filter.findData(project_id)
        if index >= 0:
            self.project_filter.setCurrentIndex(index)
        self._filter_label.setVisible(False)
        self.project_filter.setVisible(False)
        self.refresh()

    def _project_id(self):
        if self._locked_project_id is not None:
            return self._locked_project_id
        return self.project_filter.currentData()

    def refresh(self):
        pid = self._project_id()
        today = database.summary(1, pid)
        week = database.summary(7, pid)
        total = database.summary_total(pid)
        rate = f"{week['count'] * 100 // max(week['started'], 1)}%" if week["started"] else "0%"
        values = [today["count"], today["minutes"], week["count"], total["count"], total["minutes"], rate]
        for label, value in zip(self._card_labels, values):
            label.setText(str(value))

        self._heatmap.set_data(database.counts_since(112, pid))

        counts = database.counts_since(7, pid)
        bar_set = QBarSet("番茄")
        bar_set.setColor(QColor("#FF806B"))
        for _, count in counts:
            bar_set.append(count)
        self._series.clear()
        self._series.append(bar_set)
        self._axis_x.clear()
        self._axis_x.append(
            [datetime.fromisoformat(day).strftime("%m-%d") for day, _ in counts]
        )
        self._axis_y.setRange(0, max(5, max(c for _, c in counts) + 2))
        self._chart.removeSeries(self._series)
        self._chart.addSeries(self._series)
        self._series.attachAxis(self._axis_x)
        self._series.attachAxis(self._axis_y)

        minutes = database.minutes_since(7, pid)
        time_set = QBarSet("分钟")
        time_set.setColor(QColor("#55A7FF"))
        for _, minutes_value in minutes:
            time_set.append(minutes_value)
        self._time_series.clear()
        self._time_series.append(time_set)
        self._time_axis_x.clear()
        self._time_axis_x.append(
            [datetime.fromisoformat(day).strftime("%m-%d") for day, _ in minutes]
        )
        self._time_axis_y.setRange(0, max(30, max(v for _, v in minutes) + 10))
        self._time_chart.removeSeries(self._time_series)
        self._time_chart.addSeries(self._time_series)
        self._time_series.attachAxis(self._time_axis_x)
        self._time_series.attachAxis(self._time_axis_y)

        records = database.recent(20, pid)
        self._table.setRowCount(len(records))
        for row, record in enumerate(records):
            start = datetime.fromisoformat(record["start_time"])
            start_item = QTableWidgetItem(start.strftime("%Y-%m-%d %H:%M"))
            minutes = QTableWidgetItem(str(record["minutes"]))
            project = QTableWidgetItem(record["project_name"] or "默认")
            status = QTableWidgetItem("完成" if record["completed"] else "中断")
            status.setForeground(
                QColor("#27AE60") if record["completed"] else QColor("#95A5A6")
            )
            self._table.setItem(row, 0, start_item)
            self._table.setItem(row, 1, minutes)
            self._table.setItem(row, 2, project)
            self._table.setItem(row, 3, status)
