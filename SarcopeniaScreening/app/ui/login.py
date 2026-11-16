"""login.py — หน้าเข้าสู่ระบบ และหน้าสร้างผู้ดูแลคนแรก (เปิดแอปครั้งแรก)"""
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QVBoxLayout

from ..core import config as C
from .widgets import ComboBox, button, field, label


class _Base(QDialog):
    def __init__(self, title, subtitle):
        super().__init__()
        self.setWindowTitle(C.APP_TITLE)
        self.setMinimumWidth(380)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(32, 28, 32, 24)
        self.v.setSpacing(10)
        t = label(title, "title")
        t.setAlignment(Qt.AlignCenter)
        self.v.addWidget(t)
        if subtitle:
            s = label(subtitle, "muted")
            s.setAlignment(Qt.AlignCenter)
            self.v.addWidget(s)
        self.v.addSpacing(8)
        self.err = label("", "error")

    def _edit(self, password=False, placeholder=""):
        e = QLineEdit()
        e.setPlaceholderText(placeholder)
        if password:
            e.setEchoMode(QLineEdit.Password)
        e.textEdited.connect(lambda: self.err.setText(""))
        return e


class LoginDialog(_Base):
    def __init__(self, db):
        super().__init__("คัดกรองภาวะมวลกล้ามเนื้อน้อย", "")
        self.db, self.user = db, None
        self.username = self._edit(placeholder="staff01")
        self.password = self._edit(password=True)
        self.v.addWidget(field("ชื่อผู้ใช้", self.username))
        self.v.addWidget(field("รหัสผ่าน", self.password))
        self.v.addWidget(self.err)
        b = button("เข้าสู่ระบบ", "primary")
        b.clicked.connect(self._login)
        self.password.returnPressed.connect(self._login)
        self.v.addWidget(b)

    def _login(self):
        if not self.username.text().strip() or not self.password.text():
            self.err.setText("กรอกชื่อผู้ใช้และรหัสผ่าน")
            return
        try:
            user = self.db.authenticate(self.username.text(), self.password.text())
        except sqlite3.OperationalError as e:
            self.err.setText("เปิดฐานข้อมูลไม่ได้ (ปิดโปรแกรมอื่นที่เปิดไฟล์ฐานข้อมูลอยู่ เช่น DB Browser): " + str(e))
            return
        if user is None:
            self.db.log(None, "login_failed", f"username={self.username.text().strip()}")
            self.err.setText("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            self.password.clear()
            return
        self.db.log(user["user_id"], "login")
        self.user = user
        self.accept()


class UserDialog(_Base):
    """สร้างผู้ใช้ใหม่ (ใช้ทั้งตอนเปิดครั้งแรก และในหน้าผู้ดูแล)"""

    def __init__(self, db, first_admin=False, actor_id=None):
        title = "ตั้งค่าครั้งแรก: สร้างผู้ดูแลระบบ" if first_admin else "เพิ่มผู้ใช้งาน"
        super().__init__(title, "รหัสผ่านอย่างน้อย 8 ตัวอักษร")
        self.db, self.first_admin, self.actor_id = db, first_admin, actor_id
        self.username = self._edit(placeholder="admin01")
        self.full_name = self._edit()
        self.pw1 = self._edit(password=True)
        self.pw2 = self._edit(password=True)
        for cap, w in [("ชื่อผู้ใช้", self.username), ("ชื่อ-สกุล ผู้ใช้", self.full_name),
                       ("รหัสผ่าน", self.pw1), ("ยืนยันรหัสผ่าน", self.pw2)]:
            self.v.addWidget(field(cap, w))
        self.role = None
        if not first_admin:
            self.role = ComboBox()
            self.role.addItem("เจ้าหน้าที่ (staff)", "staff")
            self.role.addItem("ผู้ดูแล (admin)", "admin")
            self.v.addWidget(field("สิทธิ์", self.role))
        self.v.addWidget(self.err)
        b = button("สร้างบัญชี", "primary")
        b.clicked.connect(self._create)
        self.v.addWidget(b)

    def _create(self):
        u, n, p1, p2 = self.username.text().strip(), self.full_name.text().strip(), self.pw1.text(), self.pw2.text()
        if not u or not n:
            self.err.setText("กรอกชื่อผู้ใช้และชื่อ-สกุล")
        elif len(p1) < C.MIN_PASSWORD:
            self.err.setText(f"รหัสผ่านต้องมีอย่างน้อย {C.MIN_PASSWORD} ตัวอักษร")
        elif p1 != p2:
            self.err.setText("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
        elif any(x["username"] == u for x in self.db.list_users()):
            self.err.setText("ชื่อผู้ใช้นี้มีอยู่แล้ว")
        else:
            role = "admin" if self.first_admin else self.role.currentData()
            uid = self.db.create_user(u, n, p1, role)
            self.db.log(self.actor_id or uid, "manage_user", f"create user_id={uid} role={role}")
            self.accept()


class PasswordDialog(_Base):
    def __init__(self, db, user_id, username, actor_id):
        super().__init__("ตั้งรหัสผ่านใหม่", username)
        self.db, self.user_id, self.actor_id = db, user_id, actor_id
        self.pw1 = self._edit(password=True)
        self.pw2 = self._edit(password=True)
        self.v.addWidget(field("รหัสผ่านใหม่", self.pw1))
        self.v.addWidget(field("ยืนยันรหัสผ่าน", self.pw2))
        self.v.addWidget(self.err)
        b = button("บันทึก", "primary")
        b.clicked.connect(self._save)
        self.v.addWidget(b)

    def _save(self):
        if len(self.pw1.text()) < C.MIN_PASSWORD:
            self.err.setText(f"รหัสผ่านต้องมีอย่างน้อย {C.MIN_PASSWORD} ตัวอักษร")
        elif self.pw1.text() != self.pw2.text():
            self.err.setText("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
        else:
            self.db.set_password(self.user_id, self.pw1.text())
            self.db.log(self.actor_id, "manage_user", f"reset password user_id={self.user_id}")
            self.accept()
