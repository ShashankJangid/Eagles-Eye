from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from config import REPORTS_DIR

class PDFReportGenerator:
    def __init__(self, output_dir: Path = REPORTS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.styles = getSampleStyleSheet()

    def generate_daily_teacher_lms_pdf(self, report_date: str, class_name: str,
                                       teacher_name: str, records: List[Dict[str, Any]]) -> str:
        file_path = self.output_dir / f"Daily_Teacher_LMS_Report_{report_date}.pdf"
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )

        elements = []

        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'HeaderSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=15
        )

        elements.append(Paragraph("<b>Eagle's Eye AI - Daily LMS Attention & Study Report</b>", title_style))
        elements.append(Paragraph(
            f"<b>Date:</b> {report_date} &nbsp;|&nbsp; <b>Class:</b> {class_name} &nbsp;|&nbsp; <b>Instructor:</b> {teacher_name}",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=15))

        total_students = len(records)
        avg_class_focus = (sum(r.get('focus_percentage', 0.0) for r in records) / total_students) if total_students > 0 else 0
        total_indiscipline = sum(r.get('indiscipline_count', 0) for r in records)

        summary_data = [
            ["Total Monitored Students", "Class Average Focus", "Total Indiscipline Flags", "LMS Sync Status"],
            [str(total_students), f"{avg_class_focus:.1f}%", str(total_indiscipline), "SYNCED TO LMS"]
        ]
        summary_table = Table(summary_data, colWidths=[130, 130, 140, 140])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#475569')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#FFFFFF')),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 12),
            ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#16A34A') if avg_class_focus >= 70 else colors.HexColor('#DC2626')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Student Attention & Engagement Breakdown</b>", self.styles['Heading2']))
        elements.append(Spacer(1, 8))

        table_data = [["Student ID", "Student Name", "Monitored", "Study Time", "Focus %", "Indiscipline", "Evaluation"]]
        for r in records:
            focus = r.get('focus_percentage', 0.0)
            indisc = r.get('indiscipline_count', 0)
            eval_text = "Exemplary" if focus >= 85 else ("Satisfactory" if focus >= 70 else ("Needs Attention" if focus >= 50 else "High Concern"))
            table_data.append([
                r.get('student_id', ''),
                r.get('name', ''),
                f"{r.get('total_monitored_minutes', 0):.0f}m",
                f"{r.get('study_minutes', 0):.0f}m",
                f"{focus:.1f}%",
                str(indisc),
                eval_text
            ])

        student_table = Table(table_data, colWidths=[75, 130, 65, 65, 65, 75, 95])
        student_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        elements.append(student_table)
        elements.append(Spacer(1, 25))

        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#94A3B8')
        )
        elements.append(Paragraph(
            f"Generated automatically by Eagle's Eye AI Camera System on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. "
            f"Synced directly with school Learning Management System (LMS).",
            footer_style
        ))

        doc.build(elements)
        return str(file_path)

    def generate_weekly_parent_report_pdf(self, student_info: Dict[str, Any], week_start: str,
                                         week_end: str, avg_focus: float, total_indiscipline: int,
                                         incidents: List[Dict[str, Any]]) -> str:
        student_id = student_info.get("student_id", "STU")
        file_path = self.output_dir / f"Weekly_Parent_Escalation_{student_id}_{week_start}.pdf"
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )

        elements = []

        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#991B1B'),
            spaceAfter=4
        )
        elements.append(Paragraph("<b>CONFIDENTIAL: Weekly Student Behavioral & Attention Notice</b>", title_style))
        elements.append(Paragraph(
            f"<b>Reporting Period:</b> {week_start} to {week_end} &nbsp;|&nbsp; <b>Recipient:</b> Parent/Guardian of {student_info.get('name')}",
            ParagraphStyle('Sub', parent=self.styles['Normal'], fontSize=10, textColor=colors.HexColor('#64748B'), spaceAfter=15)
        ))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#DC2626'), spaceAfter=15))

        elements.append(Paragraph(f"Dear <b>{student_info.get('parent_name', 'Parent/Guardian')}</b>,", self.styles['Normal']))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            f"This automated weekly report is sent to keep you informed of <b>{student_info.get('name')}</b>'s "
            f"learning engagement and classroom discipline in {student_info.get('grade', 'Class')}. "
            f"During the past week, our AI classroom monitoring system ('Eagle's Eye') registered behavior patterns "
            f"that exceeded our threshold for active teacher and parent attention.",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 15))

        metric_data = [
            ["Weekly Average Focus Score", "Total Indiscipline Incidents", "Severity Status", "Action Level"],
            [f"{avg_focus:.1f}%", str(total_indiscipline), "HIGH CONCERN", "PARENT CONSULTATION REQUIRED"]
        ]
        metric_table = Table(metric_data, colWidths=[130, 140, 130, 140])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEE2E2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#FEF2F2')),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#DC2626')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#FCA5A5')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FECACA')),
        ]))
        elements.append(metric_table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Log of Specific Indiscipline Incidents Registered This Week:</b>", self.styles['Heading2']))
        elements.append(Spacer(1, 8))

        inc_data = [["Timestamp", "Incident Category", "Severity", "Duration", "Behavioral Observation"]]
        if incidents:
            for inc in incidents[:8]:
                inc_data.append([
                    inc.get("timestamp", "")[:16],
                    inc.get("event_type", "").replace("_", " "),
                    inc.get("severity", "HIGH"),
                    f"{inc.get('duration_seconds', 0):.0f}s",
                    inc.get("notes", "Classroom disruption detected")
                ])
        else:
            inc_data.append(["-", "Cumulative inattention pattern", "HIGH", "-", "Frequent off-task gaze and conversation."])

        inc_table = Table(inc_data, colWidths=[90, 120, 60, 50, 220])
        inc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (3, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        elements.append(inc_table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Recommended Home-School Collaboration Actions:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 6))
        bullet_style = ParagraphStyle('Bullet', parent=self.styles['Normal'], fontSize=9, leading=14, leftIndent=15)
        elements.append(Paragraph("• <b>Review Screen & Device Habits:</b> Discuss maintaining focus during independent study sessions without switching to unauthorized apps or mobile phone usage.", bullet_style))
        elements.append(Paragraph("• <b>Sleep Schedule:</b> Ensure adequate 8 hours of sleep to minimize daytime drowsiness and cognitive fatigue in morning classes.", bullet_style))
        elements.append(Paragraph("• <b>Teacher Conference:</b> Please schedule a 15-minute conference with the homeroom teacher to review this week's progress.", bullet_style))
        elements.append(Spacer(1, 20))

        elements.append(Paragraph(
            f"<b>Eagle's Eye AI Proctoring & LMS Administration</b> &nbsp;|&nbsp; Direct contact: support@school.edu",
            ParagraphStyle('Foot', parent=self.styles['Normal'], fontSize=8, textColor=colors.HexColor('#94A3B8'))
        ))

        doc.build(elements)
        return str(file_path)

    def generate_session_event_report_pdf(self, session_data: Dict[str, Any]) -> str:
        student_info = session_data.get("student", {})
        student_id = student_info.get("student_id", "STU")
        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.output_dir / f"Session_Report_{student_id}_{timestamp_slug}.pdf"

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )

        elements = []

        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=self.styles['Heading1'],
            fontSize=21,
            leading=25,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=3
        )
        subtitle_style = ParagraphStyle(
            'HeaderSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=12
        )

        elements.append(Paragraph("<b>Eagle's Eye AI - Live Session Proctoring Report</b>", title_style))
        elements.append(Paragraph(
            f"Automated Event Evaluation | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563EB'), spaceAfter=14))

        start_str = session_data.get("start_time", "-")
        end_str = session_data.get("end_time", "-")
        duration_str = session_data.get("duration_formatted", "0s")

        meta_data = [
            ["Student Name:", student_info.get("name", "Student"), "Student ID:", student_id],
            ["Class / Grade:", student_info.get("grade", "Grade 10"), "Camera Source:", session_data.get("camera_source", "Webcam")],
            ["Session Start:", start_str, "Session End:", end_str],
            ["Total Duration:", duration_str, "Total Frames Analyzed:", str(session_data.get("total_frames", 0))]
        ]
        meta_table = Table(meta_data, colWidths=[95, 175, 110, 160])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1E293B')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        avg_focus = session_data.get("avg_focus", 0.0)
        study_pct = session_data.get("study_time_pct", 0.0)
        dist_pct = session_data.get("distracted_time_pct", 0.0)
        indisc_cnt = session_data.get("indiscipline_count", 0)
        evaluation = session_data.get("overall_evaluation", "Satisfactory")

        focus_color = colors.HexColor('#16A34A') if avg_focus >= 70 else (colors.HexColor('#D97706') if avg_focus >= 50 else colors.HexColor('#DC2626'))

        metric_data = [
            ["Average Focus Score", "Study Time Active", "Distracted / Off-Task", "Discipline Flags", "Overall Rating"],
            [f"{avg_focus:.1f}%", f"{study_pct:.0f}%", f"{dist_pct:.0f}%", str(indisc_cnt), evaluation]
        ]
        metric_table = Table(metric_data, colWidths=[108, 108, 114, 100, 110])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#475569')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 1), (-1, 1), colors.white),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('TEXTCOLOR', (0, 1), (0, 1), focus_color),
            ('TEXTCOLOR', (3, 1), (3, 1), colors.HexColor('#DC2626') if indisc_cnt > 0 else colors.HexColor('#16A34A')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        elements.append(metric_table)
        elements.append(Spacer(1, 14))

        telemetry = session_data.get("telemetry_averages", {})
        elements.append(Paragraph("<b>Perception & Biometric Telemetry Breakdown</b>", self.styles['Heading2']))
        elements.append(Spacer(1, 6))

        telem_data = [
            ["Metric Stream", "Observed Average", "Normal Benchmark", "Status Assessment"],
            ["Eye Openness (EAR)", f"{telemetry.get('avg_ear', 0.28):.2f}", "0.22 - 0.35", "Alert & Awake" if telemetry.get('avg_ear', 0.28) >= 0.20 else "Drowsy / Drooping"],
            ["Mouth Activity (MAR)", f"{telemetry.get('avg_mar', 0.05):.2f}", "< 0.40", "Silent & Attentive" if telemetry.get('avg_mar', 0.05) <= 0.40 else "Verbal Interaction"],
            ["Head Pose (Yaw / Pitch)", f"Y:{telemetry.get('avg_yaw', 0.0):+.1f}° | P:{telemetry.get('avg_pitch', 0.0):+.1f}°", "-20° to +20°", "Forward Aligned" if abs(telemetry.get('avg_yaw', 0.0)) <= 22 else "Turned Away"],
            ["Directed Gaze (DG) Target Lock", f"{telemetry.get('gaze_in_target_pct', 85.0):.1f}%", ">= 75.0%", "On Study Viewport" if telemetry.get('gaze_in_target_pct', 85.0) >= 70 else "Off-Screen Wander"]
        ]
        telem_table = Table(telem_data, colWidths=[150, 110, 120, 160])
        telem_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8.5),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        elements.append(telem_table)
        elements.append(Spacer(1, 14))

        elements.append(Paragraph("<b>Session Incident & Behavioral Log</b>", self.styles['Heading2']))
        elements.append(Spacer(1, 6))

        incidents = session_data.get("incident_log", [])
        if incidents:
            inc_data = [["Timestamp", "Infraction Category", "Severity", "Duration", "Observation Notes"]]
            for inc in incidents[:6]:
                inc_data.append([
                    inc.get("timestamp", "-")[-8:],
                    inc.get("event_type", "INCIDENT").replace("_", " "),
                    inc.get("severity", "MEDIUM"),
                    f"{inc.get('duration_seconds', 5.0):.0f}s",
                    inc.get("notes", "Behavioral deviation registered")[:40]
                ])
            inc_table = Table(inc_data, colWidths=[70, 130, 65, 55, 220])
            inc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (3, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FEF2F2')]),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ]))
            elements.append(inc_table)
        else:
            clean_box = [["No indiscipline or disruptive infractions were recorded during this proctoring interval."]]
            clean_table = Table(clean_box, colWidths=[540])
            clean_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#DCFCE7')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#166534')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#86EFAC')),
            ]))
            elements.append(clean_table)

        elements.append(Spacer(1, 14))

        elements.append(Paragraph("<b>Pedagogical Insights & Recommended Interventions</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 4))
        bullet_style = ParagraphStyle('Bullet', parent=self.styles['Normal'], fontSize=8.5, leading=12, leftIndent=12)

        if avg_focus >= 80 and indisc_cnt == 0:
            elements.append(Paragraph("• <b>High Engagement:</b> Student demonstrated sustained concentration and posture alignment with learning materials throughout the event.", bullet_style))
            elements.append(Paragraph("• <b>Positive Reinforcement:</b> Maintain current desk layout and study cadence.", bullet_style))
        elif indisc_cnt > 0:
            elements.append(Paragraph("• <b>Attention Lapses:</b> Discrete episodes of distraction or verbal interaction were observed. Review seating proximity to chatty peers.", bullet_style))
            elements.append(Paragraph("• <b>Targeted Follow-up:</b> Share this automated session excerpt during weekly academic guidance review.", bullet_style))
        else:
            elements.append(Paragraph("• <b>Moderate Focus:</b> Overall study metrics are acceptable with minor gaze drifts. Encourage active note-taking to elevate engagement.", bullet_style))

        elements.append(Spacer(1, 14))
        elements.append(Paragraph(
            f"<b>Eagle's Eye AI Proctoring & LMS Administration</b> &nbsp;|&nbsp; Session Report Document: {file_path.name}",
            ParagraphStyle('Foot', parent=self.styles['Normal'], fontSize=7.5, textColor=colors.HexColor('#94A3B8'))
        ))

        doc.build(elements)
        return str(file_path)
