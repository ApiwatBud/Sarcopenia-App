"""page_single.py — คัดกรองรายคน"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..core import config as C
from ..core import idcode
from .widgets import Badge, ComboBox, ProbBars, button, card, error, field, label, set_invalid


def read_values(edits: dict) -> tuple[dict, list]:
    """อ่านค่าตัวเลขจากช่องกรอก -> (values, errors)"""
    vals, errs = {}, []
    for key, e in edits.items():
        txt = e.text().strip().replace(",", "")
        lo, hi = C.RANGES[key]
        try:
            v = float(txt)
            ok = lo <= v <= hi
        except ValueError:
            v, ok = None, False
        set_invalid(e, not ok)
        if not ok:
            errs.append(f"{C.FIELD_TH[key]} ต้องอยู่ระหว่าง {lo}–{hi}")
        vals[key] = v
    return vals, errs


class SinglePage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.s = session
        self.subject = None
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        # ID + ค้นหา (ค้นเมื่อกด Enter / ค้นหา / ออกจากช่อง)
        self.nid = QLineEdit()
        self.nid.setPlaceholderText(f"ID เช่น {idcode.EXAMPLE}")
        self.nid.setMaxLength(12)
        self.nid.textEdited.connect(self._nid_edited)
        self.nid.editingFinished.connect(self._nid_finished)
        self.nid_ok = QLabel()
        find = button("ค้นหา")
        find.clicked.connect(self.lookup)
        row = QHBoxLayout()
        row.addWidget(self.nid, 1)
        row.addWidget(self.nid_ok)
        row.addWidget(find)
        root.addWidget(label("ID"))
        root.addLayout(row)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("background:#E6F1FB;color:#185FA5;border-radius:6px;padding:7px 9px;")
        self.banner.hide()
        root.addWidget(self.banner)

        # ข้อมูลส่วนตัว + ค่าวัด
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        self.first, self.last = QLineEdit(), QLineEdit()
        self.sex = ComboBox()
        for code, name in C.SEX_TH.items():
            self.sex.addItem(name, code)
        num = QDoubleValidator(0, 300, 2)
        self.edits = {}
        for key in ("age_years", "weight_kg", "height_cm", "grip_kg", "calf_cm"):
            e = QLineEdit()
            e.setValidator(num)
            e.textEdited.connect(lambda _=None, e=e: set_invalid(e, False))
            self.edits[key] = e
        self.edits["weight_kg"].textEdited.connect(self._bmi)
        self.edits["height_cm"].textEdited.connect(self._bmi)
        self.bmi = QLineEdit()
        self.bmi.setReadOnly(True)
        cells = [("ชื่อ", self.first), ("นามสกุล", self.last), ("เพศ", self.sex),
                 ("อายุ (ปี)", self.edits["age_years"]), ("น้ำหนัก (kg)", self.edits["weight_kg"]),
                 ("ส่วนสูง (cm)", self.edits["height_cm"]), ("BMI (คำนวณให้)", self.bmi),
                 ("แรงบีบมือ (kg)", self.edits["grip_kg"]), ("รอบน่อง (cm)", self.edits["calf_cm"])]
        for i, (cap, w) in enumerate(cells):
            g.addWidget(field(cap, w), i // 3, i % 3)
        root.addLayout(g)

        self.err = label("", "error")
        self.err.setWordWrap(True)
        root.addWidget(self.err)
        act = QHBoxLayout()
        self.go = button("คัดกรองและบันทึก", "primary")
        self.go.clicked.connect(self.run)
        clear = button("ล้าง")
        clear.clicked.connect(self.clear)
        self.task = ComboBox()
        for t in self.s.models.tasks:
            self.task.addItem(C.TASK_LABELS[t], t)
        act.addWidget(self.go)
        act.addWidget(clear)
        act.addStretch(1)
        act.addWidget(self.task)
        root.addLayout(act)

        # ผลลัพธ์
        self.result = card()
        rl = QHBoxLayout(self.result)
        rl.setContentsMargins(16, 12, 16, 12)
        left = QVBoxLayout()
        left.setAlignment(Qt.AlignCenter)
        cap = label("ผล")
        cap.setAlignment(Qt.AlignCenter)
        self.badge = Badge()
        self.badge.setAlignment(Qt.AlignCenter)
        self.pct = QLabel()
        self.pct.setAlignment(Qt.AlignCenter)
        self.pct.setStyleSheet("font-size:20pt;font-weight:600;")
        for w in (cap, self.badge, self.pct):
            left.addWidget(w)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(150)
        right = QVBoxLayout()
        self.bars = ProbBars()
        self.factors = label("", "muted")
        self.factors.setWordWrap(True)
        right.addWidget(self.bars)
        right.addWidget(self.factors)
        right.addWidget(label(C.DISCLAIMER, "muted"))
        rl.addWidget(lw)
        rl.addLayout(right, 1)
        self.result.hide()
        root.addWidget(self.result)
        root.addStretch(1)

    # ------------------------------------------------------------------ helpers
    def _nid_edited(self):
        """ระหว่างพิมพ์: แสดง ✓ เมื่อรูปแบบถูก (ยังไม่ค้น)"""
        self.banner.hide()
        self.subject = None
        self.err.setText("")
        set_invalid(self.nid, False)
        ok = idcode.is_valid(self.nid.text())
        self.nid_ok.setText("✓" if ok else "")
        self.nid_ok.setStyleSheet("color:#3B6D11;font-size:13pt;")

    def _nid_finished(self):
        """กด Enter หรือออกจากช่อง: ค้นหา (ถ้ากรอกไว้)"""
        if self.nid.text().strip() and self.subject is None:
            self.lookup()

    def _bmi(self):
        try:
            w = float(self.edits["weight_kg"].text())
            h = float(self.edits["height_cm"].text()) / 100
            self.bmi.setText(f"{w / h ** 2:.1f}" if h > 0 else "")
        except ValueError:
            self.bmi.setText("")

    def lookup(self):
        d = idcode.normalize(self.nid.text())
        if not idcode.is_valid(d):
            self.err.setText(idcode.problem(d))
            set_invalid(self.nid, True)
            return
        self.nid.setText(d)
        self.err.setText("")
        s = self.s.db.find_subject(d)
        self.subject = s
        if s:
            n = self.s.db.assessment_count(s["subject_id"])
            hist = self.s.db.assessments_for(s["subject_id"])
            last = hist[-1]["assessed_at"][:10] if hist else "-"
            self.first.setText(s["first_name"])
            self.last.setText(s["last_name"])
            self.sex.setCurrentIndex(self.sex.findData(s["sex"]))
            self.banner.setText(f"พบในระบบ: {s['first_name']} {s['last_name']} · ประเมินแล้ว {n} ครั้ง "
                                f"(ล่าสุด {last}) — จะบันทึกเป็นครั้งที่ {n + 1}")
            self.s.db.log(self.s.user_id, "view_subject", f"subject_id={s['subject_id']}")
        else:
            self.banner.setText("ยังไม่มีในระบบ — จะสร้างผู้รับการประเมินใหม่")
        self.banner.show()

    def prefill(self, code):
        self.clear()
        self.nid.setText(idcode.normalize(code))
        self.lookup()

    def clear(self):
        for e in [self.nid, self.first, self.last, self.bmi, *self.edits.values()]:
            e.clear()
            set_invalid(e, False)
        self.nid_ok.setText("")
        self.banner.hide()
        self.result.hide()
        self.err.setText("")
        self.subject = None

    # ------------------------------------------------------------------ run
    def run(self):
        errs = []
        d = idcode.normalize(self.nid.text())
        if not idcode.is_valid(d):
            errs.append(idcode.problem(d))
        if not self.first.text().strip() or not self.last.text().strip():
            errs.append("กรอกชื่อและนามสกุล")
        vals, verrs = read_values(self.edits)
        errs += verrs
        if not errs:
            vals["bmi"] = round(vals["weight_kg"] / (vals["height_cm"] / 100) ** 2, 2)
            lo, hi = C.RANGES["bmi"]
            if not lo <= vals["bmi"] <= hi:
                errs.append(f"BMI {vals['bmi']:.1f} อยู่นอกช่วง {lo}–{hi} ตรวจน้ำหนักและส่วนสูง")
        if errs:
            self.err.setText(" · ".join(errs))
            return
        self.err.setText("")
        vals["sex"] = self.sex.currentData()
        task = self.task.currentData()
        model = self.s.models.get(task)
        try:
            res = model.predict([vals])[0]
        except Exception as e:                                   # noqa: BLE001
            error(self, "ทำนายไม่ได้", str(e))
            return

        db, uid = self.s.db, self.s.user_id
        subject = self.subject or db.find_subject(d)
        if subject is None:
            sid = db.create_subject(d, self.first.text(), self.last.text(), vals["sex"], uid)
            db.log(uid, "create_subject", f"subject_id={sid}")
        else:
            sid = subject["subject_id"]
            if (subject["first_name"], subject["last_name"], subject["sex"]) != \
                    (self.first.text().strip(), self.last.text().strip(), vals["sex"]):
                db.update_subject(sid, self.first.text(), self.last.text(), vals["sex"])
                db.log(uid, "update_subject", f"subject_id={sid}")
        mv = db.ensure_model_version(model)
        aid = db.add_assessment(sid, mv, uid, vals, res["probs"], res["predicted"])
        db.log(uid, "assess", f"subject_id={sid} assessment_id={aid}")
        self.subject = db.get_subject(sid)
        self._show(task, res)
        n = db.assessment_count(sid)
        self.banner.setText(f"บันทึกแล้ว: {self.subject['first_name']} {self.subject['last_name']} · ครั้งที่ {n}")
        self.banner.show()

    def _show(self, task, res):
        key = res["predicted"]
        self.badge.set(C.CLASS_TH[key], C.CLASS_TONE[key])
        self.pct.setText(f"{res['probs'][key]:.0%}")
        self.bars.set(task, res["probs"])
        if res["factors"]:
            parts = [f"{name} {'↑' if s > 0 else '↓'}" for name, s in res["factors"]]
            self.factors.setText("ปัจจัยหลักต่อความเสี่ยง Sarcopenia: " + " · ".join(parts)
                                 + "   (↑ เพิ่มความเสี่ยง, ↓ ลดความเสี่ยง)")
        else:
            self.factors.setText("")
        self.result.show()
