"""page_batch.py — คัดกรองหลายคนจากไฟล์ Excel, บันทึกลงประวัติ และ export"""
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..core import config as C
from ..core import excel_io
from .theme import TONES
from .widgets import ComboBox, button, card, confirm, error, info, label


def save_path(parent, title, default_name) -> str | None:
    """เลือกที่บันทึก และเตือนถ้าเป็นโฟลเดอร์ที่ซิงก์คลาวด์"""
    path, _ = QFileDialog.getSaveFileName(parent, title, str(Path.home() / default_name), "Excel (*.xlsx)")
    if not path:
        return None
    if not path.lower().endswith(".xlsx"):
        path += ".xlsx"
    svc = excel_io.cloud_sync_warning(path)
    if svc and not confirm(parent, "โฟลเดอร์ซิงก์คลาวด์",
                           f"โฟลเดอร์นี้ซิงก์กับ {svc} ข้อมูลจะถูกอัปโหลดขึ้นคลาวด์\n"
                           "ซึ่งอาจขัดกับข้อกำหนดจริยธรรมการวิจัย\n\nยืนยันบันทึกที่นี่หรือไม่?"):
        return None
    return path


class ExportDialog(QDialog):
    def __init__(self, parent, default_name: str):
        super().__init__(parent)
        self.setWindowTitle("Export Excel")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 16)
        self.probs = QCheckBox("ความน่าจะเป็นทุกคลาส")
        self.probs.setChecked(True)
        v.addWidget(self.probs)
        v.addWidget(label("ไฟล์มีคอลัมน์ ID ใช้ map กับไฟล์ข้อมูลโครงการได้", "muted"))
        self.path = QLineEdit()
        self.path.setReadOnly(True)
        self.warn = QLabel()
        self.warn.setWordWrap(True)
        bg, fg, _ = TONES["warning"]
        self.warn.setStyleSheet(f"background:{bg};color:{fg};border-radius:6px;padding:6px;")
        self.warn.hide()
        pick = button("เลือกที่บันทึก…")
        pick.clicked.connect(lambda: self._pick(default_name))
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(pick)
        v.addSpacing(6)
        v.addLayout(row)
        v.addWidget(self.warn)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = button("ยกเลิก")
        cancel.clicked.connect(self.reject)
        self.ok = button("บันทึก", "primary")
        self.ok.clicked.connect(self._accept)
        btns.addWidget(cancel)
        btns.addWidget(self.ok)
        v.addLayout(btns)

    def _pick(self, default_name):
        path, _ = QFileDialog.getSaveFileName(self, "บันทึกผล", str(Path.home() / default_name), "Excel (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            self.path.setText(path)
            svc = excel_io.cloud_sync_warning(path)
            self.warn.setText(f"⚠ โฟลเดอร์นี้ซิงก์กับ {svc} — ข้อมูลจะขึ้นคลาวด์" if svc else "")
            self.warn.setVisible(bool(svc))

    def _accept(self):
        if not self.path.text():
            self.warn.setText("เลือกที่บันทึกไฟล์ก่อน")
            self.warn.show()
            return
        if excel_io.cloud_sync_warning(self.path.text()) and not confirm(
                self, "โฟลเดอร์ซิงก์คลาวด์", "ยืนยันบันทึกในโฟลเดอร์ที่ซิงก์คลาวด์หรือไม่?"):
            return
        self.accept()


class BatchPage(QWidget):
    COLS = ["แถว", "ชื่อ-สกุล", "ID", "อายุ", "BMI", "grip", "น่อง", "ผล", "สถานะ"]

    def __init__(self, session):
        super().__init__()
        self.s = session
        self.rows, self.file, self.sha, self.saved = [], None, None, False
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        drop = card("drop")
        dl = QHBoxLayout(drop)
        dl.setContentsMargins(12, 10, 12, 10)
        self.file_lbl = QLabel("ยังไม่ได้เลือกไฟล์")
        self.file_sub = label("ใช้ไฟล์จากปุ่มดาวน์โหลดต้นแบบ", "muted")
        col = QVBoxLayout()
        col.addWidget(self.file_lbl)
        col.addWidget(self.file_sub)
        dl.addLayout(col, 1)
        self.task = ComboBox()
        for t in self.s.models.tasks:
            self.task.addItem(C.TASK_LABELS[t], t)
        self.task.currentIndexChanged.connect(lambda: self.file and self.load(self.file))
        pick = button("เลือกไฟล์")
        pick.clicked.connect(self.choose)
        tpl = button("ดาวน์โหลดต้นแบบ")
        tpl.clicked.connect(self.template)
        for w in (self.task, pick, tpl):
            dl.addWidget(w)
        root.addWidget(drop)

        self.metrics = QGridLayout()
        self.metric_lbl = {}
        root.addLayout(self.metrics)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("ค้นหาชื่อ")
        self.search.textChanged.connect(self.fill_table)
        self.filter = ComboBox()
        self.filter.currentIndexChanged.connect(self.fill_table)
        self.save_btn = button("บันทึกลงประวัติ")
        self.save_btn.clicked.connect(self.save)
        self.export_btn = button("Export Excel", "primary")
        self.export_btn.clicked.connect(self.export)
        bottom.addWidget(self.search, 1)
        bottom.addWidget(self.filter)
        bottom.addWidget(self.save_btn)
        bottom.addWidget(self.export_btn)
        root.addLayout(bottom)
        self._buttons()

    def _buttons(self):
        has = any(not r["errors"] for r in self.rows)
        self.save_btn.setEnabled(has and not self.saved)
        self.export_btn.setEnabled(bool(self.rows))

    # ------------------------------------------------------------------ actions
    def template(self):
        path = save_path(self, "บันทึกไฟล์ต้นแบบ", "sarcopenia_template.xlsx")
        if path:
            excel_io.make_template(path)
            info(self, "ดาวน์โหลดต้นแบบ", f"บันทึกไฟล์ต้นแบบที่\n{path}")

    def choose(self):
        path, _ = QFileDialog.getOpenFileName(self, "เลือกไฟล์", str(Path.home()), "Excel (*.xlsx)")
        if path:
            self.load(path)

    def load(self, path):
        try:
            rows = excel_io.read_batch(path)
        except Exception as e:                                 # noqa: BLE001
            error(self, "อ่านไฟล์ไม่ได้", str(e))
            return
        self.file, self.sha, self.saved = path, excel_io.file_sha256(path), False
        task = self.task.currentData()
        good = [r for r in rows if not r["errors"]]
        if good:
            for r, res in zip(good, self.s.models.get(task).predict(good)):
                r.update(res)
        db = self.s.db
        for r in rows:
            if r["errors"]:
                r["status"] = ", ".join(r["errors"])
                continue
            subj = db.find_subject(r["code"])
            r["subject"] = subj
            r["status"] = f"ครั้งที่ {db.assessment_count(subj['subject_id']) + 1}" if subj else "คนใหม่"
        self.rows = rows
        n_new = sum(r.get("status") == "คนใหม่" for r in rows)
        n_old = sum(1 for r in rows if not r["errors"] and r.get("subject"))
        n_bad = sum(1 for r in rows if r["errors"])
        self.file_lbl.setText(Path(path).name)
        self.file_sub.setText(f"{len(rows)} แถว · คนใหม่ {n_new} · มีในระบบ {n_old} · ข้อมูลผิด {n_bad}"
                              + (" · ⚠ ไฟล์นี้เคยบันทึกแล้ว" if db.batch_exists(self.sha) else ""))
        self._metrics(task)
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItem("ทุกผล", None)
        for k in C.DISPLAY_ORDER[task]:
            self.filter.addItem(C.CLASS_TH[k], k)
        self.filter.addItem("ข้อมูลผิด", "error")
        self.filter.blockSignals(False)
        self.fill_table()
        self._buttons()

    def _metrics(self, task):
        while self.metrics.count():
            w = self.metrics.takeAt(0).widget()
            if w:
                w.deleteLater()
        keys = C.DISPLAY_ORDER[task]
        for i, k in enumerate(keys):
            f = card("metric")
            v = QVBoxLayout(f)
            v.setContentsMargins(10, 6, 10, 6)
            v.addWidget(label(C.CLASS_TH[k]))
            n = QLabel(str(sum(r.get("predicted") == k for r in self.rows)))
            n.setStyleSheet("font-size:16pt;font-weight:600;")
            v.addWidget(n)
            self.metrics.addWidget(f, 0, i)

    def fill_table(self):
        q = self.search.text().strip()
        flt = self.filter.currentData()
        shown = [r for r in self.rows
                 if (not q or q in f"{r['first_name']} {r['last_name']}")
                 and (flt is None or (flt == "error" and r["errors"]) or r.get("predicted") == flt)]
        self.table.setRowCount(len(shown))
        for i, r in enumerate(shown):
            pred = r.get("predicted")
            cells = [str(r["row"]), f"{r['first_name']} {r['last_name']}",
                     r["code"] or "—",
                     _f(r.get("age_years"), 0), _f(r.get("bmi")), _f(r.get("grip_kg")), _f(r.get("calf_cm")),
                     f"{C.CLASS_TH[pred]} {r['probs'][pred]:.0%}" if pred else "—", r.get("status", "")]
            for j, text in enumerate(cells):
                it = QTableWidgetItem(text)
                if j == 7 and pred:
                    bg, fg, _ = TONES[C.CLASS_TONE[pred]]
                    it.setBackground(QColor(bg))
                    it.setForeground(QColor(fg))
                if r["errors"] and j in (2, 8):
                    it.setForeground(QColor(TONES["danger"][1]))
                self.table.setItem(i, j, it)

    def save(self):
        good = [r for r in self.rows if not r["errors"]]
        if not good:
            return
        db, uid = self.s.db, self.s.user_id
        if db.batch_exists(self.sha) and not confirm(self, "ไฟล์ซ้ำ", "ไฟล์นี้เคยบันทึกแล้ว บันทึกซ้ำหรือไม่?"):
            return
        if not confirm(self, "บันทึกลงประวัติ", f"บันทึกผลของ {len(good)} คนลงประวัติ?"):
            return
        model = self.s.models.get(self.task.currentData())
        mv = db.ensure_model_version(model)
        bid = db.add_batch(Path(self.file).name, self.sha, len(self.rows), len(good), len(self.rows) - len(good), uid)
        for r in good:
            subj = db.find_subject(r["code"])
            if subj is None:
                sid = db.create_subject(r["code"], r["first_name"], r["last_name"], r["sex"], uid)
            else:
                sid = subj["subject_id"]
            db.add_assessment(sid, mv, uid, r, r["probs"], r["predicted"], batch_id=bid)
        db.log(uid, "import", f"batch_id={bid} rows={len(good)}")
        self.saved = True
        self._buttons()
        info(self, "บันทึกแล้ว", f"บันทึกผล {len(good)} คนลงประวัติ")

    def export(self):
        if not self.rows:
            return
        default = Path(self.file).stem + "_result.xlsx" if self.file else "result.xlsx"
        dlg = ExportDialog(self, default)
        if dlg.exec() != QDialog.Accepted:
            return
        excel_io.export_results(dlg.path.text(), self.rows, self.task.currentData(), dlg.probs.isChecked())
        self.s.db.log(self.s.user_id, "export", f"rows={len(self.rows)} file={Path(dlg.path.text()).name}")
        info(self, "Export", f"บันทึกไฟล์แล้ว\n{dlg.path.text()}")


def _f(v, nd=1):
    return "—" if v is None else f"{v:.{nd}f}"
