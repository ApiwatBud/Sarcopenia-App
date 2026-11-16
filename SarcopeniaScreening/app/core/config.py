"""
config.py — ค่าคงที่ของแอป: ตำแหน่งไฟล์, ชื่อคลาส, ช่วงค่าที่รับได้

ฐานข้อมูลเก็บที่ %LOCALAPPDATA%\\FF69Sarcopenia\\screening.db
(LOCALAPPDATA ไม่ซิงก์ขึ้น OneDrive และไม่ roam ตามบัญชีโดเมน)
ตั้งค่า FF69_DATA_DIR เพื่อเปลี่ยนตำแหน่ง (ใช้ตอนทดสอบ)
"""
import os
import sys
from pathlib import Path

APP_NAME = "FF69Sarcopenia"
APP_TITLE = "Sarcopenia Screening"

# โฟลเดอร์ของแอป (รองรับตอนแพ็กเป็น .exe ด้วย PyInstaller)
if getattr(sys, "frozen", False):
    APP_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    APP_DIR = Path(__file__).resolve().parent.parent

MODELS_DIR = APP_DIR / "models"
SCHEMA_SQL = APP_DIR / "schema.sql"
ICON = APP_DIR / "assets" / "icon.ico"


def data_dir() -> Path:
    base = os.environ.get("FF69_DATA_DIR") or os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    d = Path(base) if os.environ.get("FF69_DATA_DIR") else Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "screening.db"


TASKS = ["y3", "y2"]
TASK_LABELS = {"y3": "3 กลุ่ม (y3)", "y2": "2 กลุ่ม (y2)"}

# ลำดับคลาสตาม src/data.py: y3 = 0 none, 1 sarcopenia, 2 possible ; y2 = 1 sarcopenia, 0 อื่น ๆ
CLASS_KEYS = {"y3": {0: "normal", 1: "sarcopenia", 2: "possible"},
              "y2": {0: "other", 1: "sarcopenia"}}
CLASS_TH = {"normal": "ปกติ", "possible": "Possible", "sarcopenia": "Sarcopenia", "other": "ไม่เป็น"}
CLASS_TONE = {"normal": "success", "other": "success", "possible": "warning", "sarcopenia": "danger"}
DISPLAY_ORDER = {"y3": ["normal", "possible", "sarcopenia"], "y2": ["other", "sarcopenia"]}

# feature ของโมเดล -> ชื่อช่องข้อมูลในแอป
FEATURE_TO_INPUT = {"gender": "sex", "age": "age_years", "BMI": "bmi", "grip ave": "grip_kg", "Calf circum": "calf_cm"}
FEATURE_TH = {"gender": "เพศ", "age": "อายุ", "BMI": "BMI", "grip ave": "แรงบีบมือ", "Calf circum": "รอบน่อง"}

# ช่วงค่าที่รับได้ (ตรงกับ CHECK ใน schema.sql)
RANGES = {"age_years": (40, 120), "weight_kg": (20, 200), "height_cm": (100, 220),
          "bmi": (10, 60), "grip_kg": (0, 80), "calf_cm": (15, 60)}
FIELD_TH = {"age_years": "อายุ (ปี)", "weight_kg": "น้ำหนัก (kg)", "height_cm": "ส่วนสูง (cm)",
            "bmi": "BMI", "grip_kg": "แรงบีบมือ (kg)", "calf_cm": "รอบน่อง (cm)"}

SEX_TH = {1: "หญิง", 2: "ชาย"}          # ตรงกับรหัสในข้อมูลวิจัย

MIN_PASSWORD = 8
DISCLAIMER = "ผลจากโมเดลใช้เพื่อคัดกรองเท่านั้น ไม่ใช่การวินิจฉัย"
