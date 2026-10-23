import sqlite3
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import DB_PATH
from database.models import SCHEMA_SQL

class DBManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        self.seed_sample_students_if_empty()

    def seed_sample_students_if_empty(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM students")
            row = cursor.fetchone()
            if row and row["count"] > 0:
                return

            sample_students = [
                ("STU-101", "Aarav Sharma", "Grade 10-A", "aarav.s@school.edu", "Rajesh Sharma", "rajesh.sharma@example.com", "+1-555-0101"),
                ("STU-102", "Priya Patel", "Grade 10-A", "priya.p@school.edu", "Sunita Patel", "sunita.patel@example.com", "+1-555-0102"),
                ("STU-103", "Rohan Mehta", "Grade 10-A", "rohan.m@school.edu", "Vikram Mehta", "vikram.mehta@example.com", "+1-555-0103"),
                ("STU-104", "Ananya Verma", "Grade 10-A", "ananya.v@school.edu", "Deepak Verma", "deepak.verma@example.com", "+1-555-0104"),
                ("STU-105", "Kabir Singh", "Grade 10-A", "kabir.s@school.edu", "Manjit Singh", "manjit.singh@example.com", "+1-555-0105"),
                ("STU-106", "Diya Iyer", "Grade 10-A", "diya.i@school.edu", "Ramesh Iyer", "ramesh.iyer@example.com", "+1-555-0106"),
            ]

            cursor.executemany(
                """
                INSERT INTO students (student_id, name, grade, email, parent_name, parent_email, parent_phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                sample_students
            )

            now = datetime.now()
            cursor.execute(
                """
                INSERT INTO sessions (session_code, class_name, subject, teacher_name, start_time, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("SES-2026-MATH10", "Grade 10-A", "Advanced Mathematics", "Dr. Shalini Rao", now.isoformat(), "IN_PROGRESS")
            )
            session_id = cursor.lastrowid

            today = date.today()
            for day_offset in range(5, 0, -1):
                day = today - timedelta(days=day_offset)
                day_str = day.isoformat()

                cursor.execute(
                    """
                    INSERT INTO daily_reports (student_id, report_date, total_monitored_minutes, study_minutes, distracted_minutes, focus_percentage, indiscipline_count, lms_sync_status, lms_synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("STU-101", day_str, 60.0, 54.0, 6.0, 90.0, 0, "SYNCED", f"{day_str}T16:00:00")
                )

                cursor.execute(
                    """
                    INSERT INTO daily_reports (student_id, report_date, total_monitored_minutes, study_minutes, distracted_minutes, focus_percentage, indiscipline_count, lms_sync_status, lms_synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("STU-102", day_str, 60.0, 48.0, 12.0, 80.0, 1, "SYNCED", f"{day_str}T16:00:00")
                )

                indiscipline_cnt = 2 if day_offset % 2 == 0 else 3
                focus_pct = 42.0 if day_offset % 2 == 0 else 38.0
                cursor.execute(
                    """
                    INSERT INTO daily_reports (student_id, report_date, total_monitored_minutes, study_minutes, distracted_minutes, focus_percentage, indiscipline_count, lms_sync_status, lms_synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("STU-103", day_str, 60.0, 24.0, 36.0, focus_pct, indiscipline_cnt, "SYNCED", f"{day_str}T16:00:00")
                )

                cursor.execute(
                    """
                    INSERT INTO indiscipline_events (session_id, student_id, timestamp, event_type, duration_seconds, severity, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, "STU-103", f"{day_str} 10:15:00", "TALKING_DISRUPTION", 145.0, "HIGH", "Talking with neighbor during study hours")
                )
                cursor.execute(
                    """
                    INSERT INTO indiscipline_events (session_id, student_id, timestamp, event_type, duration_seconds, severity, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, "STU-103", f"{day_str} 10:35:00", "PHONE_USAGE", 210.0, "HIGH", "Looking down at mobile phone")
                )

                cursor.execute(
                    """
                    INSERT INTO daily_reports (student_id, report_date, total_monitored_minutes, study_minutes, distracted_minutes, focus_percentage, indiscipline_count, lms_sync_status, lms_synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("STU-104", day_str, 60.0, 51.0, 9.0, 85.0, 0, "SYNCED", f"{day_str}T16:00:00")
                )

                cursor.execute(
                    """
                    INSERT INTO daily_reports (student_id, report_date, total_monitored_minutes, study_minutes, distracted_minutes, focus_percentage, indiscipline_count, lms_sync_status, lms_synced_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("STU-105", day_str, 60.0, 35.0, 25.0, 58.0, 1, "SYNCED", f"{day_str}T16:00:00")
                )

            conn.commit()

    def get_all_students(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students ORDER BY student_id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_student_by_id(self, student_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def log_frame(self, session_id: int, student_id: str, focus_score: float, study_state: str,
                  ear: float, mar: float, yaw: float, pitch: float, dg_gaze_score: float, emotion: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO frame_logs (session_id, student_id, focus_score, study_state, ear, mar, yaw, pitch, dg_gaze_score, emotion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, student_id, focus_score, study_state, ear, mar, yaw, pitch, dg_gaze_score, emotion)
            )
            conn.commit()

    def log_indiscipline_event(self, session_id: int, student_id: str, event_type: str,
                               duration_seconds: float, severity: str, notes: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO indiscipline_events (session_id, student_id, event_type, duration_seconds, severity, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, student_id, event_type, duration_seconds, severity, notes)
            )
            conn.commit()

    def get_indiscipline_events(self, student_id: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            if student_id:
                cursor.execute(
                    """
                    SELECT e.*, s.name as student_name, s.grade, s.parent_name, s.parent_email
                    FROM indiscipline_events e
                    JOIN students s ON e.student_id = s.student_id
                    WHERE e.student_id = ? AND e.timestamp >= ?
                    ORDER BY e.timestamp DESC
                    """,
                    (student_id, since_date)
                )
            else:
                cursor.execute(
                    """
                    SELECT e.*, s.name as student_name, s.grade, s.parent_name, s.parent_email
                    FROM indiscipline_events e
                    JOIN students s ON e.student_id = s.student_id
                    WHERE e.timestamp >= ?
                    ORDER BY e.timestamp DESC
                    """,
                    (since_date,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def upsert_daily_report(self, student_id: str, report_date: str, total_monitored_minutes: float,
                            study_minutes: float, distracted_minutes: float, focus_percentage: float,
                            indiscipline_count: int, lms_sync_status: str = "PENDING",
                            lms_payload: Optional[Dict] = None):
        payload_str = json.dumps(lms_payload) if lms_payload else None
        synced_at = datetime.now().isoformat() if lms_sync_status == "SYNCED" else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO daily_reports (student_id, report_date, total_monitored_minutes, study_minutes,
                                          distracted_minutes, focus_percentage, indiscipline_count,
                                          lms_sync_status, lms_synced_at, lms_payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, report_date) DO UPDATE SET
                    total_monitored_minutes = excluded.total_monitored_minutes,
                    study_minutes = excluded.study_minutes,
                    distracted_minutes = excluded.distracted_minutes,
                    focus_percentage = excluded.focus_percentage,
                    indiscipline_count = excluded.indiscipline_count,
                    lms_sync_status = excluded.lms_sync_status,
                    lms_synced_at = excluded.lms_synced_at,
                    lms_payload_json = excluded.lms_payload_json
                """,
                (student_id, report_date, total_monitored_minutes, study_minutes, distracted_minutes,
                 focus_percentage, indiscipline_count, lms_sync_status, synced_at, payload_str)
            )
            conn.commit()

    def get_daily_reports_for_date(self, report_date: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.*, s.name, s.grade, s.email, s.parent_name
                FROM daily_reports r
                JOIN students s ON r.student_id = s.student_id
                WHERE r.report_date = ?
                ORDER BY r.student_id ASC
                """,
                (report_date,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_weekly_summary_for_all_students(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    s.student_id,
                    s.name,
                    s.grade,
                    s.parent_name,
                    s.parent_email,
                    s.parent_phone,
                    COUNT(r.id) as days_recorded,
                    AVG(r.focus_percentage) as avg_focus_pct,
                    SUM(r.indiscipline_count) as total_indiscipline_count,
                    SUM(r.study_minutes) as total_study_minutes,
                    SUM(r.distracted_minutes) as total_distracted_minutes
                FROM students s
                LEFT JOIN daily_reports r ON s.student_id = r.student_id 
                    AND r.report_date BETWEEN ? AND ?
                GROUP BY s.student_id
                ORDER BY total_indiscipline_count DESC, avg_focus_pct ASC
                """,
                (start_date, end_date)
            )
            return [dict(row) for row in cursor.fetchall()]

    def record_weekly_escalation(self, student_id: str, week_start: str, week_end: str,
                                avg_focus: float, indiscipline_count: int, escalation_status: str,
                                parent_notified_at: Optional[str] = None, pdf_path: Optional[str] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO weekly_reports (student_id, week_start_date, week_end_date, avg_focus_percentage,
                                            total_indiscipline_count, escalation_status, parent_notified_at,
                                            pdf_report_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, week_start_date) DO UPDATE SET
                    avg_focus_percentage = excluded.avg_focus_percentage,
                    total_indiscipline_count = excluded.total_indiscipline_count,
                    escalation_status = excluded.escalation_status,
                    parent_notified_at = excluded.parent_notified_at,
                    pdf_report_path = excluded.pdf_report_path
                """,
                (student_id, week_start, week_end, avg_focus, indiscipline_count, escalation_status,
                 parent_notified_at, pdf_path)
            )
            conn.commit()

    def get_weekly_reports(self, week_start: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.*, s.name, s.grade, s.parent_name, s.parent_email, s.parent_phone
                FROM weekly_reports w
                JOIN students s ON w.student_id = s.student_id
                WHERE w.week_start_date = ?
                ORDER BY w.total_indiscipline_count DESC
                """,
                (week_start,)
            )
            return [dict(row) for row in cursor.fetchall()]
