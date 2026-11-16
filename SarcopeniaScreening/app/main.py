"""
main.py — จุดเริ่มแอปคัดกรองภาวะมวลกล้ามเนื้อน้อย (Windows, ทำงานออฟไลน์)

วิธีรัน (จากโฟลเดอร์โปรเจกต์ หลัง activate .venv):
    python -m app.build_models     # ครั้งแรก/เมื่อเทรนโมเดลใหม่: สร้าง app/models/*.joblib
    python -m app.main
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .core import config as C
from .core.db import Database, KeyMismatchError
from .core.models import ModelService
from .core.security import KeyMissingError
from .ui.login import LoginDialog, UserDialog
from .ui.main_window import MainWindow, Session
from .ui.theme import apply_light_theme


def main():
    if sys.platform == "win32":                        # ให้ taskbar ใช้ไอคอนของแอป ไม่ใช่ไอคอน Python
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("UP.FF69.SarcopeniaScreening")
        except Exception:                              # noqa: BLE001
            pass
    app = QApplication(sys.argv)
    if C.ICON.exists():
        app.setWindowIcon(QIcon(str(C.ICON)))
    app.setApplicationName(C.APP_TITLE)
    apply_light_theme(app)
    app.setQuitOnLastWindowClosed(False)          # ออกจากระบบแล้วกลับหน้า login ได้

    models = ModelService()
    if not models.tasks:
        QMessageBox.critical(None, C.APP_TITLE, "ไม่พบโมเดล\n" + "\n".join(models.errors)
                             + "\n\nรัน python -m app.build_models ก่อน")
        return 1
    if models.errors:
        QMessageBox.warning(None, C.APP_TITLE, "\n".join(models.errors))

    try:
        db = Database()
    except (KeyMissingError, KeyMismatchError) as e:
        QMessageBox.critical(None, C.APP_TITLE,
                             f"{e}\n\nเปิดฐานข้อมูลไม่ได้ ข้อมูลยังอยู่ที่\n{C.db_path()}\n"
                             "แต่ต้องใช้กุญแจเดิมของบัญชี Windows นี้ (ติดต่อผู้ดูแลระบบ)")
        return 1

    if db.user_count() == 0 and not UserDialog(db, first_admin=True).exec():
        return 0

    windows = []

    def login():
        dlg = LoginDialog(db)
        if not dlg.exec():
            app.quit()
            return
        win = MainWindow(Session(db, models, dlg.user))
        win.logged_out.connect(login)
        windows[:] = [win]
        win.show()

    login()
    if not windows:
        return 0
    code = app.exec()
    db.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
