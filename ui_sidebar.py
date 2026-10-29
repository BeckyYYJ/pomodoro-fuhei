from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QInputDialog,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import database

_SECTION_STYLE = "font-size: 15px; font-weight: bold; padding: 2px 8px;"
_ITEM_STYLE = (
    "QListWidget { border: none; background: transparent; font-size: 14px; }"
    "QListWidget::item { padding: 6px 10px; border-radius: 6px; }"
    "QListWidget::item:selected { font-weight: bold; }"
)

FUNCTION_KEYS = [("计时", "timer"), ("统计", "stats"), ("设置", "settings")]


class SidebarWidget(QWidget):
    function_selected = Signal(str)
    project_selected = Signal(int)
    projects_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(190)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("功能", styleSheet=_SECTION_STYLE))
        self.function_list = QListWidget()
        self.function_list.setStyleSheet(_ITEM_STYLE)
        for label, key in FUNCTION_KEYS:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            self.function_list.addItem(item)
        self.function_list.setFixedHeight(112)
        # Focus restoration after a drag may change currentRow without a user
        # navigation. Only explicit mouse/keyboard activation changes pages.
        self.function_list.itemClicked.connect(
            lambda item: self._on_function_changed(self.function_list.row(item)))
        self.function_list.itemActivated.connect(
            lambda item: self._on_function_changed(self.function_list.row(item)))
        layout.addWidget(self.function_list)

        self._add_divider(layout)

        layout.addWidget(QLabel("项目", styleSheet=_SECTION_STYLE))
        self.project_list = QListWidget()
        self.project_list.setStyleSheet(_ITEM_STYLE)
        self.project_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._on_context_menu)
        self.project_list.itemClicked.connect(
            lambda item: self._on_project_changed(self.project_list.row(item)))
        self.project_list.itemActivated.connect(
            lambda item: self._on_project_changed(self.project_list.row(item)))
        layout.addWidget(self.project_list, 1)

        new_button = QPushButton("＋ 新建项目")
        new_button.clicked.connect(self._on_new_project)
        layout.addWidget(new_button)

        self._add_divider(layout)
        self.archive_button = QPushButton("归档")
        self.archive_button.setProperty("role", "archiveNav")
        self.archive_button.setCheckable(True)
        self.archive_button.setAccessibleName("查看全部项目归档")
        self.archive_button.clicked.connect(lambda: self.select_function("archive"))
        layout.addWidget(self.archive_button)

        self.select_function("timer")

    def _add_divider(self, layout):
        line = QFrame()
        line.setObjectName("sidebarDivider")
        line.setFixedSize(116, 1)
        layout.addWidget(line, 0, Qt.AlignHCenter)

    def set_projects(self, projects):
        current = self.project_list.currentItem()
        current_id = current.data(Qt.UserRole) if current else None
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for project in projects:
            item = QListWidgetItem(project["name"])
            item.setData(Qt.UserRole, project["id"])
            if project["id"] == database.DEFAULT_PROJECT_ID:
                item.setToolTip("默认项目")
            self.project_list.addItem(item)
        index = next((i for i in range(self.project_list.count())
                      if self.project_list.item(i).data(Qt.UserRole) == current_id), -1)
        self.project_list.setCurrentRow(index if index >= 0 else -1)
        self.project_list.blockSignals(False)

    def select_function(self, key):
        if key == "archive":
            for nav in (self.function_list, self.project_list):
                nav.blockSignals(True)
                nav.setCurrentRow(-1)
                nav.blockSignals(False)
            self.archive_button.setChecked(True)
            self.function_selected.emit(key)
            return
        index = self.project_list.currentRow()
        if index >= 0:
            self.project_list.blockSignals(True)
            self.project_list.setCurrentRow(-1)
            self.project_list.blockSignals(False)
        for i in range(self.function_list.count()):
            if self.function_list.item(i).data(Qt.UserRole) == key:
                self.function_list.setCurrentRow(i)
                self._on_function_changed(i)
                return

    def select_project(self, project_id):
        index = self.function_list.currentRow()
        if index >= 0:
            self.function_list.blockSignals(True)
            self.function_list.setCurrentRow(-1)
            self.function_list.blockSignals(False)
        for i in range(self.project_list.count()):
            if self.project_list.item(i).data(Qt.UserRole) == project_id:
                self.project_list.setCurrentRow(i)
                self._on_project_changed(i)
                return

    def _on_function_changed(self, row):
        if row < 0:
            return
        self.archive_button.setChecked(False)
        key = self.function_list.item(row).data(Qt.UserRole)
        if self.project_list.currentRow() >= 0:
            self.project_list.blockSignals(True)
            self.project_list.setCurrentRow(-1)
            self.project_list.blockSignals(False)
        self.function_selected.emit(key)

    def _on_project_changed(self, row):
        if row < 0:
            return
        self.archive_button.setChecked(False)
        pid = self.project_list.item(row).data(Qt.UserRole)
        if self.function_list.currentRow() >= 0:
            self.function_list.blockSignals(True)
            self.function_list.setCurrentRow(-1)
            self.function_list.blockSignals(False)
        self.project_selected.emit(pid)

    def _on_new_project(self):
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称：")
        if not (ok and name.strip()):
            return
        pid = database.create_project(name.strip())
        if pid is None:
            QMessageBox.warning(self, "提示", "项目名称已存在")
            return
        self.projects_changed.emit()
        self.select_project(pid)

    def _on_context_menu(self, pos):
        item = self.project_list.itemAt(pos)
        if item is None:
            return
        pid = item.data(Qt.UserRole)
        menu = QMenu(self)
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")
        if pid == database.DEFAULT_PROJECT_ID:
            rename_action.setEnabled(False)
            delete_action.setEnabled(False)
        chosen = menu.exec(self.project_list.mapToGlobal(pos))
        if chosen is rename_action:
            self._on_rename(pid, item.text())
        elif chosen is delete_action:
            self._on_delete(pid, item.text())

    def _on_rename(self, pid, current_name):
        name, ok = QInputDialog.getText(self, "重命名项目", "项目名称：", text=current_name)
        if ok and name.strip():
            with database._conn() as conn:
                conn.execute(
                    "UPDATE projects SET name = ? WHERE id = ?", (name.strip(), pid)
                )
            self.projects_changed.emit()

    def _on_delete(self, pid, name):
        answer = QMessageBox.question(
            self,
            "删除项目",
            f"删除项目「{name}」？\n其看板、归档卡片和步骤将一并删除，番茄记录归入默认项目。",
        )
        if answer == QMessageBox.Yes:
            database.delete_project(pid)
            self.projects_changed.emit()
