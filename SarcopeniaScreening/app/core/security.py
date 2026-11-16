"""
security.py — รหัสผ่าน, การเข้ารหัสข้อมูลระบุตัวตน และกุญแจ

- รหัสผ่าน: bcrypt
- ชื่อ/นามสกุล/ID: เข้ารหัสด้วย Fernet (AES-128-CBC + HMAC-SHA256, ไลบรารี cryptography)
- ค้นหาด้วย ID: HMAC-SHA256 (ไม่ต้องถอดรหัสทั้งตาราง)
- กุญแจหลัก 32 ไบต์ เก็บใน Windows Credential Manager ผ่าน keyring
  แยกกุญแจย่อยด้วย HMAC(master, label) สำหรับเข้ารหัส / ทำดัชนี / ตรวจกุญแจ
"""
import base64
import hashlib
import hmac
import secrets

import bcrypt
from cryptography.fernet import Fernet

SERVICE = "FF69Sarcopenia"
KEY_NAME = "master-key"


class KeyMissingError(RuntimeError):
    pass


def load_master_key(backend=None, create: bool = True) -> bytes:
    """อ่านกุญแจหลักจาก Credential Manager; สร้างใหม่ได้เฉพาะเมื่อ create=True (ฐานข้อมูลใหม่)"""
    if backend is None:
        import keyring as backend
    value = backend.get_password(SERVICE, KEY_NAME)
    if value is None:
        if not create:
            raise KeyMissingError("ไม่พบกุญแจของฐานข้อมูลใน Windows Credential Manager")
        value = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        backend.set_password(SERVICE, KEY_NAME, value)
    return base64.urlsafe_b64decode(value)


def _sub(master: bytes, label: bytes) -> bytes:
    return hmac.new(master, label, hashlib.sha256).digest()


class Crypto:
    def __init__(self, master: bytes):
        self._f = Fernet(base64.urlsafe_b64encode(_sub(master, b"enc")))
        self._idx = _sub(master, b"idx")
        self.key_check = _sub(master, b"check").hex()

    def enc(self, text: str) -> bytes:
        return self._f.encrypt(text.encode("utf-8"))

    def dec(self, blob) -> str:
        return self._f.decrypt(bytes(blob)).decode("utf-8")

    def id_hash(self, code: str) -> str:
        return hmac.new(self._idx, code.encode(), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode())
    except ValueError:
        return False
