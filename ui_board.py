from PySide6.QtCore import QMimeData, QRect, QSize, Qt, Signal
from PySide6.QtGui import QDrag, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QSizePolicy,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import database

CARD_MIME = "application/x-card-id"

STATUS_COLORS = {
    database.STATUS_TODO: "#55A7FF",
    database.STATUS_DOING: "#FF9A57",
    database.STATUS_DONE: "#55D98A",
}
PRIORITY_COLORS = {
    database.PRIORITY_LOW: "#95A5A6",
    database.PRIORITY_MED: "#E67E22",
    database.PRIORITY_HIGH: "#E74C3C",
}

_CARD_STYLE = (
    "QFrame#card { background: #202328; border: 1px solid #343A43;"
    " border-radius: 10px; }"
    "QFrame#card:hover { border-color: #697482; background: #252A31; }"
)
_BADGE_STYLE = (
    "QLabel { font-size: 11px; padding: 3px 8px; border-radius: 5px; }"
)


def _elide(text, width):
    metrics = QFontMetrics(QFont())
    return metrics.elidedText(text, Qt.ElideRight, width)


class FlowLayout(QLayout):
    """A compact wrapping layout used for square board cards."""

    def __init__(self, parent=None, margin=0, spacing=10):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(width, True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect.width(), False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _do_layout(self, width, test_only):
        margins = self.contentsMargins()
        effective_width = max(0, width - margins.left() - margins.right())
        lines = []
        line = []
        line_width = 0
        line_height = 0
        for item in self._items:
            item_size = item.sizeHint()
            next_width = line_width + (self.spacing() if line else 0) + item_size.width()
            if line and next_width > effective_width:
                lines.append((line, line_width, line_height))
                line = []
                line_width = 0
                line_height = 0
            line.append((item, item_size))
            line_width += item_size.width() + (self.spacing() if len(line) > 1 else 0)
            line_height = max(line_height, item_size.height())
        if line:
            lines.append((line, line_width, line_height))

        y = margins.top()
        for line, line_width, line_height in lines:
            x = margins.left()
            for item, item_size in line:
                if not test_only:
                    item.setGeometry(QRect(x, y, item_size.width(), item_size.height()))
                x += item_size.width() + self.spacing()
            y += line_height + self.spacing()
        return max(0, y - self.spacing() + margins.bottom())


class CardFrame(QFrame):
    def __init__(self, card, on_drop=None, parent=None):
        super().__init__(parent)
        self._card_id = card["id"]
        self._status = card["status"]
        self._priority = card["priority"]
        self._on_drop = on_drop
        self._drag_start = None
        self.setObjectName("card")
        self.setAcceptDrops(True)
        self.setFixedSize(180, 180)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet(self._base_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(7)

        title = QLabel(card["title"])
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F4F6F8;")
        title.setToolTip(
            f"{card['title']}\n优先级：{database.PRIORITY_NAMES[card['priority']]}"
        )
        layout.addWidget(title)

        if card["note"]:
            note = QLabel(_elide(card["note"], 190))
            note.setWordWrap(True)
            note.setStyleSheet("font-size: 11px; color: #929AA6;")
            note.setToolTip(card["note"])
            layout.addWidget(note)

        total, done = card["total"], card["done"]
        tags = QHBoxLayout()
        tags.setSpacing(6)
        priority_names = {database.PRIORITY_LOW: "低", database.PRIORITY_MED: "中", database.PRIORITY_HIGH: "高"}
        priority_bg = {database.PRIORITY_LOW: "#263A4C", database.PRIORITY_MED: "#4B3D20", database.PRIORITY_HIGH: "#4B2C2A"}
        priority_fg = {database.PRIORITY_LOW: "#8FC8FF", database.PRIORITY_MED: "#FFD36A", database.PRIORITY_HIGH: "#FF9C8D"}
        priority = QLabel(f"⚑ {priority_names[card['priority']]}")
        priority.setStyleSheet(_BADGE_STYLE + f"color: {priority_fg[card['priority']]}; background: {priority_bg[card['priority']]};")
        tags.addWidget(priority)
        tags.addStretch(1)
        layout.addLayout(tags)

        progress = QProgressBar()
        progress.setRange(0, max(total, 1))
        progress.setValue(done)
        progress.setFixedHeight(5)
        progress.setTextVisible(False)
        progress.setStyleSheet(
            "QProgressBar { background: #30353D; border: none; border-radius: 2px; }"
            f"QProgressBar::chunk {{ background: {STATUS_COLORS[self._status]}; border-radius: 2px; }}"
        )
        layout.addWidget(progress)
        count = QLabel(f"{done}/{total} 完成")
        count.setStyleSheet("font-size: 10px; color: #929AA6;")
        layout.addWidget(count)

    def _base_style(self, hover=False):
        highlight = "border: 2px solid #2980B9;" if hover else ""
        return (
            _CARD_STYLE
            + f"QFrame#card {{ {highlight}"
            f"border-top: 4px solid {STATUS_COLORS[self._status]}; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None and (
            event.position().toPoint() - self._drag_start
        ).manhattanLength() >= QApplication.startDragDistance():
            self._drag_start = None
            self._start_drag(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def _start_drag(self, event):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(CARD_MIME, str(self._card_id).encode())
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()
            self.setStyleSheet(self._base_style(hover=True))

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._base_style())

    def dropEvent(self, event):
        self.setStyleSheet(self._base_style())
        if event.mimeData().hasFormat(CARD_MIME):
            card_id = int(bytes(event.mimeData().data(CARD_MIME)).decode())
            if self._on_drop is not None:
                self._on_drop(card_id, self._status)
            event.acceptProposedAction()


class _Column(QWidget):
    card_dropped = Signal(int, int)

    def __init__(self, status, parent=None):
        super().__init__(parent)
        self._status = status
        self._color = STATUS_COLORS[status]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        self.setStyleSheet("QWidget { background: #181B20; border-radius: 10px; }")

        header = QHBoxLayout()
        header.setSpacing(6)
        title = QLabel(database.STATUS_NAMES[status])
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #F4F6F8; background: transparent;")
        header.addWidget(title)
        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(
            "font-size: 12px; color: #C4CBD3; background: #30353D;"
            " border-radius: 9px; padding: 1px 8px;"
        )
        header.addWidget(self._count_label)
        header.addStretch(1)
        layout.addLayout(header)

        body_widget = QWidget()
        body_widget.setAcceptDrops(True)
        body_widget.dragEnterEvent = self._drag_enter
        body_widget.dragMoveEvent = self._drag_move
        body_widget.dragLeaveEvent = self._drag_leave
        body_widget.dropEvent = self._drop
        self._body = FlowLayout(body_widget, spacing=10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body_widget)
        scroll.setFrameShape(QFrame.NoFrame)
        self._scroll = scroll
        scroll.setStyleSheet("QScrollArea { background: #181B20; border: none; }")
        layout.addWidget(scroll, 1)

    def _drag_enter(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()
            self._set_over(True)

    def _drag_move(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def _drag_leave(self, event):
        self._set_over(False)

    def _drop(self, event):
        self._set_over(False)
        if event.mimeData().hasFormat(CARD_MIME):
            card_id = int(bytes(event.mimeData().data(CARD_MIME)).decode())
            self.card_dropped.emit(card_id, self._status)
            event.acceptProposedAction()

    def _set_over(self, on):
        if on:
            self._scroll.setStyleSheet(
                f"QScrollArea {{ border: 2px solid {self._color};"
                " border-radius: 6px; }"
            )
        else:
            self._scroll.setStyleSheet("")

    def clear_cards(self):
        while self._body.count():
            item = self._body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def add_section_header(self, name):
        label = QLabel(f"▍{name}")
        label.setStyleSheet("font-size: 12px; color: #89939E; padding-top: 4px; background: transparent;")
        label.setFixedHeight(22)
        self._body.addWidget(label)

    def add_card(self, card):
        frame = CardFrame(
            card,
            on_drop=lambda card_id, status: self.card_dropped.emit(card_id, status),
        )
        self._body.addWidget(frame)

    def set_count(self, count):
        self._count_label.setText(str(count))


class BoardWidget(QWidget):
    projects_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locked_project_id = None
        self.setStyleSheet("background: #101216; color: #F4F6F8;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(10)
        heading = QLabel("Backlog")
        heading.setStyleSheet("font-size: 26px; font-weight: 800; color: #FFFFFF; background: transparent;")
        top.addWidget(heading)
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("font-size: 12px; color: #929AA6; background: transparent;")
        top.addWidget(self._summary_label)
        top.addStretch(1)
        self._project_label = QLabel("项目：")
        self._project_label.setStyleSheet("color: #AEB6C0; background: transparent;")
        top.addWidget(self._project_label)
        self._project_combo = QComboBox()
        self._project_combo.currentIndexChanged.connect(self._refresh_board)
        top.addWidget(self._project_combo, 1)
        self._new_project_button = QPushButton("新建项目")
        self._new_project_button.clicked.connect(self._on_new_project)
        top.addWidget(self._new_project_button)
        self._rename_project_button = QPushButton("重命名")
        self._rename_project_button.clicked.connect(self._on_rename_project)
        top.addWidget(self._rename_project_button)
        self._delete_project_button = QPushButton("删除")
        self._delete_project_button.clicked.connect(self._on_delete_project)
        top.addWidget(self._delete_project_button)
        self._add_button = QPushButton("＋")
        self._add_button.setFixedSize(40, 40)
        self._add_button.setToolTip("请在待办页新建任务")
        self._add_button.setStyleSheet("QPushButton { background: #1D2127; border: 1px solid #343A43; border-radius: 8px; font-size: 22px; color: #C4CBD3; } QPushButton:hover { background: #292E35; }")
        top.addWidget(self._add_button)
        layout.addLayout(top)

        columns = QHBoxLayout()
        columns.setSpacing(16)
        self._columns = {}
        for status in (database.STATUS_TODO, database.STATUS_DOING, database.STATUS_DONE):
            column = _Column(status)
            column.card_dropped.connect(self._on_card_dropped)
            columns.addWidget(column, 1)
            self._columns[status] = column
        layout.addLayout(columns, 1)

        self.refresh_projects()

    def _on_card_dropped(self, card_id, status):
        if 0 <= status <= 2:
            database.set_card_status(card_id, status)
            self._refresh_board()

    def set_locked_project(self, project_id):
        self._locked_project_id = project_id
        for widget in (
            self._project_label,
            self._project_combo,
            self._new_project_button,
            self._rename_project_button,
            self._delete_project_button,
        ):
            widget.setVisible(False)
        self.refresh_projects()

    def refresh_projects(self):
        if self._locked_project_id is None:
            current = self._project_combo.currentData()
            self._project_combo.blockSignals(True)
            self._project_combo.clear()
            for project in database.list_projects():
                self._project_combo.addItem(project["name"], project["id"])
            index = self._project_combo.findData(current)
            self._project_combo.setCurrentIndex(max(0, index))
            self._project_combo.blockSignals(False)
        self._refresh_board()

    def _current_project_id(self):
        if self._locked_project_id is not None:
            return self._locked_project_id
        pid = self._project_combo.currentData()
        return pid if pid is not None else database.DEFAULT_PROJECT_ID

    def _refresh_board(self):
        project_id = self._current_project_id()
        cards = database.list_cards(project_id)
        sections = database.list_sections(project_id)

        groups = {database.STATUS_TODO: {}, database.STATUS_DOING: {}, database.STATUS_DONE: {}}
        counts = {database.STATUS_TODO: 0, database.STATUS_DOING: 0, database.STATUS_DONE: 0}
        for card in cards:
            counts[card["status"]] += 1
            groups[card["status"]].setdefault(card["section_id"], []).append(card)

        for status, column in self._columns.items():
            column.clear_cards()
            column.set_count(counts[status])
            for section in sections:
                section_cards = groups[status].get(section["id"])
                if not section_cards:
                    continue
                for card in section_cards:
                    column.add_card(card)
        self._summary_label.setText(
            f"{counts[database.STATUS_TODO]} 待办  ·  "
            f"{counts[database.STATUS_DOING]} 进行中  ·  "
            f"{counts[database.STATUS_DONE]} 已完成"
        )

    def _on_new_project(self):
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称：")
        if ok and name.strip():
            if database.create_project(name.strip()) is None:
                QMessageBox.warning(self, "提示", "项目名称已存在")
            else:
                self.projects_changed.emit()
                self.refresh_projects()

    def _on_rename_project(self):
        pid = self._current_project_id()
        if pid == database.DEFAULT_PROJECT_ID:
            QMessageBox.information(self, "提示", "默认项目不可重命名")
            return
        name, ok = QInputDialog.getText(
            self, "重命名项目", "项目名称：", text=self._project_combo.currentText()
        )
        if ok and name.strip():
            with database._conn() as conn:
                conn.execute("UPDATE projects SET name = ? WHERE id = ?", (name.strip(), pid))
            self.projects_changed.emit()
            self.refresh_projects()

    def _on_delete_project(self):
        pid = self._current_project_id()
        if pid == database.DEFAULT_PROJECT_ID:
            QMessageBox.information(self, "提示", "默认项目不可删除")
            return
        answer = QMessageBox.question(
            self,
            "删除项目",
            f"删除项目「{self._project_combo.currentText()}」？\n"
            "其看板内容将一并删除，番茄记录归入默认项目。",
        )
        if answer == QMessageBox.Yes:
            database.delete_project(pid)
            self.projects_changed.emit()
            self.refresh_projects()
