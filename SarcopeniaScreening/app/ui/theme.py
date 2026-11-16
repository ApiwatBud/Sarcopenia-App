"""theme.py — สีและ stylesheet (Qt Style Sheets) ของแอป"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette

TONES = {  # (พื้น, ตัวอักษร, แถบ)
    "success": ("#EAF3DE", "#3B6D11", "#639922"),
    "warning": ("#FAEEDA", "#854F0B", "#EF9F27"),
    "danger": ("#FCEBEB", "#A32D2D", "#E24B4A"),
    "accent": ("#E6F1FB", "#185FA5", "#2F6FD0"),
    "neutral": ("#F1EFE8", "#5F5E5A", "#888780"),
}
GOOD, BAD = TONES["success"][1], TONES["danger"][1]
ACCENT = "#2F6FD0"

QSS = """
QWidget { color: #1F1E1C; font-size: 10pt; }
QMainWindow, QDialog { background: #FFFFFF; }
#Sidebar { background: #FBFAF7; border-right: 1px solid #E3E1DA; }
#Sidebar QPushButton { text-align: left; padding: 8px 12px; border: none; border-radius: 6px; color: #5F5E5A; }
#Sidebar QPushButton:hover { background: #F1EFE8; }
#Sidebar QPushButton:checked { background: #E6F1FB; color: #185FA5; }
#Header { background: #F5F4EF; border-bottom: 1px solid #E3E1DA; }
#Header QLabel { color: #5F5E5A; }
QLabel[role="label"] { color: #5F5E5A; font-size: 9pt; }
QLabel[role="muted"] { color: #9A988F; font-size: 9pt; }
QLabel[role="error"] { color: #A32D2D; font-size: 9pt; }
QLabel[role="title"] { font-size: 13pt; font-weight: 600; }
QLineEdit { lineedit-password-character: 42; }          /* ช่องรหัสผ่านแสดงเป็น * */
QLineEdit, QComboBox { border: 1px solid #CFCCC2; border-radius: 6px; padding: 5px 8px; background: #FFFFFF; min-height: 20px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #378ADD; }
QComboBox { color: #1F1E1C; }
QLineEdit[readOnly="true"] { background: #F5F4EF; }
QLineEdit[invalid="true"] { border: 1px solid #E24B4A; }
QPushButton { border: 1px solid #CFCCC2; border-radius: 6px; padding: 6px 14px; background: #FFFFFF; }
QPushButton:hover { background: #F5F4EF; }
QPushButton:disabled { color: #B4B2A9; }
QPushButton[kind="primary"] { background: #2F6FD0; color: #FFFFFF; border: none; }
QPushButton[kind="primary"]:hover { background: #2760B8; }
QPushButton[kind="danger"] { color: #A32D2D; }
QFrame[card="true"] { border: 1px solid #E3E1DA; border-radius: 10px; background: #FFFFFF; }
QFrame[metric="true"] { border: none; border-radius: 6px; background: #F5F4EF; }
QFrame[drop="true"] { border: 1px dashed #CFCCC2; border-radius: 10px; }
QTableWidget, QListWidget { background: #FFFFFF; alternate-background-color: #FAF9F6; color: #1F1E1C; }
QTableWidget { border: 1px solid #E3E1DA; border-radius: 6px; gridline-color: #EEECE6; selection-background-color: #E6F1FB; selection-color: #1F1E1C; }
QHeaderView::section { background: #F5F4EF; border: none; border-bottom: 1px solid #E3E1DA; padding: 6px; color: #5F5E5A; }
QCheckBox { spacing: 6px; }
"""


def app_font() -> QFont:
    f = QFont()
    f.setFamilies(["Leelawadee UI", "Segoe UI", "Tahoma", "Loma", "Noto Sans Thai", "sans-serif"])
    f.setPointSize(10)
    return f


def badge_css(tone: str) -> str:
    bg, fg, _ = TONES[tone]
    return f"background:{bg}; color:{fg}; border-radius:6px; padding:0px;"


def light_palette() -> QPalette:
    pal = QPalette()
    for role, color in [(QPalette.Window, "#FFFFFF"), (QPalette.WindowText, "#1F1E1C"), (QPalette.Base, "#FFFFFF"),
                        (QPalette.AlternateBase, "#FAF9F6"), (QPalette.Text, "#1F1E1C"), (QPalette.Button, "#FFFFFF"),
                        (QPalette.ButtonText, "#1F1E1C"), (QPalette.Highlight, "#E6F1FB"),
                        (QPalette.HighlightedText, "#1F1E1C"), (QPalette.ToolTipBase, "#FFFFFF"),
                        (QPalette.ToolTipText, "#1F1E1C"), (QPalette.PlaceholderText, "#9A988F")]:
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor("#B4B2A9"))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#B4B2A9"))
    return pal


def apply_light_theme(app):
    """บังคับธีมสว่างเสมอ ไม่ตามโหมดมืดของ Windows (ไม่เช่นนั้นตารางจะเป็นพื้นดำ ตัวหนังสือดำ)"""
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)        # Qt 6.8+
    except AttributeError:
        pass
    app.setStyle("Fusion")
    app.setPalette(light_palette())
    app.setFont(app_font())
    app.setStyleSheet(QSS)
