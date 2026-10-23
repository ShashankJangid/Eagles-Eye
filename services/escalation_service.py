from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from config import (
    WEEKLY_INDISCIPLINE_ESCALATION_THRESHOLD,
    WEEKLY_AVERAGE_FOCUS_CRITICAL
)
from database.db_manager import DBManager
from services.pdf_generator import PDFReportGenerator

class EscalationService:
    def __init__(self, db: Optional[DBManager] = None):
        self.db = db or DBManager()
        self.pdf_generator = PDFReportGenerator()

    def evaluate_weekly_reports(self, start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        today = date.today()
        if not end_date:
            end_date = today.isoformat()
        if not start_date:
            start_date = (today - timedelta(days=7)).isoformat()

        summaries = self.db.get_weekly_summary_for_all_students(start_date, end_date)
        evaluated_results = []

        for item in summaries:
            sid = item["student_id"]
            avg_focus = float(item["avg_focus_pct"] or 0.0)
            indisc_count = int(item["total_indiscipline_count"] or 0)

            is_escalated = False
            status = "NORMAL"

            if (indisc_count >= WEEKLY_INDISCIPLINE_ESCALATION_THRESHOLD) or (avg_focus < WEEKLY_AVERAGE_FOCUS_CRITICAL and indisc_count >= 3):
                is_escalated = True
                status = "PARENT_ESCALATED"
            elif indisc_count >= 3 or avg_focus < 65.0:
                status = "REVIEW_NEEDED"

            incidents = self.db.get_indiscipline_events(student_id=sid, days=7)

            pdf_path = None
            parent_notice = None

            if is_escalated:
                student_info = self.db.get_student_by_id(sid) or item
                pdf_path = self.pdf_generator.generate_weekly_parent_report_pdf(
                    student_info=student_info,
                    week_start=start_date,
                    week_end=end_date,
                    avg_focus=avg_focus,
                    total_indiscipline=indisc_count,
                    incidents=incidents
                )
                parent_notice = self.compose_parent_notification_email(
                    student_info=student_info,
                    week_start=start_date,
                    week_end=end_date,
                    avg_focus=avg_focus,
                    total_indiscipline=indisc_count,
                    pdf_path=pdf_path
                )

            self.db.record_weekly_escalation(
                student_id=sid,
                week_start=start_date,
                week_end=end_date,
                avg_focus=avg_focus,
                indiscipline_count=indisc_count,
                escalation_status=status,
                parent_notified_at=datetime.now().isoformat() if is_escalated else None,
                pdf_path=pdf_path
            )

            evaluated_results.append({
                **item,
                "status": status,
                "is_escalated": is_escalated,
                "pdf_path": pdf_path,
                "parent_notice": parent_notice,
                "incidents_count": len(incidents)
            })

        return evaluated_results

    def compose_parent_notification_email(self, student_info: Dict[str, Any], week_start: str,
                                         week_end: str, avg_focus: float,
                                         total_indiscipline: int, pdf_path: str) -> Dict[str, str]:
        student_name = student_info.get("name", "Student")
        parent_name = student_info.get("parent_name", "Parent/Guardian")
        parent_email = student_info.get("parent_email", "parent@example.com")
        grade = student_info.get("grade", "Class")

        subject = f"[IMPORTANT] Weekly Academic Engagement & Behavior Report: {student_name} ({grade})"
        body = f"""Dear {parent_name},

We are writing from the Academic Guidance & Monitoring Office regarding {student_name}'s classroom study performance for the week of {week_start} to {week_end}.

Our classroom learning analytics system ('Eagle's Eye' AI proctoring) recorded behavioral patterns that require mutual home-school intervention:
- Weekly Average Study Focus: {avg_focus:.1f}% (Class benchmark is >= 75%)
- Recorded Indiscipline & Distraction Events: {total_indiscipline} incidents (Talking with peers, phone distraction, and inattention)

Because this exceeded our weekly threshold for proactive parent engagement, an official behavioral dossier has been compiled.

Attached to this notification is the comprehensive PDF report detailing specific incident timestamps and teacher observations.

Please review the attached report and contact our academic counselor to schedule a brief follow-up discussion.

Sincerely,
Eagle's Eye Academic Coordination Team
Learning Management System (LMS) Notification Service
"""
        return {
            "to": parent_email,
            "subject": subject,
            "body": body,
            "attachment": pdf_path
        }
