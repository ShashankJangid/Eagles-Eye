# 🦅 Eagle's Eye: AI Camera & DG Data Student Attention Monitoring System

**Eagle's Eye** is a multi-modal classroom proctoring and student attention analysis system. It fuses **Computer Vision (CV) facial expression cues** with **Directed Gaze (DG) telemetry** to determine whether students are actively studying, passively attending, distracted, drowsy, or disruptive.

It automates:
1. **Daily Teacher Reports via LMS**: Synchronizes daily attention percentage, study time, and engagement indicators to the school's Learning Management System (Canvas / Moodle / Google Classroom).
2. **Weekly Parent Escalations**: Automatically detects students exceeding indiscipline thresholds (e.g. repeated talking, mobile phone usage, sustained inattention, sleeping) over the week and generates official PDF reports & notifications for parents.

---

## 🏛️ System Architecture

```
[ AI Camera Stream ]               [ DG Telemetry Stream ]
 (Webcam / RTSP / Sim)               (Directed Gaze & Desk Gestures)
        │                                    │
        ▼                                    ▼
[ 478 Face Mesh & Blendshapes ]     [ Gaze Viewport & Fixation Engine ]
  • Eye Aspect Ratio (EAR)            • Gaze (x, y) target coordinates
  • Mouth Aspect Ratio (MAR)          • Fixation duration (ms)
  • 3D Head Pose (Yaw, Pitch, Roll)   • Screen gesture state
  • Facial Expression / Affect
        │                                    │
        └─────────────────┬──────────────────┘
                          ▼
            [ Multi-Modal Fusion Engine ]
              • Continuous Focus Index (0-100%)
              • State Classifier:
                - STUDYING_FOCUSED
                - STUDYING_PASSIVE
                - DISTRACTED_LOOKING_AWAY
                - DROWSY_SLEEPING
                - INDISCIPLINE_TALKING
                - INDISCIPLINE_ABSENT
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
 [ Daily LMS Service ]             [ Weekly Escalation Service ]
  • Daily focus aggregation         • 7-day cumulative analytics
  • Canvas/Moodle LTI sync          • Threshold trigger (>= 5 flags)
  • Teacher Daily PDF Report        • Confidential Parent Dossier (PDF)
                                    • Automated Parent Email/SMS Notice
```

---

## 🚀 Quick Start

### 1. Requirements
Ensure Python 3.10+ is installed. Dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch Interactive Web Dashboard
Run the full Streamlit web interface with real-time proctoring, Teacher LMS portal, and Parent Escalation center:
```bash
python run.py --ui
```
or directly:
```bash
streamlit run ui/app.py
```

### 3. Run CLI Proctoring Engine
To proctor a student directly from the terminal (works with physical webcam `0` or simulated classroom video):
```bash
# Run 15-second simulation
python run.py --cli --source synthetic --student STU-101 --duration 15

# Run with physical webcam
python run.py --cli --source 0 --student STU-101 --duration 30
```

### 4. Dispatch Daily Teacher LMS Report
```bash
python run.py --lms
```

### 5. Evaluate & Trigger Weekly Parent Escalations
```bash
python run.py --escalate
```

---

## 📁 Project Structure

```
Eagle's eye/
├── config.py                 # System thresholds, weights, LMS endpoints
├── run.py                    # Unified CLI and UI runner
├── database/
│   ├── models.py             # SQLite database schemas
│   └── db_manager.py         # DB operations, queries, and student seeding
├── core/
│   ├── camera.py             # Video capture (Webcam, RTSP, Synthetic student stream)
│   ├── face_mesh_detector.py # MediaPipe 478 landmarks, EAR, MAR, head pose & affect
│   ├── dg_fusion.py          # Directed Gaze & digital gestures multi-modal fusion
│   └── study_detector.py     # Main real-time pipeline & HUD renderer
├── services/
│   ├── lms_service.py        # Daily LMS aggregation, Canvas/Moodle JSON & sync
│   ├── escalation_service.py # Weekly parent threshold analysis & notification composer
│   └── pdf_generator.py      # ReportLab automated PDF report generator
├── ui/
│   ├── app.py                # Streamlit control panel & interactive dashboard
│   └── components.py         # UI styling, metric cards, badges
├── tests/
│   ├── test_cv_engine.py     # Tests for face mesh, blendshapes, and DG fusion
│   └── test_lms_and_reports.py # Tests for LMS sync and parent PDF creation
├── data/
│   ├── models/               # MediaPipe FaceLandmarker model file
│   └── eagles_eye.db         # SQLite persistent database
└── reports/                  # Generated Daily Teacher and Weekly Parent PDFs
```

---

## 📊 Daily LMS Payload Specification

Eagle's Eye outputs industry-compliant LTI engagement JSON payloads:
```json
{
  "lms_provider": "Canvas",
  "version": "v1.2",
  "course": {
    "course_name": "Grade 10 - Science & Mathematics",
    "course_code": "SCI-MTH-10"
  },
  "student": {
    "student_id": "STU-101",
    "name": "Aarav Sharma"
  },
  "engagement_metrics": {
    "date": "2026-10-21",
    "total_monitored_minutes": 60.0,
    "active_study_minutes": 54.0,
    "focus_percentage": 90.0,
    "indiscipline_incidents": 0,
    "attendance_status": "PRESENT",
    "study_evaluation": "EXEMPLARY"
  }
}
```

---

## 👨‍👩‍👧 Weekly Parent Escalation Mechanism

When a student triggers $\ge 5$ indiscipline infractions or maintains $< 50\%$ focus over a 7-day period:
1. **Dossier Compilation**: System queries all timestamps, behavior classifications, and duration of disruptions.
2. **Confidential Parent PDF Generation**: ReportLab compiles an official report card with recommendations.
3. **Notification Transmission**: Dispatches formal email & SMS alerts to parents detailing the incident history and next steps.
