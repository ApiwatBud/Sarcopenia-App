"""
run_app.py — จุดเริ่มสำหรับแพ็กเป็น .exe (PyInstaller) และใช้รันปกติได้ด้วย: python run_app.py

ตัวเลือก
    --selftest <ไฟล์ผล>   ตรวจว่าแพ็กครบ (โหลดโมเดล, ทำนาย 1 แถว, มี schema, โหลด Qt) แล้วเขียนผลลงไฟล์
                         ไม่แตะฐานข้อมูลหรือกุญแจ ใช้หลัง build (.exe แบบไม่มีหน้าต่าง console จึง print ไม่ได้)
"""
import sys
import traceback
from datetime import datetime


def selftest(out_path):
    lines = []
    try:
        from PySide6.QtWidgets import QWidget  # noqa: F401
        from app.core import config as C
        from app.core.models import ModelService
        lines.append(f"schema.sql: {'OK' if C.SCHEMA_SQL.exists() else 'MISSING'}")
        ms = ModelService()
        for t in ms.tasks:
            m = ms.get(t)
            r = m.predict([{"sex": 1, "age_years": 70, "bmi": 21, "grip_kg": 18, "calf_cm": 31}])[0]
            lines.append(f"{t}: {m.fs}+{m.model_name} -> {r['predicted']} "
                         f"{ {k: round(v, 3) for k, v in r['probs'].items()} } factors={r['factors']}")
        lines += [f"ERROR {e}" for e in ms.errors]
        ok = C.SCHEMA_SQL.exists() and len(ms.tasks) == len(C.TASKS) and not ms.errors
    except Exception:                                                    # noqa: BLE001
        lines.append(traceback.format_exc())
        ok = False
    lines.append("SELFTEST " + ("PASS" if ok else "FAIL"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1


def _excepthook(exc_type, exc, tb):
    """ข้อผิดพลาดที่ไม่คาดคิด: เขียน log ในโฟลเดอร์ข้อมูล แล้วแจ้งผู้ใช้ (ไม่มี console ให้เห็น)"""
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        from app.core import config as C
        log = C.data_dir() / "error.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{text}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, C.APP_TITLE, f"เกิดข้อผิดพลาด: {exc}\n\nรายละเอียดบันทึกที่\n{log}")
    except Exception:                                                    # noqa: BLE001
        pass


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        sys.exit(selftest(sys.argv[2]))
    sys.excepthook = _excepthook
    from app.main import main
    sys.exit(main())
