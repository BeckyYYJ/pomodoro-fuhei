"""Read-only, searchable archive for one project or all projects."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

import database
from ui_card import CardFrame, delete_card_with_confirmation


class ArchiveWidget(QWidget):
    def __init__(self, project_id=None, parent=None):
        super().__init__(parent)
        self._project_id = project_id
        self._expanded_ids = set()
        self.setObjectName("archive")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setProperty("role", "heading")
        header.addWidget(self._title)
        self._summary_label = QLabel()
        self._summary_label.setProperty("role", "muted")
        header.addWidget(self._summary_label)
        header.addStretch(1)
        layout.addLayout(header)
        hint = QLabel("已完成卡片 · 点击查看步骤 · 右键删除")
        hint.setProperty("role", "muted")
        layout.addWidget(hint)
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索归档任务、备注、项目、分类或标签…")
        self._search.setClearButtonEnabled(True)
        self._search.setAccessibleName("搜索归档任务")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self.refresh)
        self._search.textChanged.connect(lambda: self._search_timer.start())
        layout.addWidget(self._search)
        filters = QHBoxLayout()
        self._priority_filter = QComboBox()
        self._priority_filter.addItem("全部优先级", None)
        for key, name in database.PRIORITY_NAMES.items():
            self._priority_filter.addItem(name + "优先级", key)
        self._priority_filter.setAccessibleName("归档优先级筛选")
        self._tag_filter = QComboBox()
        self._tag_filter.addItem("全部标签", None)
        self._tag_filter.setAccessibleName("归档标签筛选")
        self._sort = QComboBox()
        for label, key in (("优先级排序", "priority"), ("标题排序", "title"),
                           ("最近创建", "created"), ("最近更新", "updated"),
                           ("最近完成", "completed"), ("最近归档", "archived")):
            self._sort.addItem(label, key)
        self._sort.setAccessibleName("归档排序")
        for combo in (self._priority_filter, self._tag_filter, self._sort):
            combo.currentIndexChanged.connect(self.refresh)
            filters.addWidget(combo)
        reset = QPushButton("清除筛选")
        reset.clicked.connect(self._clear_filters)
        filters.addWidget(reset)
        filters.addStretch(1)
        layout.addLayout(filters)
        self._scroll = QScrollArea()
        self._scroll.setObjectName("archiveScroll")
        self._scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("archiveGrid")
        self._grid = QGridLayout(body)
        self._grid.setContentsMargins(1, 1, 1, 1)
        self._grid.setSpacing(12)
        self._grid.setAlignment(Qt.AlignTop)
        for col in range(4):
            self._grid.setColumnStretch(col, 1)
        self._scroll.setWidget(body)
        self._empty = QLabel("暂无已归档卡片\n在看板中归档已完成的任务后，可在这里查看")
        self._empty.setProperty("role", "muted")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setWordWrap(True)
        layout.addWidget(self._empty, 1)
        layout.addWidget(self._scroll, 1)
        self.refresh()

    def set_project(self, project_id):
        if project_id != self._project_id:
            self._project_id = project_id
            self._clear_filters()
        else:
            self.refresh()

    def _clear_filters(self):
        self._search.clear()
        self._search_timer.stop()
        for combo in (self._priority_filter, self._tag_filter, self._sort):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.refresh()

    def refresh(self):
        self._title.setText("全部归档" if self._project_id is None else "项目归档")
        selected_tag = self._tag_filter.currentData()
        self._tag_filter.blockSignals(True)
        self._tag_filter.clear()
        self._tag_filter.addItem("全部标签", None)
        for tag in database.list_tags(self._project_id, archived=True):
            self._tag_filter.addItem(tag, tag)
        self._tag_filter.setCurrentIndex(max(0, self._tag_filter.findData(selected_tag)))
        self._tag_filter.blockSignals(False)
        cards = database.list_cards(self._project_id, archived=True, search=self._search.text(),
                                    priority=self._priority_filter.currentData(),
                                    tag=self._tag_filter.currentData(), sort=self._sort.currentData())
        while self._grid.count():
            old = self._grid.takeAt(0).widget()
            if old:
                old.hide()
                old.deleteLater()
        for index, card in enumerate(cards):
            frame = CardFrame(card, expanded=card["id"] in self._expanded_ids)
            frame.delete_requested.connect(self._on_delete_card)
            frame.expanded_changed.connect(self._remember_expanded)
            self._grid.addWidget(frame, index // 4, index % 4)
        self._summary_label.setText(f"{len(cards)} 个已完成任务")
        self._empty.setText("没有符合筛选条件的归档卡片" if self._search.text() or
                            self._priority_filter.currentData() is not None or
                            self._tag_filter.currentData() else
                            "暂无已归档卡片\n在看板中归档已完成的任务后，可在这里查看")
        self._empty.setVisible(not cards)
        self._scroll.setVisible(bool(cards))

    def _remember_expanded(self, card_id, expanded):
        if expanded:
            self._expanded_ids.add(card_id)
        else:
            self._expanded_ids.discard(card_id)

    def _on_delete_card(self, card_id):
        if delete_card_with_confirmation(self, card_id):
            self._expanded_ids.discard(card_id)
            self.refresh()
