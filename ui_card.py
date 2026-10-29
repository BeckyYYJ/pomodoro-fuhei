"""Shared task cards, drag payloads, context menus and deletion confirmation."""

from PySide6.QtCore import QEvent, QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

import database

CARD_MIME = "application/x-card-id"


def set_drop_state(widget, active):
    widget.setProperty("dropActive", active)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def drag_card_id(event):
    try:
        return int(bytes(event.mimeData().data(CARD_MIME)).decode())
    except (ValueError, UnicodeDecodeError):
        return None


def delete_card_with_confirmation(parent, card_id):
    with database._conn() as conn:
        card = conn.execute("SELECT title FROM cards WHERE id = ?", (card_id,)).fetchone()
    if card and QMessageBox.question(
        parent, "删除卡片", f"删除「{card['title']}」？\n具体步骤也将删除，此操作无法撤销。",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
    ) == QMessageBox.Yes:
        database.delete_card(card_id)
        return True
    return False


class CardFrame(QFrame):
    opened = Signal(int)
    expanded_changed = Signal(int, bool)
    archive_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, card, on_drop=None, parent=None, expanded=False):
        super().__init__(parent)
        self._card_id = card["id"]
        self._status = card["status"]
        self._archived = bool(card["archived_at"])
        self._on_drop = on_drop
        self._drag_start = None
        self._expanded = False
        self._total, self._done = card["total"], card["done"]
        self.setObjectName("card")
        self.setAcceptDrops(not self._archived)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(card["title"])
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(200 if self._archived else 230)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        category = QLabel(f"{card['project_name']} · {card['section_name']}")
        category.setTextFormat(Qt.PlainText)
        category.setProperty("role", "muted")
        category.setWordWrap(True)
        header = QHBoxLayout()
        header.addWidget(category, 1)
        self._edit_button = QPushButton("edit", self)
        self._edit_button.setProperty("role", "cardEdit")
        self._edit_button.setAccessibleName(f"编辑任务 {card['title']}")
        self._edit_button.clicked.connect(lambda: self.opened.emit(self._card_id))
        self._edit_button.setVisible(not self._archived)
        header.addWidget(self._edit_button, 0, Qt.AlignTop)
        layout.addLayout(header)
        title = QLabel(card["title"])
        title.setTextFormat(Qt.PlainText)
        title.setWordWrap(True)
        title.setProperty("role", "cardTitle")
        layout.addWidget(title)
        if card["note"]:
            note = QLabel(card["note"] if self._archived else
                          card["note"][:110] + ("…" if len(card["note"]) > 110 else ""))
            note.setTextFormat(Qt.PlainText)
            note.setWordWrap(True)
            note.setProperty("role", "muted")
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
        self._steps_summary = QLabel()
        self._steps_summary.setProperty("role", "muted")
        layout.addWidget(self._steps_summary)
        self._steps_panel = QWidget()
        self._steps_panel.setObjectName("cardSteps")
        self._steps_panel.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._steps_layout = QVBoxLayout(self._steps_panel)
        self._steps_layout.setContentsMargins(0, 6, 0, 0)
        self._steps_layout.setSpacing(8)
        layout.addWidget(self._steps_panel)
        self._set_expanded(expanded)
        if card["done_at"]:
            completed = QLabel("完成于 " + card["done_at"].replace("T", " "))
            completed.setProperty("role", "muted")
            completed.setWordWrap(True)
            layout.addWidget(completed)
        if self._archived:
            archived = QLabel("归档于 " + card["archived_at"].replace("T", " "))
            archived.setProperty("role", "muted")
            archived.setWordWrap(True)
            layout.addWidget(archived)
        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setToolTip("点击展开或收起具体步骤；右键删除" if self._archived else
                        "点击展开或收起具体步骤；点击 edit 编辑；拖动修改状态；右键更多操作")

    def create_context_menu(self):
        menu = QMenu(self)
        if not self._archived and self._status == database.STATUS_DONE:
            menu.addAction("归档", lambda: self.archive_requested.emit(self._card_id))
        menu.addAction("删除", lambda: self.delete_requested.emit(self._card_id))
        if not self._archived:
            menu.addAction("编辑", lambda: self.opened.emit(self._card_id))
        return menu

    def contextMenuEvent(self, event):
        menu = self.create_context_menu()
        menu.exec(event.globalPos())
        menu.deleteLater()

    def _fit_archive_height(self):
        if self._archived and self.layout():
            # A scroll area's grid may allocate a wrapped card only its
            # unwrapped size hint. Enforce the height at the actual width.
            height = self.layout().totalHeightForWidth(self.width())
            if height >= 0 and self.minimumHeight() != height:
                self.setMinimumHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_archive_height()

    def event(self, event):
        handled = super().event(event)
        if event.type() == QEvent.LayoutRequest and getattr(self, "_archived", False):
            self._fit_archive_height()
        return handled

    def _set_expanded(self, expanded):
        self._expanded = expanded
        if expanded:
            while self._steps_layout.count():
                widget = self._steps_layout.takeAt(0).widget()
                if widget:
                    widget.hide()
                    widget.deleteLater()
            steps = database.list_items(self._card_id)
            for step in steps:
                row = QWidget()
                line = QVBoxLayout(row)
                line.setContentsMargins(0, 0, 0, 0)
                line.setSpacing(2)
                content = QLabel(step["content"])
                content.setTextFormat(Qt.PlainText)
                content.setWordWrap(True)
                if step["status"] == database.STATUS_DONE:
                    content.setProperty("role", "completedStep")
                line.addWidget(content)
                state = QLabel(database.STATUS_NAMES[step["status"]])
                state.setProperty("role", "muted")
                line.addWidget(state)
                if step["note"]:
                    note = QLabel(step["note"])
                    note.setTextFormat(Qt.PlainText)
                    note.setWordWrap(True)
                    note.setProperty("role", "muted")
                    line.addWidget(note)
                self._steps_layout.addWidget(row)
            if not steps:
                empty = QLabel("暂无具体步骤" if self._archived else "暂无具体步骤，点击 edit 添加")
                empty.setWordWrap(True)
                empty.setProperty("role", "muted")
                self._steps_layout.addWidget(empty)
        self._steps_panel.setVisible(expanded)
        self._steps_summary.setText(
            f"步骤 {self._done}/{self._total} · " + ("收起" if expanded else "展开"))
        self.updateGeometry()
        self._fit_archive_height()

    def _toggle_steps(self):
        self._set_expanded(not self._expanded)
        self.expanded_changed.emit(self._card_id, self._expanded)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._archived and self._drag_start is not None and (
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
            self._toggle_steps()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self._toggle_steps()
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if not self._archived and event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()
            set_drop_state(self, True)

    def dragMoveEvent(self, event):
        if not self._archived and event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        set_drop_state(self, False)

    def dropEvent(self, event):
        set_drop_state(self, False)
        card_id = drag_card_id(event)
        if not self._archived and card_id is not None and self._on_drop:
            self._on_drop(card_id, self._status)
            event.acceptProposedAction()
