"""Three-column project board and its task actions."""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

import database
from ui_card import CARD_MIME, CardFrame, delete_card_with_confirmation, drag_card_id, set_drop_state
from ui_card_dialog import CardDialog


class _Column(QFrame):
    card_dropped = Signal(int, int)
    card_opened = Signal(int)
    add_requested = Signal(int)
    expanded_changed = Signal(int, bool)
    archive_requested = Signal(int)
    delete_requested = Signal(int)
    archive_done_requested = Signal()

    def __init__(self, status, parent=None):
        super().__init__(parent)
        self._status = status
        self.setObjectName("boardColumn")
        self.setMinimumWidth(270)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel({0: "待办 · To do", 1: "进行中 · Doing", 2: "已完成 · Done"}[status])
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        header.addWidget(title)
        self._count_label = QLabel("0")
        self._count_label.setProperty("role", "muted")
        header.addWidget(self._count_label)
        header.addStretch(1)
        if status == database.STATUS_DONE:
            self._archive_button = QPushButton("一键归档")
            self._archive_button.setProperty("role", "cardEdit")
            self._archive_button.setToolTip("归档当前项目的全部已完成卡片，不受搜索和筛选影响")
            self._archive_button.clicked.connect(self.archive_done_requested)
            header.addWidget(self._archive_button)
        layout.addLayout(header)
        body = QWidget()
        body.setObjectName("columnBody")
        body.setAcceptDrops(True)
        body.dragEnterEvent = self.dragEnterEvent
        body.dragMoveEvent = self.dragMoveEvent
        body.dragLeaveEvent = self.dragLeaveEvent
        body.dropEvent = self.dropEvent
        self._body = QVBoxLayout(body)
        self._body.setContentsMargins(1, 1, 1, 1)
        self._body.setSpacing(8)
        self._body.setAlignment(Qt.AlignTop)
        self._scroll = QScrollArea()
        self._scroll.setObjectName("columnScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setWidget(body)
        layout.addWidget(self._scroll, 1)
        add = QPushButton("＋ 添加任务")
        add.setProperty("role", "subtle")
        add.clicked.connect(lambda: self.add_requested.emit(self._status))
        layout.addWidget(add)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()
            set_drop_state(self, True)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        set_drop_state(self, False)

    def dropEvent(self, event):
        set_drop_state(self, False)
        card_id = drag_card_id(event)
        if card_id is not None:
            self.card_dropped.emit(card_id, self._status)
            event.acceptProposedAction()

    def clear_cards(self):
        while self._body.count():
            widget = self._body.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()

    def add_card(self, card, expanded=False):
        frame = CardFrame(card, on_drop=self.card_dropped.emit, expanded=expanded)
        frame.opened.connect(self.card_opened)
        frame.expanded_changed.connect(self.expanded_changed)
        frame.archive_requested.connect(self.archive_requested)
        frame.delete_requested.connect(self.delete_requested)
        self._body.addWidget(frame)

    def set_count(self, count):
        self._count_label.setText(str(count))
        if not count:
            empty = QLabel("暂无任务" if not self._status else "将任务拖到这里")
            empty.setProperty("role", "muted")
            empty.setAlignment(Qt.AlignCenter)
            empty.setMinimumHeight(65)
            empty.setAttribute(Qt.WA_TransparentForMouseEvents)
            self._body.addWidget(empty)


class BoardWidget(QWidget):
    projects_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locked_project_id = None
        self._expanded_ids = set()
        self.setObjectName("board")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        top = QHBoxLayout()
        heading = QLabel("项目看板")
        heading.setProperty("role", "heading")
        top.addWidget(heading)
        self._summary_label = QLabel()
        self._summary_label.setProperty("role", "muted")
        top.addWidget(self._summary_label)
        top.addStretch(1)
        self._project_combo = QComboBox()
        self._project_combo.currentIndexChanged.connect(self._refresh_board)
        top.addWidget(self._project_combo)
        self._add_button = QPushButton("＋ 新建任务")
        self._add_button.setProperty("role", "primary")
        self._add_button.clicked.connect(lambda: self._on_add_card(database.STATUS_TODO))
        top.addWidget(self._add_button)
        layout.addLayout(top)
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索任务、备注、分类或标签…")
        self._search.setClearButtonEnabled(True)
        self._search.setAccessibleName("搜索任务")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self._refresh_board)
        self._search.textChanged.connect(lambda: self._search_timer.start())
        search_row.addWidget(self._search, 1)
        self._scope = QComboBox()
        self._scope.addItem("当前项目", False)
        self._scope.addItem("全部项目", True)
        self._scope.setAccessibleName("搜索范围")
        self._scope.currentIndexChanged.connect(self._refresh_board)
        search_row.addWidget(self._scope)
        layout.addLayout(search_row)
        filters = QHBoxLayout()
        self._priority_filter = QComboBox()
        self._priority_filter.addItem("全部优先级", None)
        for key, name in database.PRIORITY_NAMES.items():
            self._priority_filter.addItem(name + "优先级", key)
        self._priority_filter.setAccessibleName("优先级筛选")
        self._tag_filter = QComboBox()
        self._tag_filter.addItem("全部标签", None)
        self._tag_filter.setAccessibleName("标签筛选")
        self._sort = QComboBox()
        for name, value in (("优先级排序", "priority"), ("标题排序", "title"),
                            ("最近创建", "created"), ("最近更新", "updated"), ("最近完成", "completed")):
            self._sort.addItem(name, value)
        self._sort.setAccessibleName("任务排序")
        for combo in (self._priority_filter, self._tag_filter, self._sort):
            combo.currentIndexChanged.connect(self._refresh_board)
            filters.addWidget(combo)
        reset = QPushButton("清除筛选")
        reset.clicked.connect(self._clear_filters)
        filters.addWidget(reset)
        filters.addStretch(1)
        layout.addLayout(filters)
        container = QWidget()
        container.setObjectName("boardColumns")
        columns = QHBoxLayout(container)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(12)
        self._columns = {}
        for status in database.STATUS_NAMES:
            column = _Column(status)
            column.card_dropped.connect(self._on_card_dropped)
            column.card_opened.connect(self._on_open_card)
            column.add_requested.connect(self._on_add_card)
            column.expanded_changed.connect(self._remember_expanded)
            column.archive_requested.connect(self._on_archive_card)
            column.delete_requested.connect(self._on_delete_card)
            column.archive_done_requested.connect(self._on_archive_done)
            columns.addWidget(column, 1)
            self._columns[status] = column
        scroll = QScrollArea()
        scroll.setObjectName("boardScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        self.refresh_projects()

    def _current_project_id(self):
        return self._locked_project_id or self._project_combo.currentData() or database.DEFAULT_PROJECT_ID

    def set_locked_project(self, project_id):
        changed = self._locked_project_id != project_id
        self._locked_project_id = project_id
        self._project_combo.hide()
        if changed:
            self._clear_filters()
        else:
            self._refresh_board()

    def refresh_projects(self):
        current = self._project_combo.currentData()
        self._project_combo.blockSignals(True)
        self._project_combo.clear()
        for project in database.list_projects():
            self._project_combo.addItem(project["name"], project["id"])
        self._project_combo.setCurrentIndex(max(0, self._project_combo.findData(current)))
        self._project_combo.blockSignals(False)
        self._refresh_board()

    def _clear_filters(self):
        self._search.clear()
        for combo in (self._scope, self._priority_filter, self._tag_filter, self._sort):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._refresh_board()

    def _refresh_board(self):
        pid = None if self._scope.currentData() else self._current_project_id()
        current_tag = self._tag_filter.currentData()
        self._tag_filter.blockSignals(True)
        self._tag_filter.clear()
        self._tag_filter.addItem("全部标签", None)
        for tag in database.list_tags(pid):
            self._tag_filter.addItem(tag, tag)
        self._tag_filter.setCurrentIndex(max(0, self._tag_filter.findData(current_tag)))
        self._tag_filter.blockSignals(False)
        cards = database.list_cards(pid, search=self._search.text(),
                                    priority=self._priority_filter.currentData(),
                                    tag=self._tag_filter.currentData(), sort=self._sort.currentData())
        for status, column in self._columns.items():
            column.clear_cards()
            matches = [c for c in cards if c["status"] == status]
            for card in matches:
                column.add_card(card, expanded=card["id"] in self._expanded_ids)
            column.set_count(len(matches))
        self._summary_label.setText(f"{len(cards)} 个任务")
        has_done = any(c["status"] == database.STATUS_DONE
                       for c in database.list_cards(self._current_project_id()))
        self._columns[database.STATUS_DONE]._archive_button.setEnabled(has_done)

    def _on_archive_card(self, card_id):
        if database.archive_card(card_id):
            self._refresh_board()

    def _on_archive_done(self):
        database.archive_done_cards(self._current_project_id())
        self._refresh_board()

    def _on_delete_card(self, card_id):
        if delete_card_with_confirmation(self, card_id):
            self._refresh_board()

    def _remember_expanded(self, card_id, expanded):
        if expanded:
            self._expanded_ids.add(card_id)
        else:
            self._expanded_ids.discard(card_id)

    def _on_card_dropped(self, card_id, status):
        if status in database.STATUS_NAMES:
            database.set_card_status(card_id, status)
            # Finish the Qt drop before deleting the target widgets.
            QTimer.singleShot(0, self._refresh_board)

    def _on_add_card(self, status):
        dialog = CardDialog(parent=self, project_id=self._current_project_id(), status=status)
        if dialog.exec():
            dialog.save_card()
            self._refresh_board()

    def _on_open_card(self, card_id):
        card = next((c for c in database.list_cards(None) if c["id"] == card_id), None)
        if card:
            dialog = CardDialog(card, self)
            if dialog.exec():
                dialog.save_card()
                self._refresh_board()
