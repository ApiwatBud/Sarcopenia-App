"""widgets.py — ส่วนประกอบหน้าจอที่ใช้ซ้ำ"""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView, QMessageBox, QProgressBar,
                               QPushButton, QSizePolicy, QStyledItemDelegate, QVBoxLayout, QWidget)

from ..core import config as C
from .theme import TONES, badge_css, light_palette


def label(text, role="label") -> QLabel:
    w = QLabel(text)
    w.setProperty("role", role)
    return w


def button(text, kind=None) -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    b.setCursor(Qt.PointingHandCursor)
    return b


def card(prop="card") -> QFrame:
    f = QFrame()
    f.setProperty(prop, True)
    return f


class ComboBox(QComboBox):
    """dropdown ที่รายการตัวเลือกเป็นพื้นขาว ตัวอักษรเข้มเสมอ
    (ตัววาดรายการปกติของ Qt บน Windows ใช้สีของเมนู ซึ่งอาจเป็นตัวอักษรขาวบนพื้นขาวเมื่อเปิดโหมดมืด)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        view = QListView()
        view.setPalette(light_palette())
        view.setStyleSheet("QListView { background: #FFFFFF; color: #1F1E1C; outline: 0; }"
                           "QListView::item { color: #1F1E1C; padding: 5px 8px; }"
                           "QListView::item:selected, QListView::item:hover { background: #E6F1FB; color: #1F1E1C; }")
        self.setView(view)
        self.setItemDelegate(QStyledItemDelegate(self))


def field(caption: str, widget: QWidget) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(3)
    v.addWidget(label(caption))
    v.addWidget(widget)
    return w


def set_invalid(edit: QLineEdit, bad: bool):
    edit.setProperty("invalid", bad)
    edit.style().unpolish(edit)
    edit.style().polish(edit)


class Badge(QLabel):
    def __init__(self, text="", tone="neutral"):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)     # ขนาดพอดีข้อความ ไม่ยืดตามหน้าต่าง
        self.setAlignment(Qt.AlignCenter)
        self.set(text, tone)

    def set(self, text, tone):
        self.setText(text)
        self.setStyleSheet(badge_css(tone))
        # คำนวณขนาดจากความกว้างตัวอักษรจริง + ขอบ (ไม่พึ่ง padding ของ stylesheet ซึ่งทำให้ตัวท้ายตกขอบ)
        fm = self.fontMetrics()
        self.setFixedSize(fm.horizontalAdvance(text) + 26, fm.height() + 10)


def class_badge(key: str, pct: float | None = None) -> Badge:
    text = C.CLASS_TH[key] + (f" {pct:.0%}" if pct is not None else "")
    return Badge(text, C.CLASS_TONE[key])


class ProbBars(QWidget):
    """แถบความน่าจะเป็นของแต่ละคลาส"""

    def __init__(self):
        super().__init__()
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(4)

    def set(self, task, probs: dict):
        while self.v.count():
            w = self.v.takeAt(0).widget()
            if w is not None:
                w.hide()                                 # ซ่อนทันที ไม่ให้ซ้อนกับของใหม่
                w.deleteLater()
        for k in C.DISPLAY_ORDER[task]:
            row = QHBoxLayout()
            name = QLabel(C.CLASS_TH[k])
            name.setFixedWidth(80)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(round(probs.get(k, 0) * 1000))
            bar.setTextVisible(False)
            bar.setFixedHeight(9)
            bar.setStyleSheet("QProgressBar{background:#F1EFE8;border:none;border-radius:4px}"
                              f"QProgressBar::chunk{{background:{TONES[C.CLASS_TONE[k]][2]};border-radius:4px}}")
            pct = QLabel(f"{probs.get(k, 0):.0%}")
            pct.setFixedWidth(40)
            pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(name)
            row.addWidget(bar, 1)
            row.addWidget(pct)
            holder = QWidget()
            holder.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            self.v.addWidget(holder)


class TrendChart(QWidget):
    """กราฟเส้น % Sarcopenia ตามเวลา (วาดเอง ไม่ต้องใช้ QtCharts)"""

    def __init__(self):
        super().__init__()
        self.points: list[tuple[str, float]] = []
        self.setMinimumHeight(170)

    def set(self, points):
        self.points = points
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        left, right, top, bottom = 34, 12, 24, 28
        pad = 36                                                    # เว้นขอบให้ป้ายวันที่ไม่ล้น
        pw, ph = w - left - right, h - top - bottom
        y_of = lambda v: top + ph * (1 - v)                        # noqa: E731
        grid = QPen(QColor("#CFCCC2"))
        p.setPen(grid)
        p.drawLine(left, int(y_of(0)), w - right, int(y_of(0)))
        dash = QPen(QColor("#CFCCC2"))
        dash.setStyle(Qt.DashLine)
        p.setPen(dash)
        p.drawLine(left, int(y_of(0.5)), w - right, int(y_of(0.5)))
        p.setPen(QColor("#9A988F"))
        p.drawText(0, int(y_of(0.5)) + 4, "50%")
        if not self.points:
            p.drawText(self.rect(), Qt.AlignCenter, "ยังไม่มีการประเมิน")
            return
        n = len(self.points)
        xs = [left + pw / 2] if n == 1 else [left + pad + (pw - 2 * pad) * i / (n - 1) for i in range(n)]
        pts = [QPointF(x, y_of(v)) for x, (_, v) in zip(xs, self.points)]
        red = QColor(TONES["danger"][2])
        p.setPen(QPen(red, 2.5))
        for a, b in zip(pts, pts[1:]):
            p.drawLine(a, b)
        for pt, (d, v) in zip(pts, self.points):
            p.setPen(Qt.NoPen)
            p.setBrush(red)
            p.drawEllipse(pt, 4, 4)
            p.setPen(QColor(TONES["danger"][1]))
            p.drawText(int(pt.x()) - 24, int(pt.y()) - 22, 48, 14, Qt.AlignCenter, f"{v:.0%}")
            p.setPen(QColor("#5F5E5A"))
            p.drawText(int(pt.x()) - 40, h - 18, 80, 16, Qt.AlignCenter, d)


def confirm(parent, title, text) -> bool:
    return QMessageBox.question(parent, title, text, QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) == QMessageBox.Yes


def info(parent, title, text):
    QMessageBox.information(parent, title, text)


def error(parent, title, text):
    QMessageBox.warning(parent, title, text)


THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def thai_date(iso: str, short_year=True) -> str:
    """'2026-11-16 10:42:00' -> '16 พ.ย. 69'"""
    try:
        y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    except (TypeError, ValueError):
        return iso or ""
    be = y + 543
    return f"{d} {THAI_MONTHS[m - 1]} {be % 100 if short_year else be}"
