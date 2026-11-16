# Sarcopenia Screening

โปรแกรม Windows สำหรับคัดกรองภาวะมวลกล้ามเนื้อน้อย (sarcopenia) ในผู้สูงอายุ
ทำงานออฟไลน์ ข้อมูลเก็บในเครื่องเท่านั้น — โครงการ FF69 มหาวิทยาลัยพะเยา

> ผลจากโมเดลใช้เพื่อคัดกรองเท่านั้น ไม่ใช่การวินิจฉัย

## ติดตั้งบนเครื่องใหม่

ต้องมี: Windows 10/11 64 บิต, [Git for Windows](https://git-scm.com/download/win), อินเทอร์เน็ต (ตอนติดตั้งครั้งเดียว)
ไม่ต้องมีสิทธิ์ admin และไม่ต้องติดตั้ง Python เอง

```
git clone <url ของ repo>
cd SarcopeniaScreening
setup.bat
```

`setup.bat` จะ
1. ติดตั้ง Python 3.11 (ถ้ายังไม่มี)
2. สร้าง `.venv` และติดตั้งไลบรารีตาม `requirements-runtime.txt`
3. ทดสอบโปรแกรม (`run_app.py --selftest`)
4. สร้าง shortcut "Sarcopenia Screening" บน Desktop และ Start Menu

เปิดโปรแกรมครั้งแรกจะให้สร้างบัญชีผู้ดูแล (admin)

## เปิดโปรแกรม
- shortcut "Sarcopenia Screening" หรือ
- ดับเบิลคลิก `run_app.bat`

## อัปเดต
```
git pull
setup.bat
```
ฐานข้อมูลเดิมไม่หาย (อยู่นอกโฟลเดอร์โปรแกรม)

## ฐานข้อมูล
- SQLite (มากับ Python) สร้างอัตโนมัติที่ `%LOCALAPPDATA%\FF69Sarcopenia\screening.db`
- แยกกันในแต่ละเครื่อง / แต่ละบัญชี Windows
- ชื่อ นามสกุล และ ID เข้ารหัสในฐานข้อมูล กุญแจอยู่ใน Windows Credential Manager ของบัญชีนั้น
- โครงสร้างตาราง: `app/schema.sql`

## โครงสร้าง
| | |
|---|---|
| `run_app.py` | จุดเริ่มโปรแกรม (`--selftest <ไฟล์>` ตรวจการติดตั้ง) |
| `app/main.py` | เริ่ม GUI, login |
| `app/core/` | ฐานข้อมูล, การเข้ารหัส, โมเดล, Excel, รูปแบบ ID |
| `app/ui/` | หน้าจอ: รายคน, หลายคน, ประวัติ, ผู้ดูแล |
| `app/models/` | โมเดลของแอป (y3: SHAP+XGBoost, y2: SHAP+EBM) สร้างจาก pipeline วิจัย |
| `app/test_data/` | ไฟล์ Excel ทดสอบ (ข้อมูลสมมติ) |

ID ผู้รับการประเมินใช้รูปแบบเดียวกับไฟล์ข้อมูลโครงการ: ตัวอักษร 1–3 ตัว + ตัวเลข 2–4 หลัก เช่น `SC0020`, `MS101`

## ข้อควรระวัง
- repo นี้ควรเป็น **private**
- ห้าม commit ข้อมูลผู้รับการประเมิน ข้อมูลวิจัย หรือไฟล์ export (`.gitignore` กันไว้แล้ว) — ตรวจ `git status` ก่อน commit ทุกครั้ง
- ไลบรารีใน `requirements-runtime.txt` ต้องเป็นรุ่นเดียวกับที่ใช้สร้างโมเดล ห้ามอัปเกรดเอง
