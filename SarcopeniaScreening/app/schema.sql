-- FF69 Sarcopenia Screening (Windows app) — SQLite schema v1
-- เก็บที่ %LOCALAPPDATA%\FF69Sarcopenia\screening.db (ไม่ใช่ Documents/OneDrive)
-- ฟิลด์ที่ลงท้าย _enc เข้ารหัสด้วย AES (Fernet) ก่อนบันทึก; กุญแจเก็บใน Windows Credential Manager
PRAGMA foreign_keys = ON;

-- ผู้ใช้งานระบบ (เจ้าหน้าที่)
CREATE TABLE users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT    NOT NULL UNIQUE,
    password_hash  TEXT    NOT NULL,                 -- bcrypt
    full_name      TEXT    NOT NULL,
    role           TEXT    NOT NULL DEFAULT 'staff' CHECK (role IN ('admin', 'staff')),
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    last_login_at  TEXT
);

-- ผู้รับการประเมิน (เก็บเท่าที่จำเป็น: ไม่เก็บวันเกิด/เบอร์โทร; ติดตามผลโดย map ID กับไฟล์ข้อมูลโครงการ)
-- ID รูปแบบเดียวกับ "ID Number" ในไฟล์ข้อมูลที่ใช้ train เช่น SC0020, MS101 (ดู app/core/idcode.py)
CREATE TABLE subjects (
    subject_id       INTEGER PRIMARY KEY,
    code_hash        TEXT    NOT NULL UNIQUE,        -- HMAC-SHA256(ID, กุญแจในเครื่อง) ใช้ค้นหา/กันซ้ำ
    code_enc         BLOB    NOT NULL,
    first_name_enc   BLOB    NOT NULL,
    last_name_enc    BLOB    NOT NULL,
    sex              INTEGER NOT NULL CHECK (sex IN (1, 2)),   -- 1 = หญิง, 2 = ชาย (ตรงกับข้อมูลวิจัย)
    created_by       INTEGER NOT NULL REFERENCES users(user_id),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at       TEXT
);

-- เวอร์ชันโมเดลที่ใช้ (เพื่อย้อนตรวจได้ว่าผลแต่ละครั้งมาจากโมเดลไหน)
CREATE TABLE model_versions (
    model_version_id INTEGER PRIMARY KEY,
    task             TEXT    NOT NULL CHECK (task IN ('y2', 'y3')),
    fs_method        TEXT    NOT NULL,               -- shap
    model_name       TEXT    NOT NULL,               -- xgb / ebm
    features_json    TEXT    NOT NULL,               -- ["gender","age","BMI","grip ave","Calf circum"]
    classes_json     TEXT    NOT NULL,               -- ชื่อคลาสตามลำดับ p0, p1, p2
    threshold        REAL,                           -- y2
    bundle_sha256    TEXT    NOT NULL UNIQUE,
    installed_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

-- การนำเข้าไฟล์ (คัดกรองหลายคน)
CREATE TABLE batches (
    batch_id     INTEGER PRIMARY KEY,
    file_name    TEXT    NOT NULL,
    file_sha256  TEXT    NOT NULL,
    n_rows       INTEGER NOT NULL,
    n_success    INTEGER NOT NULL,
    n_error      INTEGER NOT NULL,
    imported_by  INTEGER NOT NULL REFERENCES users(user_id),
    imported_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ประวัติการประเมิน (1 แถว = การคัดกรอง 1 ครั้ง)
CREATE TABLE assessments (
    assessment_id    INTEGER PRIMARY KEY,
    subject_id       INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    model_version_id INTEGER NOT NULL REFERENCES model_versions(model_version_id),
    batch_id         INTEGER REFERENCES batches(batch_id),          -- NULL = กรอกรายคน
    assessed_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    assessed_by      INTEGER NOT NULL REFERENCES users(user_id),
    -- ค่าที่ใช้ทำนาย (ณ วันที่ประเมิน)
    age_years        REAL    NOT NULL CHECK (age_years BETWEEN 40 AND 120),
    weight_kg        REAL    CHECK (weight_kg BETWEEN 20 AND 200),
    height_cm        REAL    CHECK (height_cm BETWEEN 100 AND 220),
    bmi              REAL    NOT NULL CHECK (bmi BETWEEN 10 AND 60),
    grip_kg          REAL    NOT NULL CHECK (grip_kg BETWEEN 0 AND 80),
    calf_cm          REAL    NOT NULL CHECK (calf_cm BETWEEN 15 AND 60),
    -- ผลลัพธ์
    prob_json        TEXT    NOT NULL,               -- {"normal":0.07,"possible":0.12,"sarcopenia":0.81}
    predicted_class  TEXT    NOT NULL,
    note             TEXT
);
CREATE INDEX ix_assess_subject ON assessments(subject_id, assessed_at);
CREATE INDEX ix_assess_date    ON assessments(assessed_at);

-- บันทึกการใช้งาน (accountability ตาม PDPA: ใครดู/แก้/export/ลบ อะไร เมื่อไร)
CREATE TABLE audit_log (
    log_id     INTEGER PRIMARY KEY,
    user_id    INTEGER REFERENCES users(user_id),
    action     TEXT    NOT NULL CHECK (action IN ('login', 'login_failed', 'logout', 'view_subject',
                        'create_subject', 'update_subject', 'delete_subject', 'assess', 'import', 'export',
                        'manage_user')),
    target     TEXT,                                 -- เช่น subject_id=12, file=xxx.xlsx (ห้ามใส่ชื่อ/ID)
    at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX ix_audit_at ON audit_log(at);

-- ค่าระบบ (เช่น key_check ใช้ตรวจว่ากุญแจใน Credential Manager ตรงกับฐานข้อมูลนี้)
CREATE TABLE app_meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
