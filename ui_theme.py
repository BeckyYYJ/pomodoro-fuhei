"""Shared palettes for the desktop app and its Trello-style board."""

from PySide6.QtGui import QColor, QPalette

PALETTES = {
    "light": dict(bg="#F7F8FA", surface="#FFFFFF", column="#F1F2F4", card="#FFFFFF",
                  text="#172B4D", muted="#626F86", border="#DCDFE4", hover="#E9F2FF",
                  selected="#CCE0FF", accent="#0C66E4", board="#E9F2FF", disabled="#8590A2"),
    "dark": dict(bg="#101418", surface="#1D2125", column="#1D2125", card="#282E33",
                 text="#DEE4EA", muted="#9FADBC", border="#454F59", hover="#333C43",
                 selected="#164B78", accent="#579DFF", board="#142A43", disabled="#738496"),
}


def palette_for(name):
    return PALETTES.get(name, PALETTES["dark"])


def stylesheet(name):
    p = palette_for(name)
    return """
QWidget { color: %(text)s; }
QMainWindow, QDialog, QStackedWidget { background: %(bg)s; }
QLabel { background: transparent; }
QLabel[role="muted"] { color: %(muted)s; }
QLabel[role="heading"] { font-size: 22px; font-weight: 700; }
QLabel[role="badge"] { background: %(selected)s; border-radius: 5px; padding: 3px 8px; font-size: 12px; }
QPushButton, QComboBox, QLineEdit, QSpinBox {
    min-height: 32px; padding: 2px 10px; border: 1px solid %(border)s;
    border-radius: 6px; background: %(surface)s; color: %(text)s;
}
QPushButton:hover, QComboBox:hover { background: %(hover)s; }
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus { border: 1px solid %(accent)s; }
QPushButton:disabled, QComboBox:disabled { color: %(disabled)s; }
QPushButton[role="primary"] { background: #0C66E4; color: #FFFFFF; border: none; font-weight: 600; }
QPushButton[role="primary"]:hover { background: #0055CC; }
QPushButton[role="subtle"] { background: transparent; border: none; text-align: left; color: %(muted)s; }
QPushButton[role="subtle"]:hover { background: %(hover)s; color: %(text)s; }
QComboBox QAbstractItemView, QMenu { background: %(surface)s; color: %(text)s; selection-background-color: %(selected)s; }
QMenu::item { padding: 8px 24px; }
QMenu::item:selected { background: %(selected)s; }
QTextEdit, QListWidget, QTableWidget, QScrollArea {
    background: %(surface)s; color: %(text)s; border: 1px solid %(border)s; border-radius: 8px;
}
QListWidget::item, QTableWidget::item { padding: 8px; border-radius: 4px; }
QListWidget::item:selected, QTableWidget::item:selected { background: %(selected)s; color: %(text)s; }
QHeaderView::section { background: %(column)s; color: %(muted)s; border: none; padding: 8px; }
QTabWidget::pane { border: none; background: %(bg)s; }
QTabBar::tab { background: transparent; color: %(muted)s; padding: 10px 18px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: %(accent)s; border-bottom: 2px solid %(accent)s; font-weight: 600; }
QProgressBar { background: %(border)s; border: none; border-radius: 3px; }
QProgressBar::chunk { background: #0C66E4; border-radius: 3px; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: %(border)s; border-radius: 4px; min-height: 24px; }
QScrollBar:horizontal { background: transparent; height: 9px; }
QScrollBar::handle:horizontal { background: %(border)s; border-radius: 4px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QWidget#sidebar { background: %(surface)s; border-right: 1px solid %(border)s; }
QWidget#sidebar QListWidget { border: none; background: transparent; }
QWidget#sidebar QListWidget::item:selected { background: %(selected)s; color: %(text)s; font-weight: 600; }
QFrame#sidebarDivider { background: %(border)s; border: none; }
QPushButton[role="archiveNav"] { background: transparent; border: none; text-align: left; padding: 6px 10px; }
QPushButton[role="archiveNav"]:hover { background: %(hover)s; }
QPushButton[role="archiveNav"]:checked { background: %(selected)s; font-weight: 600; }
QWidget#board, QWidget#archive { background: %(board)s; border-radius: 10px; }
QScrollArea#boardScroll, QScrollArea#columnScroll, QScrollArea#archiveScroll { background: transparent; border: none; }
QWidget#boardColumns, QWidget#columnBody, QWidget#archiveGrid { background: transparent; }
QFrame#boardColumn { background: %(column)s; border-radius: 10px; }
QFrame#boardColumn[dropActive="true"] { border: 2px solid %(accent)s; }
QFrame#card { background: %(card)s; border: 1px solid %(border)s; border-radius: 8px; }
QFrame#card:hover, QFrame#card[dropActive="true"] { border: 1px solid %(accent)s; }
QLabel[role="cardTitle"] { font-weight: 600; }
QLabel[role="tag"] { background: %(selected)s; border-radius: 4px; padding: 2px 6px; }
QLabel[role="priority0"] { background: #216E4E; color: #FFFFFF; border-radius: 4px; padding: 2px 6px; }
QLabel[role="priority1"] { background: #F5CD47; color: #172B4D; border-radius: 4px; padding: 2px 6px; }
QLabel[role="priority2"] { background: #AE2E24; color: #FFFFFF; border-radius: 4px; padding: 2px 6px; }
QLabel[role="completedStep"] { color: %(muted)s; text-decoration: line-through; }
QPushButton[role="cardEdit"] { min-height: 22px; padding: 2px 8px; color: %(muted)s; }
QWidget#cardSteps { border-top: 1px solid %(border)s; }
QCheckBox { spacing: 8px; }
""" % p


def apply_theme(app, name):
    name = name if name in PALETTES else "dark"
    p = palette_for(name)
    palette = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.WindowText, "text"),
                      (QPalette.Base, "surface"), (QPalette.AlternateBase, "column"),
                      (QPalette.Text, "text"), (QPalette.Button, "surface"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "selected"),
                      (QPalette.HighlightedText, "text"), (QPalette.PlaceholderText, "muted"),
                      (QPalette.ToolTipBase, "surface"), (QPalette.ToolTipText, "text")):
        palette.setColor(role, QColor(p[key]))
    app.setPalette(palette)
    app.setProperty("ui_theme", name)
    app.setStyleSheet(stylesheet(name))
