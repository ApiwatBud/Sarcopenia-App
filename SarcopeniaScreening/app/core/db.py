"""
db.py — ฐานข้อมูล SQLite (โครงสร้างใน schema.sql)

ข้อมูลระบุตัวตนถูกเข้ารหัส/ถอดรหัสในคลาสนี้เท่านั้น ส่วนอื่นของแอปเห็นเป็นข้อความปกติ
"""
import json
import sqlite3
from pathlib import Path

from . import config as C
from . import idcode
from .security import Crypto, KeyMissingError, check_password, hash_password, load_master_key


class KeyMismatchError(RuntimeError):
    pass


class Database:
    def __init__(self, path: Path | None = None, key_backend=None):
        self.path = Path(path or C.db_path())
        is_new = not self.path.exists()
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        if is_new:
            self.con.executescript(C.SCHEMA_SQL.read_text(encoding="utf-8"))
        self._migrate()
        # กุญแจ: ฐานข้อมูลใหม่สร้างกุญแจได้ ฐานข้อมูลเดิมต้องใช้กุญแจเดิมเท่านั้น
        stored = self._meta("key_check")
        try:
            master = load_master_key(key_backend, create=stored is None)
        except KeyMissingError:
            self.con.close()
            raise
        self.crypto = Crypto(master)
        if stored is None:
            self._set_meta("key_check", self.crypto.key_check)
        elif stored != self.crypto.key_check:
            self.con.close()
            raise KeyMismatchError("กุญแจใน Credential Manager ไม่ตรงกับฐานข้อมูลนี้")

    # ------------------------------------------------------------------ migration
    def _migrate(self):
        """ปรับโครงสร้างฐานข้อมูลเดิมให้ตรงกับ schema.sql ปัจจุบัน (ข้อมูลเดิมยังอยู่)
        v2: subjects.national_id_hash/_enc -> code_hash/code_enc (เปลี่ยนจากเลขบัตรประชาชนเป็น ID)"""
        cols = [r["name"] for r in self.con.execute("PRAGMA table_info(subjects)")]
        if "national_id_hash" in cols:
            with self.con:
                self.con.execute("ALTER TABLE subjects RENAME COLUMN national_id_hash TO code_hash")
                self.con.execute("ALTER TABLE subjects RENAME COLUMN national_id_enc TO code_enc")
                self.con.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES ('schema_version', '2')")

    # ------------------------------------------------------------------ meta
    def _meta(self, key):
        r = self.con.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
        return r["value"] if r else None

    def _set_meta(self, key, value):
        with self.con:
            self.con.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (key, value))

    # ------------------------------------------------------------------ users
    def user_count(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def create_user(self, username, full_name, password, role="staff") -> int:
        with self.con:
            cur = self.con.execute(
                "INSERT INTO users(username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                (username.strip(), hash_password(password), full_name.strip(), role))
        return cur.lastrowid

    def authenticate(self, username, password):
        """คืน dict ของผู้ใช้เมื่อถูกต้องและยังใช้งานได้, ไม่เช่นนั้นคืน None"""
        r = self.con.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if r and r["is_active"] and check_password(password, r["password_hash"]):
            with self.con:
                self.con.execute("UPDATE users SET last_login_at = datetime('now','localtime') WHERE user_id = ?",
                                 (r["user_id"],))
            return dict(r)
        return None

    def list_users(self):
        return [dict(r) for r in self.con.execute(
            "SELECT user_id, username, full_name, role, is_active, last_login_at FROM users ORDER BY username")]

    def set_user_active(self, user_id, active: bool):
        with self.con:
            self.con.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (int(active), user_id))

    def set_password(self, user_id, password):
        with self.con:
            self.con.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (hash_password(password), user_id))

    def active_admin_count(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1").fetchone()[0]

    # ------------------------------------------------------------------ subjects
    def _subject_out(self, r):
        return {"subject_id": r["subject_id"], "code": self.crypto.dec(r["code_enc"]),
                "first_name": self.crypto.dec(r["first_name_enc"]), "last_name": self.crypto.dec(r["last_name_enc"]),
                "sex": r["sex"], "created_at": r["created_at"]}

    def find_subject(self, code):
        r = self.con.execute("SELECT * FROM subjects WHERE code_hash = ?",
                             (self.crypto.id_hash(idcode.normalize(code)),)).fetchone()
        return self._subject_out(r) if r else None

    def get_subject(self, subject_id):
        r = self.con.execute("SELECT * FROM subjects WHERE subject_id = ?", (subject_id,)).fetchone()
        return self._subject_out(r) if r else None

    def create_subject(self, code, first_name, last_name, sex, user_id) -> int:
        code = idcode.normalize(code)
        e = self.crypto.enc
        with self.con:
            cur = self.con.execute(
                "INSERT INTO subjects(code_hash, code_enc, first_name_enc, last_name_enc, sex, created_by) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self.crypto.id_hash(code), e(code), e(first_name.strip()), e(last_name.strip()), int(sex), user_id))
        return cur.lastrowid

    def update_subject(self, subject_id, first_name, last_name, sex):
        e = self.crypto.enc
        with self.con:
            self.con.execute("UPDATE subjects SET first_name_enc=?, last_name_enc=?, sex=?, "
                             "updated_at=datetime('now','localtime') WHERE subject_id=?",
                             (e(first_name.strip()), e(last_name.strip()), int(sex), subject_id))

    def delete_subject(self, subject_id):
        with self.con:                                    # assessments ถูกลบตาม (ON DELETE CASCADE)
            self.con.execute("DELETE FROM subjects WHERE subject_id = ?", (subject_id,))

    def list_subjects(self, text=None):
        """รายชื่อผู้รับการประเมินทั้งหมด + สรุปการประเมินล่าสุด (ใหม่สุดก่อน)
        text: กรองด้วย ID (ตรงทั้งหมด) หรือบางส่วนของชื่อ-สกุล"""
        q = """
            SELECT s.*,
                   (SELECT COUNT(*) FROM assessments a WHERE a.subject_id = s.subject_id) AS n,
                   l.assessed_at AS last_at, l.predicted_class AS last_class, l.prob_json AS last_prob
            FROM subjects s
            LEFT JOIN assessments l ON l.assessment_id = (
                SELECT a.assessment_id FROM assessments a WHERE a.subject_id = s.subject_id
                ORDER BY a.assessed_at DESC, a.assessment_id DESC LIMIT 1)
            ORDER BY COALESCE(l.assessed_at, s.created_at) DESC"""
        text = (text or "").strip()
        code = idcode.normalize(text)
        want = self.crypto.id_hash(code) if idcode.is_valid(code) else None
        out = []
        for r in self.con.execute(q):
            if want and r["code_hash"] != want:
                continue
            d = self._subject_out(r)
            if text and not want and text not in f"{d['first_name']} {d['last_name']}":
                continue
            d.update(n=r["n"], last_at=r["last_at"], last_class=r["last_class"],
                     last_sar=json.loads(r["last_prob"]).get("sarcopenia") if r["last_prob"] else None)
            out.append(d)
        return out

    # ------------------------------------------------------------------ models / batches / assessments
    def ensure_model_version(self, m) -> int:
        r = self.con.execute("SELECT model_version_id FROM model_versions WHERE bundle_sha256 = ?",
                             (m.sha256,)).fetchone()
        if r:
            return r[0]
        with self.con:
            cur = self.con.execute(
                "INSERT INTO model_versions(task, fs_method, model_name, features_json, classes_json, threshold, "
                "bundle_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (m.task, m.fs, m.model_name, json.dumps(m.selected), json.dumps(m.class_keys), m.threshold, m.sha256))
        return cur.lastrowid

    def add_batch(self, file_name, file_sha256, n_rows, n_success, n_error, user_id) -> int:
        with self.con:
            cur = self.con.execute("INSERT INTO batches(file_name, file_sha256, n_rows, n_success, n_error, imported_by) "
                                   "VALUES (?, ?, ?, ?, ?, ?)", (file_name, file_sha256, n_rows, n_success, n_error, user_id))
        return cur.lastrowid

    def batch_exists(self, file_sha256) -> bool:
        return self.con.execute("SELECT 1 FROM batches WHERE file_sha256 = ?", (file_sha256,)).fetchone() is not None

    def add_assessment(self, subject_id, model_version_id, user_id, values: dict, probs: dict, predicted: str,
                       batch_id=None, note=None) -> int:
        with self.con:
            cur = self.con.execute(
                "INSERT INTO assessments(subject_id, model_version_id, batch_id, assessed_by, age_years, weight_kg, "
                "height_cm, bmi, grip_kg, calf_cm, prob_json, predicted_class, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (subject_id, model_version_id, batch_id, user_id, values["age_years"], values.get("weight_kg"),
                 values.get("height_cm"), values["bmi"], values["grip_kg"], values["calf_cm"],
                 json.dumps(probs), predicted, note))
        return cur.lastrowid

    def assessments_for(self, subject_id):
        rows = self.con.execute(
            "SELECT a.*, u.username, m.task FROM assessments a JOIN users u ON u.user_id = a.assessed_by "
            "JOIN model_versions m ON m.model_version_id = a.model_version_id "
            "WHERE subject_id = ? ORDER BY assessed_at, assessment_id", (subject_id,))
        out = []
        for r in rows:
            d = dict(r)
            d["probs"] = json.loads(d.pop("prob_json"))
            out.append(d)
        return out

    def assessment_count(self, subject_id) -> int:
        return self.con.execute("SELECT COUNT(*) FROM assessments WHERE subject_id = ?", (subject_id,)).fetchone()[0]

    # ------------------------------------------------------------------ audit
    def log(self, user_id, action, target=None):
        with self.con:
            self.con.execute("INSERT INTO audit_log(user_id, action, target) VALUES (?, ?, ?)", (user_id, action, target))

    def audit(self, limit=300):
        return [dict(r) for r in self.con.execute(
            "SELECT l.at, u.username, l.action, l.target FROM audit_log l LEFT JOIN users u ON u.user_id = l.user_id "
            "ORDER BY l.log_id DESC LIMIT ?", (limit,))]

    def close(self):
        self.con.close()
