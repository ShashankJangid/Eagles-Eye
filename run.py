import sys
import argparse
import subprocess
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.study_detector import StudyDetectorPipeline
from services.lms_service import LMSService
from services.escalation_service import EscalationService
from database.db_manager import DBManager

def run_streamlit_ui():
    app_path = Path(__file__).resolve().parent / "ui" / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    print(f"[Eagle's Eye] Launching Web Interface: {' '.join(cmd)}")
    subprocess.run(cmd)

def run_cli_proctoring(camera_source="synthetic", duration_sec=15, student_id="STU-101"):
    print(f"\n=======================================================")
    print(f"[EAGLE'S EYE] AI Camera & DG Multi-Modal Proctoring")
    print(f"=======================================================")
    print(f"Student: {student_id} | Source: {camera_source} | Duration: {duration_sec}s")
    
    pipeline = StudyDetectorPipeline(camera_source=camera_source, student_id=student_id)
    start_t = time.time()
    frame_idx = 0

    try:
        while time.time() - start_t < duration_sec:
            frame_idx += 1
            res = pipeline.step()
            if not res["success"]:
                print("[ERROR] Camera feed error.")
                break

            fusion = res["fusion_result"]
            cv_res = res["cv_result"]
            dg = fusion["dg_data"]

            state = fusion["study_state"]
            focus = fusion["focus_score"]
            ear = cv_res["ear"]
            mar = cv_res["mar"]
            yaw = cv_res["head_pose"]["yaw"]

            indisc_msg = f" | [FLAG: {fusion['indiscipline_type']}]" if fusion["indiscipline_flag"] else ""
            print(f"[{frame_idx:03d}] State: {state:<22} | Focus: {focus:5.1f}% | EAR: {ear:.2f} | MAR: {mar:.2f} | Yaw: {yaw:+5.1f}° | DG Focus: {dg['dg_focus_score']:3.0f}%{indisc_msg}")
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[Eagle's Eye] Proctoring stopped by user.")
    finally:
        pipeline.release()
        print(f"\n[Eagle's Eye] Session concluded. Logged {frame_idx} frames to database.")

def run_lms_dispatch():
    print("\n[Eagle's Eye] Dispatching Daily Teacher LMS Report...")
    lms = LMSService()
    res = lms.dispatch_daily_report_to_lms()
    print(f"[STATUS] {res['status']}")
    print(f"[RECORDS] {res['synced_records']} students synced")
    print(f"[PDF] {res['pdf_report_path']}")

def run_weekly_escalation():
    print("\n[Eagle's Eye] Evaluating Weekly Student Indiscipline for Parent Escalation...")
    esc = EscalationService()
    results = esc.evaluate_weekly_reports()
    print(f"\nAnalyzed {len(results)} students over past 7 days:")
    for r in results:
        status_sym = "[PARENT ESCALATION]" if r["is_escalated"] else "[NORMAL]"
        print(f" - {r['student_id']}: {r['name']:<16} | Focus: {r['avg_focus_pct']:4.1f}% | Indiscipline: {r['total_indiscipline_count']} flags | {status_sym}")
        if r["is_escalated"]:
            print(f"     -> Parent PDF: {r['pdf_path']}")
            print(f"     -> Notified: {r['parent_name']} ({r['parent_email']})")

def main():
    parser = argparse.ArgumentParser(description="Eagle's Eye - AI Classroom & Student Attention System")
    parser.add_argument("--ui", action="store_true", help="Launch the Streamlit interactive dashboard")
    parser.add_argument("--cli", action="store_true", help="Run live camera & DG proctoring in terminal")
    parser.add_argument("--source", type=str, default="synthetic", help="Camera source: 0 for webcam, 'synthetic' for simulation")
    parser.add_argument("--student", type=str, default="STU-103", help="Student ID to proctor")
    parser.add_argument("--duration", type=int, default=15, help="Duration in seconds for CLI proctoring")
    parser.add_argument("--lms", action="store_true", help="Generate and sync Daily LMS Report for teachers")
    parser.add_argument("--escalate", action="store_true", help="Evaluate weekly indiscipline and escalate to parents")

    args = parser.parse_args()

    if args.cli:
        run_cli_proctoring(camera_source=args.source, duration_sec=args.duration, student_id=args.student)
    elif args.lms:
        run_lms_dispatch()
    elif args.escalate:
        run_weekly_escalation()
    else:
        run_streamlit_ui()

if __name__ == "__main__":
    main()
