"""
excel_io.py — ไฟล์ต้นแบบ, อ่านไฟล์หลายคน, export ผล และตรวจโฟลเดอร์ที่ซิงก์คลาวด์
"""
import hashlib
import os
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import config as C
from . import idcode

# (key, หัวคอลัมน์ในไฟล์, ตัวอย่าง)
TEMPLATE_COLUMNS = [
    ("code", "ID", "ตัวอย่าง"),
    ("first_name", "ชื่อ", "สมศรี"),
    ("last_name", "นามสกุล", "ใจดี"),
    ("sex", "เพศ", "หญิง"),
    ("age_years", "อายุ (ปี)", 72),
    ("weight_kg", "น้ำหนัก (kg)", 48.5),
    ("height_cm", "ส่วนสูง (cm)", 156),
    ("grip_kg", "แรงบีบมือ (kg)", 15.2),
    ("calf_cm", "รอบน่อง (cm)", 29.5),
]
SEX_PARSE = {"หญิง": 1, "ญ": 1, "f": 1, "female": 1, "1": 1, "ชาย": 2, "ช": 2, "m": 2, "male": 2, "2": 2}
MAX_ROWS = 5000
HEAD_FILL = PatternFill("solid", fgColor="E6F1FB")


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cloud_sync_warning(path) -> str | None:
    """คืนชื่อบริการถ้าโฟลเดอร์อยู่ใต้โฟลเดอร์ที่ซิงก์คลาวด์ (ตรวจจากตัวแปรระบบและชื่อโฟลเดอร์)"""
    p = str(Path(path).resolve()).lower()
    for env in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = os.environ.get(env)
        if root and p.startswith(str(Path(root).resolve()).lower()):
            return "OneDrive"
    for name, label in (("onedrive", "OneDrive"), ("google drive", "Google Drive"), ("googledrive", "Google Drive"),
                        ("dropbox", "Dropbox"), ("icloud", "iCloud")):
        if name in p:
            return label
    return None


# ---------------------------------------------------------------------- template
def make_template(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ข้อมูล"
    for j, (_, head, example) in enumerate(TEMPLATE_COLUMNS, 1):
        c = ws.cell(1, j, head)
        c.font, c.fill = Font(bold=True), HEAD_FILL
        ws.cell(2, j, example).font = Font(color="888888", italic=True)
        ws.column_dimensions[get_column_letter(j)].width = 18
    for r in range(2, MAX_ROWS + 2):                       # ID เป็นข้อความ กัน Excel ตัดเลข 0 นำหน้า
        ws.cell(r, 1).number_format = "@"
    ws.freeze_panes = "A2"

    last = MAX_ROWS + 1
    dv_sex = DataValidation(type="list", formula1='"หญิง,ชาย"', allow_blank=True,
                            error="เลือก หญิง หรือ ชาย", errorTitle="เพศ", showErrorMessage=True)
    ws.add_data_validation(dv_sex)
    dv_sex.add(f"D2:D{last}")
    for j, (key, head, _) in enumerate(TEMPLATE_COLUMNS, 1):
        if key in C.RANGES:
            lo, hi = C.RANGES[key]
            dv = DataValidation(type="decimal", operator="between", formula1=str(lo), formula2=str(hi),
                                allow_blank=True, showErrorMessage=True, errorTitle=head,
                                error=f"ต้องเป็นตัวเลขระหว่าง {lo} ถึง {hi}")
            ws.add_data_validation(dv)
            col = get_column_letter(j)
            dv.add(f"{col}2:{col}{last}")

    info = wb.create_sheet("คำอธิบาย")
    lines = [("วิธีกรอก", ""),
             ("1", "กรอก 1 แถวต่อ 1 คน เริ่มแถวที่ 2 (ลบแถวตัวอย่างสีเทาออกก่อน)"),
             ("2", f"ID รูปแบบเดียวกับไฟล์ข้อมูลโครงการ: ตัวอักษร 1–3 ตัว + ตัวเลข 2–4 หลัก เช่น {idcode.EXAMPLE}, MS101"),
             ("3", "เพศ เลือก หญิง หรือ ชาย"),
             ("4", "แรงบีบมือ = ค่าเฉลี่ย (kg) ตามวิธีวัดของโครงการ"),
             ("5", "อย่าเปลี่ยนชื่อหรือลำดับหัวคอลัมน์"),
             ("", ""), ("ช่วงค่าที่รับได้", "")]
    lines += [(C.FIELD_TH[k], f"{lo} – {hi}") for k, (lo, hi) in C.RANGES.items() if k != "bmi"]
    for i, (a, b) in enumerate(lines, 1):
        info.cell(i, 1, a).font = Font(bold=not b)
        info.cell(i, 2, b)
    info.column_dimensions["A"].width = 20
    info.column_dimensions["B"].width = 70
    wb.save(path)


# ---------------------------------------------------------------------- read
def _num(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return "bad"


def read_batch(path) -> list[dict]:
    """อ่านไฟล์ตามต้นแบบ -> list ของ {row, values..., errors[]}"""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows, [])]
    expected = [h for _, h, _ in TEMPLATE_COLUMNS]
    missing = [h for h in expected if h not in header]
    if missing:
        raise ValueError("ไม่พบคอลัมน์: " + ", ".join(missing) + " (ใช้ไฟล์จากปุ่มดาวน์โหลดต้นแบบ)")
    idx = {key: header.index(h) for key, h, _ in TEMPLATE_COLUMNS}

    out = []
    for n, row in enumerate(rows, start=2):
        if row is None or all(v is None or str(v).strip() == "" for v in row):
            continue
        if n - 1 > MAX_ROWS:
            raise ValueError(f"ไฟล์มีเกิน {MAX_ROWS} แถว")
        get = lambda k: row[idx[k]] if idx[k] < len(row) else None          # noqa: E731
        r = {"row": n, "errors": []}
        code = idcode.normalize(get("code"))
        r["code"] = code
        if not idcode.is_valid(code):
            r["errors"].append("ID ไม่ถูกต้อง")
        r["first_name"] = str(get("first_name") or "").strip()
        r["last_name"] = str(get("last_name") or "").strip()
        if not r["first_name"] or not r["last_name"]:
            r["errors"].append("ไม่มีชื่อ-สกุล")
        sex = SEX_PARSE.get(str(get("sex") or "").strip().lower())
        r["sex"] = sex
        if sex is None:
            r["errors"].append("เพศไม่ถูกต้อง")
        for key in ("age_years", "weight_kg", "height_cm", "grip_kg", "calf_cm"):
            v = _num(get(key))
            lo, hi = C.RANGES[key]
            if v is None or v == "bad" or not (lo <= v <= hi):
                r["errors"].append(f"{C.FIELD_TH[key]} ไม่ถูกต้อง")
                v = None
            r[key] = v
        if r["weight_kg"] and r["height_cm"]:
            r["bmi"] = round(r["weight_kg"] / (r["height_cm"] / 100) ** 2, 2)
            lo, hi = C.RANGES["bmi"]
            if not lo <= r["bmi"] <= hi:
                r["errors"].append("BMI นอกช่วง")
        else:
            r["bmi"] = None
        out.append(r)
    wb.close()
    # ID ซ้ำในไฟล์เดียวกัน
    seen = {}
    for r in out:
        if r["code"] in seen and "ID ไม่ถูกต้อง" not in r["errors"]:
            r["errors"].append(f"ID ซ้ำกับแถว {seen[r['code']]}")
        seen.setdefault(r["code"], r["row"])
    return out


# ---------------------------------------------------------------------- export
def export_results(path, rows: list[dict], task: str, include_probs: bool):
    """rows: dict ที่มี code, first_name, last_name, sex, ค่าวัด, predicted, probs, status"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ผลคัดกรอง"
    keys = C.DISPLAY_ORDER[task]
    head = ["ID", "ชื่อ", "นามสกุล", "เพศ", "อายุ (ปี)", "น้ำหนัก (kg)", "ส่วนสูง (cm)", "BMI",
            "แรงบีบมือ (kg)", "รอบน่อง (cm)", "ผล"]
    if include_probs:
        head += [f"ความน่าจะเป็น {C.CLASS_TH[k]}" for k in keys]
    head += ["สถานะ"]
    for j, h in enumerate(head, 1):
        c = ws.cell(1, j, h)
        c.font, c.fill, c.alignment = Font(bold=True), HEAD_FILL, Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(j)].width = 16
    for i, r in enumerate(rows, 2):
        vals = [idcode.normalize(r.get("code")), r.get("first_name"), r.get("last_name"),
                C.SEX_TH.get(r.get("sex"), ""), r.get("age_years"), r.get("weight_kg"), r.get("height_cm"),
                r.get("bmi"), r.get("grip_kg"), r.get("calf_cm"),
                C.CLASS_TH.get(r.get("predicted"), "") if r.get("predicted") else ""]
        if include_probs:
            vals += [round(r["probs"][k], 4) if r.get("probs") else None for k in keys]
        vals += [r.get("status", "")]
        for j, v in enumerate(vals, 1):
            ws.cell(i, j, v)
        ws.cell(i, 1).number_format = "@"
    ws.freeze_panes = "A2"
    note = wb.create_sheet("หมายเหตุ")
    note["A1"] = C.DISCLAIMER
    note["A2"] = f"โมเดล: {C.TASK_LABELS[task]}"
    wb.save(path)
