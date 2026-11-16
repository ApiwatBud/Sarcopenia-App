"""page_admin.py — ผู้ดูแลระบบ: จัดการผู้ใช้, ดูบันทึกการใช้งาน, ข้อมูลโมเดล"""
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from .login import PasswordDialog, UserDialog
from .widgets import button, card, error


class AdminPage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.s = session
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        uc = card()
        ul = QVBoxLayout(uc)
        ul.setContentsMargins(14, 12, 14, 12)
        head = QHBoxLayout()
        t = QLabel("ผู้ใช้งาน")
        t.setStyleSheet("font-weight:600;")
        add = button("+ เพิ่ม")
        add.clicked.connect(self.add_user)
        head.addWidget(t)
        head.addStretch(1)
        head.addWidget(add)
        ul.addLayout(head)
        self.users = QTableWidget(0, 4)
        self.users.setHorizontalHeaderLabels(["ชื่อผู้ใช้", "ชื่อ-สกุล", "สิทธิ์", "สถานะ"])
        self.users.verticalHeader().setVisible(False)
        self.users.setEditTriggers(QTableWidget.NoEditTriggers)
        self.users.setSelectionBehavior(QTableWidget.SelectRows)
        self.users.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ul.addWidget(self.users, 1)
        acts = QHBoxLayout()
        tog = button("เปิด/ปิดการใช้งาน")
        tog.clicked.connect(self.toggle)
        pw = button("ตั้งรหัสผ่านใหม่")
        pw.clicked.connect(self.reset_pw)
        acts.addWidget(tog)
        acts.addWidget(pw)
        acts.addStretch(1)
        ul.addLayout(acts)

        ac = card()
        al = QVBoxLayout(ac)
        al.setContentsMargins(14, 12, 14, 12)
        h2 = QHBoxLayout()
        t2 = QLabel("บันทึกการใช้งาน")
        t2.setStyleSheet("font-weight:600;")
        ref = button("รีเฟรช")
        ref.clicked.connect(self.refresh)
        h2.addWidget(t2)
        h2.addStretch(1)
        h2.addWidget(ref)
        al.addLayout(h2)
        self.audit = QTableWidget(0, 4)
        self.audit.setHorizontalHeaderLabels(["เวลา", "ผู้ใช้", "การกระทำ", "รายละเอียด"])
        self.audit.verticalHeader().setVisible(False)
        self.audit.setEditTriggers(QTableWidget.NoEditTriggers)
        hh = self.audit.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setStretchLastSection(True)
        al.addWidget(self.audit, 1)

        root.addWidget(uc, 2)
        root.addWidget(ac, 3)
        self.refresh()

    def refresh(self):
        self._users = self.s.db.list_users()
        self.users.setRowCount(len(self._users))
        for i, u in enumerate(self._users):
            for j, v in enumerate([u["username"], u["full_name"], u["role"],
                                   "ใช้งาน" if u["is_active"] else "ปิดใช้งาน"]):
                self.users.setItem(i, j, QTableWidgetItem(v))
        rows = self.s.db.audit()
        self.audit.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate([r["at"], r["username"] or "-", r["action"], r["target"] or ""]):
                self.audit.setItem(i, j, QTableWidgetItem(v))

    def _selected(self):
        i = self.users.currentRow()
        return self._users[i] if 0 <= i < len(self._users) else None

    def add_user(self):
        if UserDialog(self.s.db, actor_id=self.s.user_id).exec():
            self.refresh()

    def toggle(self):
        u = self._selected()
        if not u:
            return
        if u["user_id"] == self.s.user_id:
            error(self, "ผู้ใช้", "ปิดการใช้งานบัญชีของตัวเองไม่ได้")
            return
        if u["role"] == "admin" and u["is_active"] and self.s.db.active_admin_count() <= 1:
            error(self, "ผู้ใช้", "ต้องมีผู้ดูแลที่ใช้งานได้อย่างน้อย 1 คน")
            return
        self.s.db.set_user_active(u["user_id"], not u["is_active"])
        self.s.db.log(self.s.user_id, "manage_user", f"{'disable' if u['is_active'] else 'enable'} "
                                                     f"user_id={u['user_id']}")
        self.refresh()

    def reset_pw(self):
        u = self._selected()
        if u and PasswordDialog(self.s.db, u["user_id"], u["username"], self.s.user_id).exec():
            self.refresh()
