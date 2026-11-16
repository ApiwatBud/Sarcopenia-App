"""page_history.py — ประวัติผู้รับการประเมิน: ค้นหา, กราฟ % Sarcopenia, ตารางเทียบกับครั้งก่อน"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QLineEdit, QSizePolicy, QSplitter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ..core import config as C
from .theme import BAD, GOOD, TONES
from .widgets import Badge, TrendChart, button, card, confirm, label, thai_date

# ทิศทางที่ "ดีขึ้น" ในมุมความเสี่ยง Sarcopenia: +1 ค่าเพิ่ม = ดี, -1 ค่าเพิ่ม = แย่
DIRECTION = {"bmi": +1, "grip_kg": +1, "calf_cm": +1, "sarcopenia": -1}


class HistoryPage(QWidget):
    new_assessment = Signal(str)                                # ID

    def __init__(self, session):
        super().__init__()
        self.s = session
        self.subject = None
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        row = QHBoxLayout()
        self.back = button("← รายชื่อทั้งหมด")
        self.back.clicked.connect(self.show_all)
        self.back.hide()
        self.q = QLineEdit()
        self.q.setPlaceholderText("ค้นหา ID หรือ ชื่อ-สกุล")
        self.q.returnPressed.connect(self.search)
        b = button("ค้นหา")
        b.clicked.connect(self.search)
        allb = button("แสดงทั้งหมด")
        allb.clicked.connect(self.show_all)
        row.addWidget(self.back)
        row.addWidget(self.q, 1)
        row.addWidget(b)
        row.addWidget(allb)
        root.addLayout(row)
        self.msg = label("", "muted")
        root.addWidget(self.msg)

        # รายชื่อทั้งหมด (หน้าแรกของประวัติ) — ดับเบิลคลิก/คลิกแถว เพื่อดูรายละเอียด
        self.list = QTableWidget(0, 7)
        self.list.setHorizontalHeaderLabels(["ID", "ชื่อ-สกุล", "เพศ", "ประเมิน (ครั้ง)", "ผลล่าสุด",
                                             "% Sarcopenia ล่าสุด", "วันที่ล่าสุด"])
        self.list.verticalHeader().setVisible(False)
        self.list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list.setSelectionBehavior(QTableWidget.SelectRows)
        self.list.setSelectionMode(QTableWidget.SingleSelection)
        lh = self.list.horizontalHeader()
        lh.setSectionResizeMode(QHeaderView.ResizeToContents)
        lh.setSectionResizeMode(1, QHeaderView.Stretch)
        self.list.cellClicked.connect(lambda r, _c: self.show_subject(self.list.item(r, 0).data(Qt.UserRole)))
        root.addWidget(self.list, 1)

        self.body = QWidget()
        bl = QVBoxLayout(self.body)
        bl.setContentsMargins(0, 0, 0, 0)
        topw = QWidget()
        top = QHBoxLayout(topw)
        top.setContentsMargins(0, 0, 0, 0)
        # การ์ดข้อมูลคน
        pc = card()
        pl = QVBoxLayout(pc)
        pl.setContentsMargins(14, 12, 14, 12)
        self.name = QLabel()
        self.name.setStyleSheet("font-size:12pt;font-weight:600;")
        self.sub = label("")
        self.count = label("")
        trend = QHBoxLayout()
        trend.setSpacing(6)
        trend.addWidget(QLabel("แนวโน้ม:"))
        self.first_badge, self.arrow, self.last_badge = Badge(), QLabel("→"), Badge()
        self.arrow.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        for w in (self.first_badge, self.arrow, self.last_badge):
            trend.addWidget(w)
        trend.addStretch(1)
        acts = QHBoxLayout()
        again = button("+ ประเมินใหม่")
        again.clicked.connect(lambda: self.subject and self.new_assessment.emit(self.subject["code"]))
        self.delete_btn = button("ลบ", "danger")
        self.delete_btn.clicked.connect(self.delete)
        self.delete_btn.setVisible(self.s.is_admin)
        acts.addWidget(again)
        acts.addWidget(self.delete_btn)
        acts.addStretch(1)
        for w in (self.name, self.sub, self.count):
            pl.addWidget(w)
        pl.addLayout(trend)
        pl.addStretch(1)
        pl.addLayout(acts)
        # กราฟ
        gc = card()
        gl = QVBoxLayout(gc)
        gl.setContentsMargins(14, 10, 14, 8)
        gl.addWidget(label("ความน่าจะเป็น Sarcopenia (%)"))
        self.chart = TrendChart()
        gl.addWidget(self.chart)
        pc.setFixedWidth(340)                                   # การ์ดข้อมูลคนกว้างคงที่ กราฟใช้พื้นที่ที่เหลือ
        top.addWidget(pc)
        top.addWidget(gc, 1)
        topw.setMinimumHeight(200)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["วันที่", "อายุ", "BMI", "grip", "น่อง", "% Sarcopenia", "ผล", "โมเดล",
                                              "ผู้ประเมิน"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(220)
        # ลากเส้นแบ่งระหว่างกราฟกับตารางเพื่อปรับความสูงได้; เริ่มต้นให้ตารางได้พื้นที่มากกว่า
        self.split = QSplitter(Qt.Vertical)
        self.split.addWidget(topw)
        self.split.addWidget(self.table)
        self.split.setChildrenCollapsible(False)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([230, 600])
        self.split.setHandleWidth(8)
        bl.addWidget(self.split, 1)
        bl.addWidget(label("เทียบกับครั้งก่อนหน้า: ▲▼ สีเขียว = ดีขึ้น · สีแดง = แย่ลง (ในมุมความเสี่ยง Sarcopenia "
                           "เท่านั้น) · ครั้งแรกไม่มีสี", "muted"))
        self.body.hide()
        root.addWidget(self.body, 1)

    def refresh(self):
        """เรียกทุกครั้งที่เปิดหน้านี้: ถ้าไม่ได้ดูรายละเอียดใครอยู่ ให้แสดงรายชื่อล่าสุด"""
        if self.subject is None:
            self.search()
        else:
            self.show_subject(self.subject["subject_id"])

    def show_all(self):
        self.q.clear()
        self.search()

    def search(self):
        text = self.q.text().strip()
        found = self.s.db.list_subjects(text)
        self.body.hide()
        self.back.hide()
        self.subject = None
        if text and len(found) == 1:
            self.show_subject(found[0]["subject_id"])
            return
        if not found:
            self.msg.setText("ไม่พบ (ค้นด้วย ID ต้องพิมพ์ครบ เช่น SC0020)" if text else "ยังไม่มีผู้รับการประเมินในระบบ")
        else:
            self.msg.setText(f"{len(found)} คน" + (f" ที่ตรงกับ “{text}”" if text else " (ใหม่สุดอยู่บน) · คลิกที่แถวเพื่อดูประวัติ"))
        self._fill_list(found)
        self.msg.show()
        self.list.show()

    def _fill_list(self, rows):
        self.list.setRowCount(len(rows))
        for i, d in enumerate(rows):
            code = QTableWidgetItem(d["code"])
            code.setData(Qt.UserRole, d["subject_id"])              # คอลัมน์แรกเก็บ subject_id ไว้เปิดประวัติ
            cls = d["last_class"]
            res = QTableWidgetItem(C.CLASS_TH[cls] if cls else "—")
            if cls:
                bg, fg, _ = TONES[C.CLASS_TONE[cls]]
                res.setBackground(QColor(bg))
                res.setForeground(QColor(fg))
            cells = [code, QTableWidgetItem(f"{d['first_name']} {d['last_name']}"), QTableWidgetItem(C.SEX_TH.get(d["sex"], "")),
                     QTableWidgetItem(str(d["n"])), res,
                     QTableWidgetItem(f"{d['last_sar']:.0%}" if d["last_sar"] is not None else "—"),
                     QTableWidgetItem(thai_date(d["last_at"]) if d["last_at"] else "—")]
            for j in (3, 5):
                cells[j].setTextAlignment(Qt.AlignCenter)
            for j, it in enumerate(cells):
                self.list.setItem(i, j, it)

    def show_subject(self, subject_id):
        s = self.s.db.get_subject(subject_id)
        if s is None:
            return
        self.subject = s
        self.list.hide()
        self.back.show()
        self.msg.setText("")
        self.msg.hide()
        self.s.db.log(self.s.user_id, "view_subject", f"subject_id={subject_id}")
        hist = self.s.db.assessments_for(subject_id)
        self.name.setText(f"{s['first_name']} {s['last_name']}")
        self.sub.setText(f"ID {s['code']} · {C.SEX_TH.get(s['sex'], '')}")
        self.count.setText(f"ประเมิน {len(hist)} ครั้ง" + (f" · ครั้งแรก {thai_date(hist[0]['assessed_at'])}" if hist else ""))
        if hist:
            a, b = hist[0]["predicted_class"], hist[-1]["predicted_class"]
            self.first_badge.set(C.CLASS_TH[a], C.CLASS_TONE[a])
            self.last_badge.set(C.CLASS_TH[b], C.CLASS_TONE[b])
        for w in (self.first_badge, self.arrow, self.last_badge):
            w.setVisible(len(hist) > 1)
        if len(hist) == 1:
            self.first_badge.setVisible(True)
        self.chart.set([(thai_date(h["assessed_at"]), h["probs"].get("sarcopenia", 0.0)) for h in hist])
        self._table(hist)
        self.body.show()

    def _table(self, hist):
        rows = list(reversed(hist))                                     # ใหม่สุดอยู่บน
        self.table.setRowCount(len(rows))
        for i, h in enumerate(rows):
            prev = rows[i + 1] if i + 1 < len(rows) else None
            pred = h["predicted_class"]
            sar = h["probs"].get("sarcopenia", 0.0)
            vals = [thai_date(h["assessed_at"]), f"{h['age_years']:.0f}"]
            items = [QTableWidgetItem(v) for v in vals]
            for key in ("bmi", "grip_kg", "calf_cm"):
                items.append(self._delta_item(f"{h[key]:.1f}", h[key], prev[key] if prev else None, DIRECTION[key]))
            items.append(self._delta_item(f"{sar:.0%}", sar, prev["probs"].get("sarcopenia") if prev else None,
                                          DIRECTION["sarcopenia"]))
            res = QTableWidgetItem(C.CLASS_TH[pred])
            bg, fg, _ = TONES[C.CLASS_TONE[pred]]
            res.setBackground(QColor(bg))
            res.setForeground(QColor(fg))
            items.append(res)
            items.append(QTableWidgetItem(C.TASK_LABELS.get(h["task"], h["task"])))
            items.append(QTableWidgetItem(h["username"]))
            for j, it in enumerate(items):
                self.table.setItem(i, j, it)

    @staticmethod
    def _delta_item(text, value, prev, direction):
        it = QTableWidgetItem(text)
        if prev is None or value is None or abs(value - prev) < 1e-9:
            return it
        up = value > prev
        it.setText(f"{text} {'▲' if up else '▼'}")
        good = up if direction > 0 else not up
        it.setForeground(QColor(GOOD if good else BAD))
        return it

    def delete(self):
        if not (self.subject and self.s.is_admin):
            return
        s = self.subject
        n = self.s.db.assessment_count(s["subject_id"])
        if not confirm(self, "ลบผู้รับการประเมิน",
                       f"ลบ {s['first_name']} {s['last_name']} และประวัติการประเมิน {n} ครั้ง\n"
                       "การลบนี้ย้อนกลับไม่ได้ ยืนยันหรือไม่?"):
            return
        self.s.db.delete_subject(s["subject_id"])
        self.s.db.log(self.s.user_id, "delete_subject", f"subject_id={s['subject_id']} assessments={n}")
        self.show_all()
        self.msg.setText("ลบแล้ว · " + self.msg.text())
