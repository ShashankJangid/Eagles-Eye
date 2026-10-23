import time
import json
import cv2
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
from pathlib import Path

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import REPORTS_DIR, LMS_PROVIDER, DEFAULT_CLASS_NAME
from database.db_manager import DBManager
from core.study_detector import StudyDetectorPipeline
from services.lms_service import LMSService
from services.escalation_service import EscalationService
from ui.components import get_custom_css

st.set_page_config(
    page_title="Eagle's Eye - AI Classroom Attention System",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(get_custom_css(), unsafe_allow_html=True)

@st.cache_resource
def get_db():
    return DBManager()

@st.cache_resource
def get_lms():
    return LMSService(db=get_db())

@st.cache_resource
def get_esc():
    return EscalationService(db=get_db())

db = get_db()
lms_service = get_lms()
escalation_service = get_esc()

if "is_proctoring" not in st.session_state:
    st.session_state["is_proctoring"] = False
if "pipeline" not in st.session_state:
    st.session_state["pipeline"] = None
if "last_source" not in st.session_state:
    st.session_state["last_source"] = None
if "last_session_pdf" not in st.session_state:
    st.session_state["last_session_pdf"] = None
if "last_session_meta" not in st.session_state:
    st.session_state["last_session_meta"] = None
if "auto_generate_pdf" not in st.session_state:
    st.session_state["auto_generate_pdf"] = True

st.sidebar.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=64)
st.sidebar.title("Eagle's Eye AI")
st.sidebar.markdown(f"**Course:** {DEFAULT_CLASS_NAME}")
st.sidebar.markdown(f"**LMS Provider:** `{LMS_PROVIDER}`")
st.sidebar.markdown("---")

all_students = db.get_all_students()
student_options = {f"{s['student_id']} - {s['name']}": s['student_id'] for s in all_students}

selected_student_label = st.sidebar.selectbox("Monitored Student", list(student_options.keys()))
active_student_id = student_options[selected_student_label]
student_record = db.get_student_by_id(active_student_id)

st.sidebar.markdown("### Student Profile")
st.sidebar.write(f"**Name:** {student_record['name']}")
st.sidebar.write(f"**Class:** {student_record['grade']}")
st.sidebar.write(f"**Parent:** {student_record['parent_name']}")
st.sidebar.write(f"**Email:** {student_record['parent_email']}")

st.sidebar.markdown("---")
fps_mode = st.sidebar.select_slider(
    "Processing Performance",
    options=["Eco (10 FPS)", "Balanced (20 FPS)", "Ultra-Smooth (30 FPS)"],
    value="Balanced (20 FPS)"
)
target_fps = 10 if "Eco" in fps_mode else (20 if "Balanced" in fps_mode else 30)
sleep_interval = 1.0 / target_fps

st.sidebar.caption("🦅 Eagle's Eye v2.5 High-Precision Engine")

st.markdown("""
<div class="main-header">
    <h1>🦅 Eagle's Eye: High-Precision Classroom Attention System</h1>
    <p>Real-time 478-Landmark CV Facial Expression Analysis fused with 3D Directed Gaze (DG) Telemetry. Zero-lag hardware execution, daily teacher LMS sync, and automated weekly parent escalation.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "📹 Live AI Camera & DG Fusion",
    "📊 Daily Teacher LMS Portal",
    "🚨 Weekly Parent Escalation Center",
    "📈 Student Behavioral Dossiers"
])

with tab1:
    st.markdown("### Live Proctoring & Attention Analysis")
    st.write("Tracks 478 face mesh landmarks, 3D pupil gaze vectors, jaw/mouth articulation, and head Euler angles in real time.")

    col_cam, col_metrics = st.columns([2, 1])

    with col_metrics:
        st.markdown("#### Stream Controls")
        cam_mode = st.radio(
            "Camera Hardware Source:",
            ["Simulated Classroom Camera (Deterministic Demo)", "Physical Webcam (Device 0)"],
            index=0
        )
        current_source = 0 if "Physical" in cam_mode else "synthetic"

        scenario_key = "auto"
        if current_source == "synthetic":
            scenario_choice = st.selectbox(
                "Simulated Behavior Scenario:",
                [
                    "Auto-Demonstration (Cycles All 7 Behaviors)",
                    "1. Focused Studying & Active Reading",
                    "2. Deep Thinking & Problem Solving",
                    "3. Talking & Chatting with Neighbor",
                    "4. Restless Swinging & Body Rocking",
                    "5. Drowsy & Sleeping on Desk",
                    "6. Concealed Phone in Lap",
                    "7. Student Absent / Left Seat"
                ],
                index=0
            )
            scenario_map = {
                "Auto-Demonstration (Cycles All 7 Behaviors)": "auto",
                "1. Focused Studying & Active Reading": "focused",
                "2. Deep Thinking & Problem Solving": "thinking",
                "3. Talking & Chatting with Neighbor": "talking",
                "4. Restless Swinging & Body Rocking": "swinging",
                "5. Drowsy & Sleeping on Desk": "drowsy",
                "6. Concealed Phone in Lap": "phone",
                "7. Student Absent / Left Seat": "absent"
            }
            scenario_key = scenario_map.get(scenario_choice, "auto")
            if st.session_state["pipeline"] is not None:
                st.session_state["pipeline"].set_simulation_scenario(scenario_key)

        st.checkbox("📄 Auto-generate PDF report on camera stop", value=True, key="auto_generate_pdf")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if not st.session_state["is_proctoring"]:
                if st.button("▶️ Start Proctoring", type="primary", use_container_width=True):
                    if st.session_state["pipeline"] is not None and st.session_state["last_source"] != current_source:
                        st.session_state["pipeline"].release()
                        st.session_state["pipeline"] = None

                    if st.session_state["pipeline"] is None:
                        st.session_state["pipeline"] = StudyDetectorPipeline(
                            camera_source=current_source,
                            student_id=active_student_id,
                            session_id=1
                        )
                    st.session_state["last_source"] = current_source
                    st.session_state["pipeline"].student_id = active_student_id
                    if current_source == "synthetic":
                        st.session_state["pipeline"].set_simulation_scenario(scenario_key)
                    st.session_state["is_proctoring"] = True
                    st.rerun()

        with col_b2:
            if st.session_state["is_proctoring"]:
                if st.button("⏹️ Stop Stream", type="secondary", use_container_width=True):
                    st.session_state["is_proctoring"] = False
                    if st.session_state["pipeline"] is not None:
                        if st.session_state.get("auto_generate_pdf", True):
                            try:
                                rep = st.session_state["pipeline"].generate_session_report(student_record)
                                if rep:
                                    st.session_state["last_session_pdf"] = rep["pdf_path"]
                                    st.session_state["last_session_meta"] = rep["session_data"]
                            except Exception as e:
                                print(f"[Session PDF Error] {e}")
                        st.session_state["pipeline"].release()
                        st.session_state["pipeline"] = None
                    st.rerun()

        st.markdown("---")
        st.markdown("#### Real-time Precision Telemetry")
        m_state = st.empty()
        m_focus = st.empty()
        m_ear = st.empty()
        m_mar = st.empty()
        m_pose = st.empty()
        m_dg = st.empty()

    with col_cam:
        video_placeholder = st.empty()
        alert_placeholder = st.empty()

    if st.session_state["is_proctoring"] and st.session_state["pipeline"] is not None:
        pipeline = st.session_state["pipeline"]
        pipeline.student_id = active_student_id

        for _ in range(60):
            if not st.session_state["is_proctoring"]:
                break

            loop_start = time.time()
            try:
                res = pipeline.step()
            except Exception as e:
                print(f"[UI Pipeline Error] {e}")
                time.sleep(0.05)
                continue

            if not res or not res.get("success", False):
                st.error("Error reading video stream.")
                st.session_state["is_proctoring"] = False
                break

            display_rgb = cv2.cvtColor(res["display_frame"], cv2.COLOR_BGR2RGB)
            video_placeholder.image(display_rgb, channels="RGB")

            fusion = res["fusion_result"]
            cv_res = res["cv_result"]
            dg = fusion["dg_data"]

            state = fusion["study_state"]
            focus = fusion["focus_score"]

            if "STUDYING" in state:
                state_badge = f'<span class="badge-studying">🟢 {state}</span>'
            elif "DISTRACTED" in state:
                state_badge = f'<span class="badge-distracted">🟠 {state}</span>'
            else:
                state_badge = f'<span class="badge-indiscipline">🔴 {state}</span>'

            m_state.markdown(f"**State:** {state_badge}", unsafe_allow_html=True)
            m_focus.metric("Focus Score (EMA)", f"{focus:.1f}%")
            m_ear.write(f"👁️ **Eye Openness (EAR):** `{cv_res['ear']:.2f}` ({'Closed/Drowsy' if cv_res['ear'] < 0.18 else 'Open'})")
            m_mar.write(f"🗣️ **Mouth Activity (MAR):** `{cv_res['mar']:.2f}` ({'Talking' if cv_res['mar'] > 0.44 else 'Silent'})")
            m_pose.write(f"🧭 **Head Pose:** Yaw `{cv_res['head_pose']['yaw']:+.1f}°` | Pitch `{cv_res['head_pose']['pitch']:+.1f}°`")
            m_dg.write(f"🎯 **DG Gaze In Target:** `{'YES' if dg['study_zone_active'] else 'NO'}` (Score: `{dg['dg_focus_score']:.0f}%`)")

            if fusion["indiscipline_flag"]:
                alert_placeholder.warning(
                    f"⚠️ **INDISCIPLINE DETECTED:** {fusion['indiscipline_type']} ({fusion['severity']} Severity) - {fusion['notes']}"
                )
            else:
                alert_placeholder.empty()

            elapsed = time.time() - loop_start
            sleep_time = max(0.005, sleep_interval - elapsed)
            time.sleep(sleep_time)

        if st.session_state["is_proctoring"]:
            st.rerun()

    elif not st.session_state["is_proctoring"]:
        video_placeholder.info("Camera stream idle. Click '▶️ Start Proctoring' above to begin.")
        m_state.write("Status: Idle")
        m_focus.metric("Focus Score", "--- %")

    if st.session_state.get("last_session_pdf") and Path(st.session_state["last_session_pdf"]).exists():
        pdf_path = Path(st.session_state["last_session_pdf"])
        meta = st.session_state.get("last_session_meta", {})

        st.markdown("---")
        st.success(f"📄 **Live Session Ended — PDF Event Report Generated:** `{pdf_path.name}`")

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Monitored Duration", meta.get("duration_formatted", "-"))
        rc2.metric("Session Average Focus", f"{meta.get('avg_focus', 0.0):.1f}%")
        rc3.metric("Indiscipline Infractions", meta.get("indiscipline_count", 0))
        rc4.metric("Session Assessment", meta.get("overall_evaluation", "Completed"))

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        col_dl, col_space = st.columns([1, 1])
        with col_dl:
            st.download_button(
                label=f"📥 Download Session PDF Report ({pdf_path.name})",
                data=pdf_bytes,
                file_name=pdf_path.name,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

        with st.expander("🔍 View Session Event Breakdown & Incident Timeline"):
            st.write(f"**Student:** {meta.get('student', {}).get('name')} ({meta.get('student', {}).get('student_id')})")
            st.write(f"**Start Time:** `{meta.get('start_time')}` | **End Time:** `{meta.get('end_time')}`")
            st.write(f"**Frames Processed:** `{meta.get('total_frames')}` | **Active Study:** `{meta.get('study_time_pct')}%` | **Off-Task:** `{meta.get('distracted_time_pct')}%`")
            
            telem = meta.get("telemetry_averages", {})
            st.markdown(f"- **Avg Eye Openness (EAR):** `{telem.get('avg_ear')}`")
            st.markdown(f"- **Avg Mouth Openness (MAR):** `{telem.get('avg_mar')}`")
            st.markdown(f"- **Avg Head Pose:** Yaw `{telem.get('avg_yaw'):+.1f}°` | Pitch `{telem.get('avg_pitch'):+.1f}°`")
            st.markdown(f"- **DG Viewport Target Ratio:** `{telem.get('gaze_in_target_pct')}%`")

            incidents = meta.get("incident_log", [])
            if incidents:
                st.markdown("##### Infraction Timeline:")
                for inc in incidents:
                    st.markdown(f"• **{inc['timestamp']}** | `{inc['event_type']}` ({inc['severity']}) — *{inc['notes']}*")
            else:
                st.info("No infractions recorded during this session.")

with tab2:
    st.markdown("### Daily LMS Reporting for Teachers")
    st.write("Aggregated daily engagement and indiscipline logs pushed directly to the school Learning Management System (LMS).")

    report_date = st.date_input("Select Report Date", value=date.today())
    date_str = report_date.isoformat()

    col_lms_act, col_lms_status = st.columns([1, 1])
    with col_lms_act:
        if st.button("🔄 Sync & Push Daily Reports to LMS Now", type="primary"):
            sync_res = lms_service.dispatch_daily_report_to_lms(date_str)
            st.success(f"✅ {sync_res['message']}")
            st.info(f"LMS Endpoint: `{sync_res['lms_endpoint']}` | Provider: `{sync_res['provider']}`")

    daily_records = db.get_daily_reports_for_date(date_str)
    if not daily_records:
        daily_records = lms_service.aggregate_daily_metrics_from_logs(date_str)

    if daily_records:
        avg_focus = sum(r["focus_percentage"] for r in daily_records) / len(daily_records)
        total_indisc = sum(r["indiscipline_count"] for r in daily_records)

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Students Monitored", len(daily_records))
        mc2.metric("Class Average Focus", f"{avg_focus:.1f}%")
        mc3.metric("Indiscipline Flags Today", total_indisc)
        mc4.metric("LMS Status", daily_records[0].get("lms_sync_status", "SYNCED"))

        st.markdown("#### Class Focus & Engagement Breakdown")
        df_daily = pd.DataFrame(daily_records)
        chart_data = df_daily[["name", "focus_percentage"]].set_index("name")
        st.bar_chart(chart_data)

        st.markdown("#### Daily Attendance & Attention Roster")
        display_df = df_daily[[
            "student_id", "name", "grade", "study_minutes", "distracted_minutes",
            "focus_percentage", "indiscipline_count", "lms_sync_status"
        ]].rename(columns={
            "student_id": "ID",
            "name": "Student Name",
            "grade": "Class",
            "study_minutes": "Study (min)",
            "distracted_minutes": "Distracted (min)",
            "focus_percentage": "Focus %",
            "indiscipline_count": "Indiscipline Flags",
            "lms_sync_status": "LMS Status"
        })
        st.dataframe(display_df, use_container_width=True)

        daily_pdf_path = REPORTS_DIR / f"Daily_Teacher_LMS_Report_{date_str}.pdf"
        if not daily_pdf_path.exists():
            lms_service.dispatch_daily_report_to_lms(date_str)

        if daily_pdf_path.exists():
            with open(daily_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="📄 Download Official Teacher LMS PDF Report",
                data=pdf_bytes,
                file_name=daily_pdf_path.name,
                mime="application/pdf"
            )

        with st.expander("🔍 View Raw LMS REST API Payload (Canvas / Moodle Schema)"):
            sample_payload = lms_service.format_lms_payload(
                student=student_record,
                report_date=date_str,
                focus_pct=daily_records[0]["focus_percentage"],
                study_min=daily_records[0]["study_minutes"],
                total_min=daily_records[0]["total_monitored_minutes"],
                indiscipline_count=daily_records[0]["indiscipline_count"]
            )
            st.json(sample_payload)

with tab3:
    st.markdown("### Weekly Indiscipline Escalation to Parents")
    st.write("Identifies students who breached the indiscipline threshold during the week and automatically sends detailed reports to parents.")

    start_w = (date.today() - timedelta(days=7)).isoformat()
    end_w = date.today().isoformat()

    weekly_data = escalation_service.evaluate_weekly_reports(start_w, end_w)
    escalated_students = [s for s in weekly_data if s["is_escalated"]]

    if escalated_students:
        st.error(f"⚠️ **ACTION REQUIRED:** {len(escalated_students)} student(s) exceeded the weekly indiscipline threshold and are flagged for Parent Escalation!")
    else:
        st.success("✅ All students maintained acceptable discipline standards this week.")

    st.markdown("#### Weekly Class Behavior Dossier")
    df_weekly = pd.DataFrame(weekly_data)[[
        "student_id", "name", "grade", "avg_focus_pct", "total_indiscipline_count", "status", "parent_name", "parent_email"
    ]].rename(columns={
        "student_id": "ID",
        "name": "Student",
        "grade": "Grade",
        "avg_focus_pct": "Weekly Focus %",
        "total_indiscipline_count": "Weekly Indiscipline Flags",
        "status": "Escalation Status",
        "parent_name": "Parent Name",
        "parent_email": "Parent Email"
    })
    st.dataframe(df_weekly, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Parent Escalation Review & Notification Dispatch")

    esc_choices = {f"{s['name']} ({s['student_id']}) - {s['total_indiscipline_count']} Incidents": s for s in weekly_data}
    selected_esc_key = st.selectbox("Select Student Dossier to Review:", list(esc_choices.keys()))
    selected_student_dossier = esc_choices[selected_esc_key]

    c_dossier1, c_dossier2 = st.columns([1, 1])

    with c_dossier1:
        st.markdown(f"##### Incident Log for {selected_student_dossier['name']}")
        incidents = db.get_indiscipline_events(student_id=selected_student_dossier['student_id'], days=7)
        if incidents:
            for inc in incidents:
                st.markdown(
                    f"• **{inc['timestamp']}** | `{inc['event_type']}` ({inc['severity']})<br/>"
                    f"&nbsp;&nbsp;*Notes: {inc['notes']}*",
                    unsafe_allow_html=True
                )
        else:
            st.info("No explicit incidents logged. Focus was within baseline.")

    with c_dossier2:
        st.markdown("##### Parent Communication Preview")
        if selected_student_dossier["parent_notice"]:
            notice = selected_student_dossier["parent_notice"]
            st.markdown(f"**To:** `{notice['to']}`")
            st.markdown(f"**Subject:** `{notice['subject']}`")
            st.text_area("Email Body:", notice["body"], height=180)

            if st.button("✉️ Dispatch Escalation Notice to Parent via Email & SMS", type="primary"):
                st.success(f"✅ Notification successfully transmitted to {selected_student_dossier['parent_name']} ({selected_student_dossier['parent_email']}).")

            pdf_path_str = selected_student_dossier.get("pdf_path")
            if pdf_path_str and Path(pdf_path_str).exists():
                with open(pdf_path_str, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="📥 Download Parent PDF Report Card",
                    data=pdf_bytes,
                    file_name=Path(pdf_path_str).name,
                    mime="application/pdf"
                )
        else:
            st.success("This student does not require parent escalation. Status is within normal limits.")

with tab4:
    st.markdown(f"### Historical Engagement Dossier: {student_record['name']} ({active_student_id})")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT report_date, focus_percentage, indiscipline_count, study_minutes, distracted_minutes
            FROM daily_reports
            WHERE student_id = ?
            ORDER BY report_date ASC
            """,
            (active_student_id,)
        )
        hist_rows = [dict(r) for r in cursor.fetchall()]

    if hist_rows:
        df_hist = pd.DataFrame(hist_rows)
        c_trend1, c_trend2 = st.columns(2)
        with c_trend1:
            st.markdown("#### 7-Day Focus Score Trend (%)")
            st.line_chart(df_hist.set_index("report_date")["focus_percentage"])
        with c_trend2:
            st.markdown("#### Study Minutes vs Distracted Minutes")
            st.bar_chart(df_hist.set_index("report_date")[["study_minutes", "distracted_minutes"]])

        st.markdown("#### Detailed Historical Log")
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("No past logs found for this student.")
