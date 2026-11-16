"""main_window.py — หน้าต่างหลัก: แถบเมนูซ้าย + หน้าต่าง ๆ"""
from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QVBoxLayout,
                               QWidget)

from ..core import config as C
from .page_admin import AdminPage
from .page_batch import BatchPage
from .page_history import HistoryPage
from .page_single import SinglePage
from .widgets import button


@dataclass
class Session:
    db: object
    models: object
    user: dict

    @property
    def user_id(self):
        return self.user["user_id"]

    @property
    def is_admin(self):
        return self.user["role"] == "admin"


class MainWindow(QMainWindow):
    logged_out = Signal()

    def __init__(self, session: Session):
        super().__init__()
        self.s = session
        self.setWindowTitle(C.APP_TITLE)
        self.resize(1100, 720)
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.addWidget(QLabel(C.APP_TITLE))
        hl.addStretch(1)
        role = "ผู้ดูแล" if session.is_admin else "เจ้าหน้าที่"
        hl.addWidget(QLabel(f"{session.user['username']} · {role}"))
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(160)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(8, 10, 8, 10)
        sl.setSpacing(2)
        self.stack = QStackedWidget()
        self.group = QButtonGroup(self)
        self.single = SinglePage(session)
        self.batch = BatchPage(session)
        self.history = HistoryPage(session)
        self.history.new_assessment.connect(self._assess_again)
        pages = [("รายคน", self.single), ("หลายคน", self.batch), ("ประวัติ", self.history)]
        if session.is_admin:
            self.admin = AdminPage(session)
            pages.append(("ผู้ดูแล", self.admin))
        for i, (name, page) in enumerate(pages):
            b = button(name)
            b.setCheckable(True)
            self.group.addButton(b, i)
            sl.addWidget(b)
            self.stack.addWidget(page)
        self.group.idClicked.connect(self._go)
        self.group.button(0).setChecked(True)
        sl.addStretch(1)
        out = button("ออกจากระบบ")
        out.clicked.connect(self.logout)
        sl.addWidget(out)
        body.addWidget(side)
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)
        self.setCentralWidget(central)

    def _go(self, i):
        self.stack.setCurrentIndex(i)
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def _assess_again(self, code):
        self.single.prefill(code)
        self.group.button(0).setChecked(True)
        self.stack.setCurrentIndex(0)

    def logout(self):
        self.s.db.log(self.s.user_id, "logout")
        self._logging_out = True
        self.close()
        self.logged_out.emit()

    def closeEvent(self, event):
        # ปิดหน้าต่าง (ไม่ใช่ออกจากระบบ) = ปิดแอป
        if not getattr(self, "_logging_out", False):
            QApplication.quit()
        super().closeEvent(event)
