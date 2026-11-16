"""
models.py — โหลดโมเดลของแอป (app/models/<task>.joblib) และทำนาย

ไฟล์โมเดลของแอปสร้างโดย app/build_models.py จาก results/final/<task>_final_bundle.joblib
มีเฉพาะสิ่งที่ต้องใช้: โมเดล, feature ที่เลือก, ค่า median/mean/scale ของ preprocessing เฉพาะ feature เหล่านั้น
(แอปจึงไม่ต้อง import โค้ดวิจัยใน src/)

การแปลงข้อมูลเหมือน pipeline วิจัยทุกประการสำหรับ feature ตัวเลข:
    ค่าว่าง -> median ของ train, แล้ว (x - mean) / scale   (SimpleImputer + StandardScaler)
"""
import hashlib
from dataclasses import dataclass, field

import joblib
import numpy as np

from . import config as C


def transform(raw: np.ndarray, num: dict) -> np.ndarray:
    """raw: (n, k) ตามลำดับ num['columns'] -> ค่าหลัง impute + scale"""
    x = np.array(raw, dtype=float, copy=True)
    med = np.asarray(num["median"], float)
    nan = np.isnan(x)
    x[nan] = np.broadcast_to(med, x.shape)[nan]
    return (x - np.asarray(num["mean"], float)) / np.asarray(num["scale"], float)


@dataclass
class AppModel:
    task: str
    fs: str
    model_name: str
    model: object
    selected: list
    num: dict
    classes: list
    threshold: float | None
    sha256: str
    class_keys: list = field(default_factory=list)

    @classmethod
    def load(cls, path):
        blob = path.read_bytes()
        d = joblib.load(path)
        unknown = [f for f in d["selected"] if f not in C.FEATURE_TO_INPUT]
        if unknown:
            raise ValueError(f"โมเดล {d['task']} ใช้ feature ที่แอปไม่มีช่องกรอก: {unknown}")
        m = cls(task=d["task"], fs=d["fs"], model_name=d["model_name"], model=d["model"], selected=d["selected"],
                num=d["num"], classes=list(d["classes"]), threshold=d.get("threshold"),
                sha256=hashlib.sha256(blob).hexdigest())
        m.class_keys = [C.CLASS_KEYS[m.task][int(k)] for k in m.classes]
        return m

    # ------------------------------------------------------------------ predict
    def _matrix(self, rows: list[dict]) -> np.ndarray:
        raw = np.array([[r.get(C.FEATURE_TO_INPUT[f], np.nan) for f in self.selected] for r in rows], dtype=float)
        return transform(raw, self.num)

    def predict(self, rows: list[dict]) -> list[dict]:
        """rows: dict ที่มี sex, age_years, bmi, grip_kg, calf_cm -> ผลทำนายต่อคน"""
        X = self._matrix(rows)
        proba = self.model.predict_proba(X)
        contrib = self._contributions(X)
        i_sar = self.class_keys.index("sarcopenia")
        out = []
        for p, c in zip(proba, contrib):
            probs = {k: float(v) for k, v in zip(self.class_keys, p)}
            if self.task == "y2" and self.threshold is not None:
                predicted = "sarcopenia" if p[i_sar] >= self.threshold else "other"
            else:
                predicted = self.class_keys[int(np.argmax(p))]
            out.append({"probs": probs, "predicted": predicted, "factors": self._factors(c)})
        return out

    # ------------------------------------------------------------------ explanation
    def _contributions(self, X: np.ndarray) -> np.ndarray:
        """ผลของแต่ละ feature ต่อ log-odds ของคลาส sarcopenia (n, k); คำนวณไม่ได้คืน NaN"""
        k = X.shape[1]
        i_sar = self.class_keys.index("sarcopenia")
        try:
            if self.model_name == "xgb":
                import xgboost as xgb
                c = self.model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
                c = np.asarray(c)
                if c.ndim == 3:                                  # หลายคลาส: (n, คลาส, feature + bias)
                    return c[:, i_sar, :k]
                return c[:, :k] if i_sar == 1 else -c[:, :k]     # 2 คลาส: ผลต่อ log-odds ของคลาส 1
            if self.model_name == "ebm":
                t = np.asarray(self.model.eval_terms(X))
                if t.ndim == 3:
                    t = t[:, :, i_sar]
                elif i_sar == 0:
                    t = -t
                out = np.zeros((X.shape[0], k))
                for j, feats in enumerate(self.model.term_features_):      # แบ่งผลของ interaction เท่า ๆ กัน
                    for f in feats:
                        out[:, f] += t[:, j] / len(feats)
                return out
        except Exception:
            pass
        return np.full((X.shape[0], k), np.nan)

    def _factors(self, c: np.ndarray, top: int = 3) -> list[tuple[str, int]]:
        """[(ชื่อ feature ภาษาไทย, +1 เพิ่มความเสี่ยง / -1 ลดความเสี่ยง)] เรียงตามขนาดผล"""
        if np.isnan(c).all():
            return []
        order = np.argsort(-np.abs(c))[:top]
        return [(C.FEATURE_TH[self.selected[i]], 1 if c[i] > 0 else -1) for i in order if abs(c[i]) > 1e-9]


class ModelService:
    def __init__(self, models_dir=None):
        d = models_dir or C.MODELS_DIR
        self.models, self.errors = {}, []
        for task in C.TASKS:
            p = d / f"{task}.joblib"
            if not p.exists():
                self.errors.append(f"ไม่พบไฟล์โมเดล {p.name}")
                continue
            try:
                self.models[task] = AppModel.load(p)
            except Exception as e:                                   # noqa: BLE001
                self.errors.append(f"โหลด {p.name} ไม่ได้: {e}")

    def get(self, task) -> AppModel:
        return self.models[task]

    @property
    def tasks(self):
        return [t for t in C.TASKS if t in self.models]
