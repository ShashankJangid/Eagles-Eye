SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    grade TEXT NOT NULL,
    email TEXT,
    parent_name TEXT NOT NULL,
    parent_email TEXT NOT NULL,
    parent_phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_code TEXT UNIQUE NOT NULL,
    class_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    teacher_name TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'IN_PROGRESS'
);

CREATE TABLE IF NOT EXISTS frame_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    student_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    focus_score REAL NOT NULL,
    study_state TEXT NOT NULL,
    ear REAL,
    mar REAL,
    yaw REAL,
    pitch REAL,
    dg_gaze_score REAL,
    emotion TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id),
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS indiscipline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    student_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    duration_seconds REAL DEFAULT 0,
    severity TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id),
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    report_date DATE NOT NULL,
    total_monitored_minutes REAL NOT NULL,
    study_minutes REAL NOT NULL,
    distracted_minutes REAL NOT NULL,
    focus_percentage REAL NOT NULL,
    indiscipline_count INTEGER DEFAULT 0,
    lms_sync_status TEXT DEFAULT 'PENDING',
    lms_synced_at TIMESTAMP,
    lms_payload_json TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    UNIQUE(student_id, report_date)
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    avg_focus_percentage REAL NOT NULL,
    total_indiscipline_count INTEGER DEFAULT 0,
    escalation_status TEXT DEFAULT 'NORMAL',
    parent_notified_at TIMESTAMP,
    parent_notification_method TEXT,
    pdf_report_path TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    UNIQUE(student_id, week_start_date)
);
"""
