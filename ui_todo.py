from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import database
from ui_board import PRIORITY_COLORS

_COLUMN_STYLE = (
    "QListWidget { border: 1px solid #2D333C; border-radius: 8px;"
    " background: #171A20; font-size: 14px; color: #E8ECF1; }"
    "QListWidget::item { padding: 10px 10px; }"
    "QListWidget::item:selected { background: #303A48; color: #FFFFFF;"
    " font-weight: bold; }"
)
_HEADER_STYLE = "font-size: 17px; font-weight: bold; color: #F4F6F8;"
_HINT_STYLE = "font-size: 13px; color: #929AA6;"


def _elide(text, width):
    metrics = QFontMetrics(QFont())
    return metrics.elidedText(text, Qt.ElideRight, width)


class _StepWidget(QWidget):
    def __init__(self, item, on_changed, parent=None):
        super().__init__(parent)
        self._on_changed = on_changed
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        content = QLabel(item["content"])
        content.setStyleSheet("font-size: 14px; color: #F4F6F8;")
        content.setToolTip(item["content"])
        text_box.addWidget(content)
        if item["note"]:
            note = QLabel(_elide(item["note"], 220))
            note.setStyleSheet("font-size: 12px; color: #929AA6;")
            note.setToolTip(item["note"])
            text_box.addWidget(note)
        layout.addLayout(text_box, 1)

        status = QComboBox()
        status.addItem("待办", database.STATUS_TODO)
        status.addItem("进行中", database.STATUS_DOING)
        status.addItem("完成", database.STATUS_DONE)
        status.setCurrentIndex(status.findData(item["status"]))
        status.setFixedWidth(68)
        status.currentIndexChanged.connect(
            lambda _: self._apply(status, database.set_item_status, item["id"])
        )
        layout.addWidget(status)

        delete_button = QPushButton("✕")
        delete_button.setFixedSize(22, 22)
        delete_button.clicked.connect(
            lambda: (database.delete_item(item["id"]), self._on_changed())
        )
        layout.addWidget(delete_button)

    def _apply(self, combo, func, item_id):
        func(item_id, combo.currentData())
        self._on_changed()


class _CardDialog(QDialog):
    def __init__(self, card=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑待办" if card else "新建待办")
        form = QFormLayout(self)

        self._title = QLineEdit(card["title"] if card else "")
        form.addRow("标题", self._title)

        self._note = QLineEdit(card["note"] if card else "")
        self._note.setPlaceholderText("备注（可选）")
        form.addRow("备注", self._note)

        self._priority = QComboBox()
        self._priority.addItem("低", database.PRIORITY_LOW)
        self._priority.addItem("中", database.PRIORITY_MED)
        self._priority.addItem("高", database.PRIORITY_HIGH)
        if card:
            self._priority.setCurrentIndex(self._priority.findData(card["priority"]))
        form.addRow("优先级", self._priority)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return {
            "title": self._title.text().strip(),
            "note": self._note.text().strip(),
            "priority": self._priority.currentData(),
        }


class TodoWidget(QWidget):
    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self._project_id = project_id
        self._section_id = None
        self._card = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("待办")
        title.setStyleSheet(_HEADER_STYLE)
        header.addWidget(title)
        hint = QLabel("大分类 → 待办 → 具体步骤")
        hint.setStyleSheet(_HINT_STYLE)
        header.addWidget(hint)
        header.addStretch(1)
        layout.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(16)

        # 左列：大分类（分区）
        col1 = QVBoxLayout()
        col1.setSpacing(4)
        col1_label = QLabel("大分类")
        col1_label.setStyleSheet(_HEADER_STYLE)
        col1.addWidget(col1_label)
        self._section_list = QListWidget()
        self._section_list.setStyleSheet(_COLUMN_STYLE)
        self._section_list.setFixedWidth(170)
        self._section_list.currentRowChanged.connect(self._on_section_changed)
        self._section_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._section_list.customContextMenuRequested.connect(
            lambda pos: self._section_menu(pos)
        )
        col1.addWidget(self._section_list, 1)
        add_section_button = QPushButton("＋ 添加分类")
        add_section_button.clicked.connect(self._on_add_section)
        col1.addWidget(add_section_button)
        columns.addLayout(col1)

        # 中列：待办（卡片）
        col2 = QVBoxLayout()
        col2.setSpacing(4)
        col2_label = QLabel("待办")
        col2_label.setStyleSheet(_HEADER_STYLE)
        col2.addWidget(col2_label)
        self._card_list = QListWidget()
        self._card_list.setStyleSheet(_COLUMN_STYLE)
        self._card_list.setFixedWidth(210)
        self._card_list.currentRowChanged.connect(self._on_card_changed)
        self._card_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._card_list.customContextMenuRequested.connect(
            lambda pos: self._card_menu(pos)
        )
        col2.addWidget(self._card_list, 1)
        add_card_button = QPushButton("＋ 添加待办")
        add_card_button.clicked.connect(self._on_add_card)
        col2.addWidget(add_card_button)
        columns.addLayout(col2)

        # 右列：具体步骤（子项）
        col3 = QVBoxLayout()
        col3.setSpacing(4)
        col3_label = QLabel("具体步骤")
        col3_label.setStyleSheet(_HEADER_STYLE)
        col3.addWidget(col3_label)
        self._card_info = QLabel()
        self._card_info.setStyleSheet("font-size: 13px; color: #929AA6;")
        col3.addWidget(self._card_info)
        body_widget = QWidget()
        self._steps_body = QVBoxLayout(body_widget)
        self._steps_body.setContentsMargins(0, 0, 0, 0)
        self._steps_body.setSpacing(6)
        self._steps_body.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body_widget)
        scroll.setFrameShape(QFrame.NoFrame)
        col3.addWidget(scroll, 1)
        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self._step_edit = QLineEdit()
        self._step_edit.setPlaceholderText("新增步骤…")
        self._step_edit.returnPressed.connect(self._on_add_step)
        add_row.addWidget(self._step_edit, 1)
        add_step_button = QPushButton("添加")
        add_step_button.clicked.connect(self._on_add_step)
        add_row.addWidget(add_step_button)
        col3.addLayout(add_row)
        columns.addLayout(col3, 1)

        layout.addLayout(columns, 1)

        self.refresh()

    def set_project(self, project_id):
        self._project_id = project_id
        self._section_id = None
        self._card = None
        self.refresh()

    def refresh(self):
        self.refresh_sections()

    # ---------- 左列：大分类 ----------
    def refresh_sections(self):
        current = self._section_id
        self._section_list.blockSignals(True)
        self._section_list.clear()
        for section in database.list_sections(self._project_id):
            item = self._section_list.addItem(section["name"])
            self._section_list.item(self._section_list.count() - 1).setData(
                Qt.UserRole, section["id"]
            )
        if current is not None:
            index = self._find_row(self._section_list, current)
            if index >= 0:
                self._section_list.setCurrentRow(index)
        self._section_list.blockSignals(False)
        if self._section_id is None or self._find_row(self._section_list, self._section_id) < 0:
            self._section_id = None
            self._card = None
        self.refresh_cards()

    def _section_menu(self, pos):
        item = self._section_list.itemAt(pos)
        if item is None:
            return
        section_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")
        chosen = menu.exec(self._section_list.mapToGlobal(pos))
        if chosen is rename_action:
            name, ok = QInputDialog.getText(self, "重命名分类", "分类名称：", text=item.text())
            if ok and name.strip():
                database.rename_section(section_id, name.strip())
                self.refresh()
        elif chosen is delete_action:
            answer = QMessageBox.question(
                self, "删除分类", f"删除分类「{item.text()}」？\n其下待办与步骤将一并删除。"
            )
            if answer == QMessageBox.Yes:
                database.delete_section(section_id)
                if self._section_id == section_id:
                    self._section_id = None
                self.refresh()

    def _on_add_section(self):
        name, ok = QInputDialog.getText(self, "新建分类", "分类名称：")
        if ok and name.strip():
            section_id = database.add_section(self._project_id, name.strip())
            self._section_id = section_id
            self.refresh()

    def _on_section_changed(self, row):
        if row < 0:
            return
        self._section_id = self._section_list.item(row).data(Qt.UserRole)
        self._card = None
        self.refresh_cards()

    # ---------- 中列：待办 ----------
    def refresh_cards(self):
        current_card_id = self._card["id"] if self._card else None
        self._card_list.blockSignals(True)
        self._card_list.clear()
        if self._section_id is not None:
            for card in database.list_cards(self._project_id):
                if card["section_id"] != self._section_id:
                    continue
                status_name = database.STATUS_NAMES[card["status"]]
                label = f"{card['title']}　[{status_name}] {done_label(card)}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, card["id"])
                item.setForeground(QColor(PRIORITY_COLORS[card["priority"]]))
                item.setToolTip(
                    f"{card['title']}\n优先级：{database.PRIORITY_NAMES[card['priority']]}"
                    f"\n状态：{status_name}"
                )
                self._card_list.addItem(item)
        if current_card_id is not None:
            index = self._find_row(self._card_list, current_card_id)
            if index >= 0:
                self._card_list.setCurrentRow(index)
        self._card_list.blockSignals(False)
        if self._card is None or self._find_row(self._card_list, self._card["id"]) < 0:
            self._card = None
        self.refresh_steps()

    def _card_menu(self, pos):
        item = self._card_list.itemAt(pos)
        if item is None:
            return
        card_id = item.data(Qt.UserRole)
        card = self._find_card(card_id)
        if card is None:
            return
        menu = QMenu(self)
        edit_action = menu.addAction("编辑")
        mark_menu = menu.addMenu("标记为")
        todo_action = mark_menu.addAction("待办")
        doing_action = mark_menu.addAction("进行中")
        done_action = mark_menu.addAction("已完成")
        delete_action = menu.addAction("删除")
        chosen = menu.exec(self._card_list.mapToGlobal(pos))
        if chosen is edit_action:
            dialog = _CardDialog(card, self)
            if not dialog.exec():
                return
            data = dialog.values()
            if not data["title"]:
                return
            database.update_card(
                card_id, data["title"], data["note"], data["priority"]
            )
            self.refresh_cards()
        elif chosen in (todo_action, doing_action, done_action):
            status = {
                todo_action: database.STATUS_TODO,
                doing_action: database.STATUS_DOING,
                done_action: database.STATUS_DONE,
            }[chosen]
            database.set_card_status(card_id, status)
            self.refresh_cards()
        elif chosen is delete_action:
            answer = QMessageBox.question(self, "删除待办", f"删除「{card['title']}」？\n其步骤将一并删除。")
            if answer == QMessageBox.Yes:
                database.delete_card(card_id)
                if self._card and self._card["id"] == card_id:
                    self._card = None
                self.refresh_cards()

    def _on_add_card(self):
        if self._section_id is None:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个分类")
            return
        dialog = _CardDialog(parent=self)
        if not dialog.exec():
            return
        data = dialog.values()
        if not data["title"]:
            return
        card_id = database.add_card(
            self._section_id, data["title"], data["note"], data["priority"]
        )
        self._card = self._find_card(card_id)
        self.refresh_cards()

    def _on_card_changed(self, row):
        if row < 0:
            return
        self._card = self._find_card(self._card_list.item(row).data(Qt.UserRole))
        self.refresh_steps()

    # ---------- 右列：具体步骤 ----------
    def refresh_steps(self):
        while self._steps_body.count() > 1:
            item = self._steps_body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if self._card is None:
            self._card_info.setText("请先在中间列选择一个待办")
            self._step_edit.setEnabled(False)
            return
        total, done = database.card_progress(self._card["id"])
        percent = f" · {done * 100 // max(total, 1)}%" if total else ""
        self._card_info.setText(
            f"{self._card['title']}（{done}/{total}{percent}）"
        )
        self._step_edit.setEnabled(True)
        for item in database.list_items(self._card["id"]):
            self._steps_body.insertWidget(
                self._steps_body.count() - 1, _StepWidget(item, self.refresh_steps)
            )

    def _on_add_step(self):
        content = self._step_edit.text().strip()
        if not content or self._card is None:
            return
        database.add_item(self._card["id"], content)
        self._step_edit.clear()
        self.refresh_steps()

    # ---------- 工具 ----------
    def _find_row(self, widget, data):
        for i in range(widget.count()):
            if widget.item(i).data(Qt.UserRole) == data:
                return i
        return -1

    def _find_card(self, card_id):
        for card in database.list_cards(self._project_id):
            if card["id"] == card_id:
                return card
        return None


def done_label(card):
    total, done = card["total"], card["done"]
    if total:
        return f"({done}/{total})"
    return ""
