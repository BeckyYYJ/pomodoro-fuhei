from PySide6.QtCore import QMimeData, Qt, Signal, QTimer
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

import database
from ui_card_dialog import CardDialog

CARD_MIME = "application/x-card-id"


def _drop_state(widget, active):
    widget.setProperty("dropActive", active)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _drag_id(event):
    try:
        return int(bytes(event.mimeData().data(CARD_MIME)).decode())
    except (ValueError, UnicodeDecodeError):
        return None


class CardFrame(QFrame):
    opened = Signal(int)

    def __init__(self, card, on_drop=None, parent=None):
        super().__init__(parent)
        self._card_id = card["id"]
        self._status = card["status"]
        self._on_drop = on_drop
        self._drag_start = None
        self.setObjectName("card")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(card["title"])
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(230)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        category = QLabel(f"{card['project_name']} · {card['section_name']}")
        category.setProperty("role", "muted")
        category.setStyleSheet("font-size: 11px;")
        category.setWordWrap(True)
        layout.addWidget(category)
        title = QLabel(card["title"])
        title.setTextFormat(Qt.PlainText)
        title.setWordWrap(True)
        title.setProperty("role", "cardTitle")
        layout.addWidget(title)
        if card["note"]:
            note = QLabel(card["note"][:110] + ("…" if len(card["note"]) > 110 else ""))
            note.setTextFormat(Qt.PlainText)
            note.setWordWrap(True)
            note.setProperty("role", "muted")
            note.setStyleSheet("font-size: 12px;")
            layout.addWidget(note)
        badges = QHBoxLayout()
        badges.setSpacing(5)
        priority = QLabel(database.PRIORITY_NAMES[card["priority"]] + "优先级")
        priority.setProperty("role", f"priority{card['priority']}")
        badges.addWidget(priority)
        tags = database.card_tags(card)
        if tags:
            tag = QLabel(tags[0][:12] + (f" +{len(tags) - 1}" if len(tags) > 1 else ""))
            tag.setTextFormat(Qt.PlainText)
            tag.setProperty("role", "tag")
            tag.setToolTip(", ".join(tags))
            badges.addWidget(tag)
        badges.addStretch(1)
        layout.addLayout(badges)
        total, done = card["total"], card["done"]
        if total:
            progress = QProgressBar()
            progress.setRange(0, total)
            progress.setValue(done)
            progress.setTextVisible(False)
            progress.setFixedHeight(4)
            progress.setAttribute(Qt.WA_TransparentForMouseEvents)
            layout.addWidget(progress)
            count = QLabel(f"步骤 {done}/{total}")
            count.setProperty("role", "muted")
            count.setStyleSheet("font-size: 11px;")
            layout.addWidget(count)
        if card["done_at"]:
            completed = QLabel("完成于 " + card["done_at"].replace("T", " "))
            completed.setProperty("role", "muted")
            completed.setStyleSheet("font-size: 11px;")
            completed.setWordWrap(True)
            layout.addWidget(completed)
        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setToolTip("点击查看或编辑；拖动到其他列修改状态")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None and (
            event.position().toPoint() - self._drag_start
        ).manhattanLength() >= QApplication.startDragDistance():
            self._drag_start = None
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData(CARD_MIME, str(self._card_id).encode())
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.exec(Qt.MoveAction)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        clicked = event.button() == Qt.LeftButton and self._drag_start is not None
        self._drag_start = None
        super().mouseReleaseEvent(event)
        if clicked:
            self.opened.emit(self._card_id)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.opened.emit(self._card_id)
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()
            _drop_state(self, True)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        _drop_state(self, False)

    def dropEvent(self, event):
        _drop_state(self, False)
        card_id = _drag_id(event)
        if card_id is not None and self._on_drop:
            self._on_drop(card_id, self._status)
            event.acceptProposedAction()


class _Column(QFrame):
    card_dropped = Signal(int, int)
    card_opened = Signal(int)
    add_requested = Signal(int)

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
            _drop_state(self, True)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        _drop_state(self, False)

    def dropEvent(self, event):
        _drop_state(self, False)
        card_id = _drag_id(event)
        if card_id is not None:
            self.card_dropped.emit(card_id, self._status)
            event.acceptProposedAction()

    def clear_cards(self):
        while self._body.count():
            widget = self._body.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()

    def add_card(self, card):
        frame = CardFrame(card, on_drop=self.card_dropped.emit)
        frame.opened.connect(self.card_opened)
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
                column.add_card(card)
            column.set_count(len(matches))
        self._summary_label.setText(f"{len(cards)} 个任务")

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
