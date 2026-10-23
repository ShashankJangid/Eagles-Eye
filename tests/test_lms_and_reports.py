from pathlib import Path
from services.lms_service import LMSService
from services.escalation_service import EscalationService
from services.pdf_generator import PDFReportGenerator
from database.db_manager import DBManager

def test_lms_daily_aggregation_and_pdf():
    db = DBManager()
    lms = LMSService(db=db)
    res = lms.dispatch_daily_report_to_lms()

    assert res["status"] == "SUCCESS"
    assert res["synced_records"] > 0
    assert Path(res["pdf_report_path"]).exists()

def test_weekly_escalation_and_parent_pdf():
    db = DBManager()
    esc = EscalationService(db=db)
    results = esc.evaluate_weekly_reports()

    assert len(results) > 0
    escalated = [r for r in results if r["is_escalated"]]
    assert len(escalated) > 0

    for esc_student in escalated:
        assert esc_student["parent_notice"] is not None
        assert "to" in esc_student["parent_notice"]
        assert "subject" in esc_student["parent_notice"]
        assert esc_student["pdf_path"] is not None
        assert Path(esc_student["pdf_path"]).exists()

def test_auto_session_pdf_generation():
    from core.study_detector import StudyDetectorPipeline
    pipeline = StudyDetectorPipeline(camera_source="synthetic", student_id="STU-102")
    for _ in range(5):
        pipeline.step()
    rep = pipeline.generate_session_report()
    assert rep is not None
    assert "pdf_path" in rep
    assert Path(rep["pdf_path"]).exists()
    assert rep["session_data"]["total_frames"] == 5
    pipeline.release()
