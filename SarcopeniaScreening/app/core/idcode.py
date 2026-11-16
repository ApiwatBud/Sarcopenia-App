"""
idcode.py — รหัสผู้รับการประเมิน (ID) รูปแบบเดียวกับคอลัมน์ "ID Number" ในไฟล์ข้อมูลที่ใช้ train

รูปแบบ: ตัวอักษรอังกฤษ 1–3 ตัว (รหัสพื้นที่) ตามด้วยตัวเลข 2–4 หลัก เช่น SC0020, MS101, NR045, M12
- เก็บเป็นข้อความเสมอ (เลข 0 นำหน้ามีความหมาย: SC0020 ≠ SC20)
- ไม่สนตัวพิมพ์เล็ก/ใหญ่ และช่องว่าง: " sc 0020 " -> "SC0020"
"""
import re

PATTERN = re.compile(r"^[A-Z]{1,3}\d{2,4}$")
EXAMPLE = "SC0020"


def normalize(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:          # NaN จาก Excel
        return ""
    return re.sub(r"[\s\-_]", "", str(value)).upper()


def is_valid(value) -> bool:
    return bool(PATTERN.match(normalize(value)))


def problem(value) -> str | None:
    """ข้อความบอกว่า ID ผิดอย่างไร (None = ถูกต้อง)"""
    d = normalize(value)
    if not d:
        return "กรอก ID"
    if not PATTERN.match(d):
        return f"ID ต้องเป็นตัวอักษร 1–3 ตัว ตามด้วยตัวเลข 2–4 หลัก เช่น {EXAMPLE} (ตอนนี้ “{d}”)"
    return None
