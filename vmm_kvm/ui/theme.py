# -*- coding: utf-8 -*-
import os

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icons")

BG      = "#0a141f"
PANEL   = "#0d1926"
CARD    = "#132434"
CARD2   = "#16293c"
BORDER  = "#1f3a52"
ACCENT  = "#2dd4bf"
ACCENT_D = "#17a493"
TEXT    = "#dbe7f1"
MUTED   = "#7e97ac"
GREEN   = "#4ade80"
AMBER   = "#fbbf24"
RED     = "#f87171"

QSS = """
* { font-family: 'Cantarell','Noto Sans','DejaVu Sans',sans-serif; font-size: 13px; color: %(TEXT)s; }
QMainWindow, QDialog { background: %(BG)s; }
QWidget#Sidebar { background: %(PANEL)s; border-right: 1px solid %(BORDER)s; }
QWidget#SideTitle { color: %(TEXT)s; font-size: 16px; font-weight: bold; }
QWidget#SideStatus { color: %(MUTED)s; font-size: 11px; }
QToolButton#NavBtn {
    text-align: left; padding: 9px 12px; border: none; border-radius: 8px;
    color: %(MUTED)s; background: transparent; font-size: 13px;
}
QToolButton#NavBtn:hover { background: %(CARD)s; color: %(TEXT)s; }
QToolButton#NavBtn:checked { background: %(CARD2)s; color: %(ACCENT)s; border-left: 3px solid %(ACCENT)s; }

QFrame#Toolbar { background: %(PANEL)s; border-bottom: 1px solid %(BORDER)s; }
QToolButton#TbBtn {
    background: %(CARD)s; border: 1px solid %(BORDER)s; border-radius: 8px;
    padding: 7px 14px; color: %(TEXT)s;
}
QToolButton#TbBtn:hover { border-color: %(ACCENT_D)s; color: %(ACCENT)s; }
QToolButton#TbBtn:disabled { color: %(MUTED)s; border-color: %(BORDER)s; background: %(CARD)s; }
QToolButton#TbAccent {
    background: %(ACCENT)s; border: 1px solid %(ACCENT)s; border-radius: 8px;
    padding: 7px 16px; color: #062a26; font-weight: bold;
}
QToolButton#TbAccent:hover { background: %(ACCENT_D)s; }
QToolButton#TbAccent:disabled { background: %(CARD2)s; color: %(MUTED)s; border-color: %(BORDER)s; }
QToolButton:focus, QPushButton:focus { border: 1px solid %(ACCENT)s; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: %(CARD)s; border: 1px solid %(BORDER)s; border-radius: 8px;
    padding: 6px 10px; min-height: 20px;
    selection-background-color: %(ACCENT_D)s; selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: %(ACCENT)s; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url(%(ARROW_DOWN)s); width: 10px; height: 6px; margin-right: 8px; }
QComboBox QAbstractItemView {
    background: %(CARD)s; border: 1px solid %(BORDER)s; selection-background-color: %(CARD2)s;
    selection-color: %(ACCENT)s; outline: none;
}
QSpinBox::up-button, QSpinBox::down-button { background: %(CARD2)s; border: none; width: 18px; }
QSpinBox::up-arrow { image: url(%(ARROW_UP)s); width: 9px; height: 5px; }
QSpinBox::down-arrow { image: url(%(ARROW_DOWN)s); width: 9px; height: 5px; }

QTabWidget::pane { border: 1px solid %(BORDER)s; border-radius: 10px; background: %(PANEL)s; top: -1px; }
QTabBar::tab {
    background: transparent; color: %(MUTED)s; padding: 8px 16px;
    border: none; border-bottom: 2px solid transparent; margin-right: 4px;
}
QTabBar::tab:hover { color: %(TEXT)s; }
QTabBar::tab:selected { color: %(ACCENT)s; border-bottom: 2px solid %(ACCENT)s; }

QListWidget, QTableWidget, QTreeWidget, QTreeView, QListView, QPlainTextEdit, QTextEdit {
    background: %(PANEL)s; border: 1px solid %(BORDER)s; border-radius: 10px;
    outline: none; alternate-background-color: %(CARD)s;
}
QTreeView::item, QListView::item { padding: 4px 6px; border-radius: 6px; }
QTreeView::item:selected, QListView::item:selected { background: %(CARD2)s; color: %(ACCENT)s; }
QListWidget::item { border-radius: 8px; }
QListWidget::item:selected { background: %(CARD2)s; }
QTableWidget { gridline-color: %(BORDER)s; }
QHeaderView::section {
    background: %(PANEL)s; color: %(MUTED)s; border: none;
    border-bottom: 1px solid %(BORDER)s; padding: 7px 10px; font-size: 12px;
}
QTableCornerButton::section { background: %(PANEL)s; border: none; }

QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid %(BORDER)s; background: %(CARD)s;
}
QCheckBox::indicator:checked { background: %(ACCENT)s; border-color: %(ACCENT)s; }
QCheckBox::indicator:hover { border-color: %(ACCENT_D)s; }

QRadioButton::indicator { width: 15px; height: 15px; border-radius: 8px; border: 1px solid %(BORDER)s; background: %(CARD)s; }
QRadioButton::indicator:checked { background: %(ACCENT)s; border-color: %(ACCENT)s; }

QPushButton {
    background: %(CARD)s; border: 1px solid %(BORDER)s; border-radius: 8px;
    padding: 7px 16px; color: %(TEXT)s;
}
QPushButton:hover { border-color: %(ACCENT_D)s; color: %(ACCENT)s; }
QPushButton:disabled { color: %(MUTED)s; }
QPushButton#Accent { background: %(ACCENT)s; color: #062a26; font-weight: bold; border-color: %(ACCENT)s; }
QPushButton#Accent:hover { background: %(ACCENT_D)s; color: #062a26; }
QPushButton#Danger:hover { border-color: %(RED)s; color: %(RED)s; }

QProgressBar {
    background: %(CARD)s; border: 1px solid %(BORDER)s; border-radius: 7px;
    text-align: center; color: %(TEXT)s; height: 14px;
}
QProgressBar::chunk { background: %(ACCENT)s; border-radius: 6px; }

QSlider::groove:horizontal { background: %(CARD)s; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal {
    background: %(ACCENT)s; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px;
}
QSlider::sub-page:horizontal { background: %(ACCENT_D)s; border-radius: 3px; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: %(CARD2)s; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: %(ACCENT_D)s; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: %(CARD2)s; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QSplitter::handle { background: %(BORDER)s; width: 2px; }

QMenu { background: %(CARD)s; border: 1px solid %(BORDER)s; border-radius: 10px; padding: 6px; }
QMenu::item { padding: 7px 22px; border-radius: 6px; }
QMenu::item:selected { background: %(CARD2)s; color: %(ACCENT)s; }
QMenu::separator { height: 1px; background: %(BORDER)s; margin: 5px 8px; }

QToolTip { background: %(CARD2)s; color: %(TEXT)s; border: 1px solid %(BORDER)s; padding: 5px; }
QMessageBox { background: %(PANEL)s; }
QLabel#H1 { font-size: 19px; font-weight: bold; }
QLabel#H2 { font-size: 15px; font-weight: bold; }
QLabel#Muted { color: %(MUTED)s; font-size: 12px; }
QLabel#Card { background: %(CARD)s; border: 1px solid %(BORDER)s; border-radius: 10px; }
QGroupBox {
    background: %(PANEL)s; border: 1px solid %(BORDER)s; border-radius: 10px;
    margin-top: 14px; padding: 14px 12px 10px 12px; font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; top: 0px; color: %(ACCENT)s; }
""" % {
    "BG": BG, "PANEL": PANEL, "CARD": CARD, "CARD2": CARD2, "BORDER": BORDER,
    "ACCENT": ACCENT, "ACCENT_D": ACCENT_D, "TEXT": TEXT, "MUTED": MUTED,
    "GREEN": GREEN, "AMBER": AMBER, "RED": RED,
    "ARROW_DOWN": (_ASSETS + "/arrow-down.svg").replace("\\", "/"),
    "ARROW_UP": (_ASSETS + "/arrow-up.svg").replace("\\", "/"),
}


def apply_theme(app):
    app.setStyleSheet(QSS)
