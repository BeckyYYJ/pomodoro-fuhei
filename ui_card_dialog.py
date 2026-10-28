from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)

import database


class CardDialog(QDialog):
    """Shared card editor; cancelling also discards unsaved step changes."""

    def __init__(self, card=None, parent=None, project_id=None, status=database.STATUS_TODO):
        super().__init__(parent)
        self._card = card
        self._project_id = project_id if project_id is not None else (
            card["project_id"] if card else getattr(parent, "_project_id", 1))
        self.setWindowTitle("任务详情" if card else "新建任务")
        self.resize(560, 650)
        self._steps = [dict(item) for item in database.list_items(card["id"])] if card else []
        self._original_steps = {s["id"]: s.copy() for s in self._steps}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        heading = QLabel(self.windowTitle())
        heading.setProperty("role", "heading")
        layout.addWidget(heading)
        form = QFormLayout()
        self._title = QLineEdit(card["title"] if card else "")
        self._title.setPlaceholderText("输入任务标题")
        form.addRow("标题", self._title)
        self._note = QTextEdit()
        self._note.setAcceptRichText(False)
        self._note.setPlainText(card["note"] if card else "")
        self._note.setPlaceholderText("添加说明或备注…")
        self._note.setMaximumHeight(100)
        form.addRow("备注", self._note)
        self._section = QComboBox()
        for section in database.list_sections(self._project_id):
            self._section.addItem(section["name"], section["id"])
        if not self._section.count():
            self._section.addItem("未分类（保存时创建）", None)
        if card:
            self._section.setCurrentIndex(self._section.findData(card["section_id"]))
        form.addRow("分类", self._section)
        self._priority = QComboBox()
        for key, name in database.PRIORITY_NAMES.items():
            self._priority.addItem(name, key)
        self._priority.setCurrentIndex(self._priority.findData(card["priority"] if card else database.PRIORITY_MED))
        form.addRow("优先级", self._priority)
        self._tags = QLineEdit(", ".join(database.card_tags(card)) if card else "")
        self._tags.setPlaceholderText("多个标签用逗号分隔，例如：设计, 重要")
        form.addRow("标签", self._tags)
        self._status = QComboBox()
        for key, name in database.STATUS_NAMES.items():
            self._status.addItem(name, key)
        self._status.setCurrentIndex(self._status.findData(card["status"] if card else status))
        form.addRow("状态", self._status)
        completed = QLabel((card["done_at"] or "未记录").replace("T", " ") if card else "未记录")
        completed.setProperty("role", "muted")
        form.addRow("完成时间", completed)
        layout.addLayout(form)
        layout.addWidget(QLabel("具体步骤"))
        body = QWidget()
        self._steps_layout = QVBoxLayout(body)
        self._steps_layout.setContentsMargins(4, 4, 4, 4)
        self._steps_layout.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        scroll.setMinimumHeight(100)
        layout.addWidget(scroll, 1)
        row = QHBoxLayout()
        self._step_input = QLineEdit()
        self._step_input.setPlaceholderText("添加一个步骤…")
        self._step_input.returnPressed.connect(self._add_step)
        row.addWidget(self._step_input, 1)
        add = QPushButton("添加步骤")
        add.clicked.connect(self._add_step)
        row.addWidget(add)
        layout.addLayout(row)
        self._buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Save).setText("保存")
        self._buttons.button(QDialogButtonBox.Save).setProperty("role", "primary")
        self._buttons.button(QDialogButtonBox.Save).setAutoDefault(False)
        self._buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)
        self._title.textChanged.connect(self._validate)
        self._validate()
        self._render_steps()

    def _validate(self):
        self._buttons.button(QDialogButtonBox.Save).setEnabled(bool(self._title.text().strip()))

    def accept(self):
        if self._title.text().strip():
            super().accept()

    def values(self):
        return dict(title=self._title.text().strip(), note=self._note.toPlainText().strip(),
                    priority=self._priority.currentData(), tags=database.normalize_tags(self._tags.text()),
                    section_id=self._section.currentData(), status=self._status.currentData())

    def _add_step(self):
        content = self._step_input.text().strip()
        if content:
            self._steps.append(dict(id=None, content=content, status=database.STATUS_TODO))
            self._step_input.clear()
            self._render_steps()

    def _remove_step(self, step):
        self._steps.remove(step)
        self._render_steps()

    def _render_steps(self):
        while self._steps_layout.count():
            item = self._steps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for step in self._steps:
            widget = QWidget()
            row = QHBoxLayout(widget)
            row.setContentsMargins(0, 0, 0, 0)
            check = QCheckBox(step["content"])
            check.setChecked(step["status"] == database.STATUS_DONE)
            check.toggled.connect(lambda checked, s=step: s.update(
                status=database.STATUS_DONE if checked else database.STATUS_TODO))
            row.addWidget(check, 1)
            remove = QPushButton("删除")
            remove.setProperty("role", "subtle")
            remove.clicked.connect(lambda _=False, s=step: self._remove_step(s))
            row.addWidget(remove)
            self._steps_layout.addWidget(widget)

    def save_card(self):
        data = self.values()
        if data["section_id"] is None:
            data["section_id"] = database.add_section(self._project_id, "未分类")
        status = data.pop("status")
        if self._card:
            card_id = self._card["id"]
            database.update_card(card_id, **data)
            if status != self._card["status"]:
                database.set_card_status(card_id, status)
        else:
            card_id = database.add_card(**data, status=status)
        remaining = {s["id"] for s in self._steps if s["id"] is not None}
        for item_id in self._original_steps.keys() - remaining:
            database.delete_item(item_id)
        for step in self._steps:
            if step["id"] is None:
                item_id = database.add_item(card_id, step["content"])
                if step["status"] == database.STATUS_DONE:
                    database.set_item_status(item_id, database.STATUS_DONE)
            elif step["status"] != self._original_steps[step["id"]]["status"]:
                database.set_item_status(step["id"], step["status"])
        return card_id
