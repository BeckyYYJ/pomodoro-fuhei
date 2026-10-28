from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import database
import sound


class SettingsWidget(QWidget):
    saved = Signal()
    projects_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        form = QFormLayout()
        self._work = QSpinBox()
        self._work.setRange(1, 120)
        self._work.setSuffix(" 分钟")
        form.addRow("专注时长", self._work)

        self._short = QSpinBox()
        self._short.setRange(1, 60)
        self._short.setSuffix(" 分钟")
        form.addRow("短休息", self._short)

        self._long = QSpinBox()
        self._long.setRange(1, 120)
        self._long.setSuffix(" 分钟")
        form.addRow("长休息", self._long)

        self._every = QSpinBox()
        self._every.setRange(1, 12)
        self._every.setSuffix(" 个")
        form.addRow("每几个番茄后长休息", self._every)

        self._margin = QComboBox()
        self._margin.addItem("紧凑（8 px）", 8)
        self._margin.addItem("标准（16 px）", 16)
        self._margin.addItem("宽松（24 px）", 24)
        form.addRow("界面边距", self._margin)

        self._font_size = QComboBox()
        self._font_size.addItem("小（12 pt）", 12)
        self._font_size.addItem("标准（14 pt）", 14)
        self._font_size.addItem("大（16 pt）", 16)
        form.addRow("字体大小", self._font_size)
        self._theme = QComboBox()
        self._theme.addItem("浅色", "light")
        self._theme.addItem("深色", "dark")
        form.addRow("界面主题", self._theme)
        layout.addLayout(form)

        sound_row = QHBoxLayout()
        sound_row.setSpacing(8)
        self._sound = QComboBox()
        for key, label in sound.SOUND_CHOICES.items():
            self._sound.addItem(label, key)
        sound_row.addWidget(QLabel("音效："))
        sound_row.addWidget(self._sound)
        test_button = QPushButton("试听")
        test_button.clicked.connect(self._on_test_sound)
        sound_row.addWidget(test_button)
        sound_row.addStretch(1)
        layout.addLayout(sound_row)

        layout.addWidget(QLabel("项目"))
        self._project_list = QListWidget()
        self._project_list.setMaximumHeight(130)
        layout.addWidget(self._project_list)
        project_buttons = QHBoxLayout()
        project_buttons.setSpacing(8)
        new_button = QPushButton("新建")
        new_button.clicked.connect(self._on_new_project)
        project_buttons.addWidget(new_button)
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(self._on_delete_project)
        project_buttons.addWidget(delete_button)
        project_buttons.addStretch(1)
        layout.addLayout(project_buttons)

        hint = QLabel("主题、音效和时长修改后点击保存生效")
        hint.setProperty("role", "muted")
        hint.setStyleSheet("font-size: 13px;")
        layout.addWidget(hint)

        self._save_button = QPushButton("保存")
        self._save_button.setFixedHeight(36)
        self._save_button.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold;"
            " background: #E74C3C; color: white; border-radius: 8px; padding: 0 24px; }"
            "QPushButton:hover { background: #C0392B; }"
        )
        self._save_button.clicked.connect(self.save)
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(lambda: self._save_button.setText("保存"))
        layout.addWidget(self._save_button)
        layout.addStretch(1)

    def load(self):
        settings = database.get_settings()
        self._work.setValue(int(settings["work_minutes"]))
        self._short.setValue(int(settings["short_minutes"]))
        self._long.setValue(int(settings["long_minutes"]))
        self._every.setValue(int(settings["long_every"]))
        index = self._sound.findData(settings["sound_effect"])
        self._sound.setCurrentIndex(max(0, index))
        margin = int(settings.get("ui_margin", 16))
        margin_index = self._margin.findData(margin)
        self._margin.setCurrentIndex(margin_index if margin_index >= 0 else 1)
        font_size = int(settings.get("ui_font_size", 14))
        font_index = self._font_size.findData(font_size)
        self._font_size.setCurrentIndex(font_index if font_index >= 0 else 1)
        self._theme.setCurrentIndex(max(0, self._theme.findData(settings.get("ui_theme", "dark"))))

    def save(self):
        database.save_settings(
            {
                "work_minutes": self._work.value(),
                "short_minutes": self._short.value(),
                "long_minutes": self._long.value(),
                "long_every": self._every.value(),
                "sound_effect": self._sound.currentData(),
                "ui_margin": self._margin.currentData(),
                "ui_font_size": self._font_size.currentData(),
                "ui_theme": self._theme.currentData(),
            }
        )
        self.saved.emit()
        self._save_button.setText("已保存")
        self._feedback_timer.start(1500)

    def _on_test_sound(self):
        sound.play(self._sound.currentData())

    def set_projects(self, projects):
        self._project_list.clear()
        for project in projects:
            item = QListWidgetItem(project["name"])
            item.setData(Qt.UserRole, project["id"])
            if project["id"] == 1:
                item.setToolTip("默认项目，不可删除")
            self._project_list.addItem(item)

    def _on_new_project(self):
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称：")
        if ok and name.strip():
            created = database.create_project(name.strip())
            if created is None:
                QMessageBox.warning(self, "提示", "项目名称已存在")
            else:
                self.projects_changed.emit()

    def _on_delete_project(self):
        item = self._project_list.currentItem()
        if item is None:
            return
        pid = item.data(Qt.UserRole)
        if pid == 1:
            QMessageBox.information(self, "提示", "默认项目不可删除")
            return
        answer = QMessageBox.question(
            self,
            "删除项目",
            f"删除项目「{item.text()}」？\n该项目的记录将归入默认项目。",
        )
        if answer == QMessageBox.Yes:
            database.delete_project(pid)
            self.projects_changed.emit()
