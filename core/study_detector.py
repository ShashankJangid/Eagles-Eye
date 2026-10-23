import time
import cv2
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from core.camera import VideoStreamHandler
from core.face_mesh_detector import FaceMeshDetector
from core.dg_fusion import DGFusionEngine
from database.db_manager import DBManager

class StudyDetectorPipeline:
    def __init__(self, camera_source=0, student_id: str = "STU-101", session_id: int = 1):
        self.camera_source = camera_source
        self.student_id = student_id
        self.session_id = session_id

        self.stream = VideoStreamHandler(source=camera_source)
        self.detector = FaceMeshDetector()
        self.fusion = DGFusionEngine()
        self.db = DBManager()

        self.last_log_time = 0.0
        self.last_indiscipline_log_time = 0.0
        self.frame_counter = 0

        self.session_start = datetime.now()
        self.frame_history = []
        self.session_incidents = []

    def step(self, external_dg_packet: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.frame_counter += 1
        ret, raw_frame = self.stream.read_frame()
        if not ret or raw_frame is None:
            return {"success": False, "error": "Unable to read frame"}

        if getattr(self.stream, "is_synthetic", False) and hasattr(self.stream, "last_synthetic_telemetry"):
            cv_result = self.detector.process_synthetic_telemetry(raw_frame, self.stream.last_synthetic_telemetry)
        else:
            cv_result = self.detector.process_frame(raw_frame)

        fusion_result = self.fusion.fuse(cv_result, external_dg_packet)
        display_frame = self._render_dashboard_hud(cv_result["annotated_frame"], fusion_result, cv_result)

        now = time.time()
        if now - self.last_log_time >= 1.0:
            self.last_log_time = now
            self.db.log_frame(
                session_id=self.session_id,
                student_id=self.student_id,
                focus_score=fusion_result["focus_score"],
                study_state=fusion_result["study_state"],
                ear=cv_result["ear"],
                mar=cv_result["mar"],
                yaw=cv_result["head_pose"]["yaw"],
                pitch=cv_result["head_pose"]["pitch"],
                dg_gaze_score=fusion_result["dg_data"]["dg_focus_score"],
                emotion=cv_result["facial_expression"]
            )

        dg_info = fusion_result.get("dg_data", {})
        self.frame_history.append({
            "focus_score": fusion_result.get("focus_score", 0.0),
            "study_state": fusion_result.get("study_state", "UNKNOWN"),
            "ear": cv_result.get("ear", 0.28),
            "mar": cv_result.get("mar", 0.05),
            "yaw": cv_result.get("head_pose", {}).get("yaw", 0.0),
            "pitch": cv_result.get("head_pose", {}).get("pitch", 0.0),
            "dg_score": dg_info.get("dg_focus_score", 50.0),
            "in_target": dg_info.get("study_zone_active", True)
        })

        if fusion_result["indiscipline_flag"] and (now - self.last_indiscipline_log_time >= 5.0):
            self.last_indiscipline_log_time = now
            self.session_incidents.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": fusion_result["indiscipline_type"],
                "duration_seconds": 5.0,
                "severity": fusion_result["severity"],
                "notes": fusion_result["notes"]
            })
            self.db.log_indiscipline_event(
                session_id=self.session_id,
                student_id=self.student_id,
                event_type=fusion_result["indiscipline_type"],
                duration_seconds=5.0,
                severity=fusion_result["severity"],
                notes=fusion_result["notes"]
            )

        return {
            "success": True,
            "raw_frame": raw_frame,
            "display_frame": display_frame,
            "cv_result": cv_result,
            "fusion_result": fusion_result,
            "student_id": self.student_id
        }

    def generate_session_report(self, student_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.frame_history:
            return None

        from services.pdf_generator import PDFReportGenerator
        now = datetime.now()
        duration_sec = max(1.0, (now - self.session_start).total_seconds())
        mins, secs = divmod(int(duration_sec), 60)
        dur_str = f"{mins:02d}m {secs:02d}s"

        total_frames = len(self.frame_history)
        avg_focus = sum(f["focus_score"] for f in self.frame_history) / total_frames
        study_frames = sum(1 for f in self.frame_history if "STUDYING" in f["study_state"])
        dist_frames = sum(1 for f in self.frame_history if "DISTRACTED" in f["study_state"] or "DROWSY" in f["study_state"])

        study_pct = (study_frames / total_frames) * 100.0
        dist_pct = (dist_frames / total_frames) * 100.0

        avg_ear = sum(f["ear"] for f in self.frame_history) / total_frames
        avg_mar = sum(f["mar"] for f in self.frame_history) / total_frames
        avg_yaw = sum(f["yaw"] for f in self.frame_history) / total_frames
        avg_pitch = sum(f["pitch"] for f in self.frame_history) / total_frames
        avg_dg = sum(f["dg_score"] for f in self.frame_history) / total_frames
        in_target_pct = (sum(1 for f in self.frame_history if f["in_target"]) / total_frames) * 100.0

        if avg_focus >= 85.0 and len(self.session_incidents) == 0:
            rating = "Exemplary Focus"
        elif avg_focus >= 70.0 and len(self.session_incidents) <= 1:
            rating = "Satisfactory Attention"
        elif avg_focus >= 50.0:
            rating = "Needs Monitoring"
        else:
            rating = "High Indiscipline"

        if student_info is None:
            student_info = self.db.get_student_by_id(self.student_id) or {
                "student_id": self.student_id,
                "name": "Student",
                "grade": "Grade 10-A"
            }

        session_data = {
            "student": student_info,
            "camera_source": "Physical Webcam (Device 0)" if self.camera_source == 0 else "Simulated Classroom Camera",
            "start_time": self.session_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_formatted": dur_str,
            "total_frames": total_frames,
            "avg_focus": round(avg_focus, 1),
            "study_time_pct": round(study_pct, 1),
            "distracted_time_pct": round(dist_pct, 1),
            "indiscipline_count": len(self.session_incidents),
            "overall_evaluation": rating,
            "telemetry_averages": {
                "avg_ear": round(avg_ear, 2),
                "avg_mar": round(avg_mar, 2),
                "avg_yaw": round(avg_yaw, 1),
                "avg_pitch": round(avg_pitch, 1),
                "avg_dg_focus": round(avg_dg, 1),
                "gaze_in_target_pct": round(in_target_pct, 1)
            },
            "incident_log": self.session_incidents
        }

        generator = PDFReportGenerator()
        pdf_path = generator.generate_session_event_report_pdf(session_data)

        return {
            "pdf_path": pdf_path,
            "filename": Path(pdf_path).name,
            "session_data": session_data
        }

    def _render_dashboard_hud(self, frame: np.ndarray, fusion: Dict[str, Any], cv_res: Dict[str, Any]) -> np.ndarray:
        h, w, _ = frame.shape
        out = frame.copy()

        cv2.rectangle(out, (0, 0), (w, 52), (18, 22, 28), -1)
        cv2.line(out, (0, 52), (w, 52), (50, 70, 90), 2)

        cv2.putText(out, "EAGLE'S EYE: AI Camera + DG Attention Monitor", (12, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(out, f"Student: {self.student_id}", (12, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 200, 220), 1, cv2.LINE_AA)

        state = fusion["study_state"]
        focus = fusion["focus_score"]
        if "STUDYING" in state:
            status_color = (0, 220, 100)
            status_text = f"STUDYING ({focus:.0f}%)"
        elif "DISTRACTED" in state:
            status_color = (0, 160, 255)
            status_text = f"DISTRACTED ({focus:.0f}%)"
        elif "DROWSY" in state:
            status_color = (220, 100, 255)
            status_text = f"DROWSY / SLEEPING ({focus:.0f}%)"
        else:
            status_color = (60, 60, 240)
            status_text = f"INDISCIPLINE: {fusion.get('indiscipline_type', 'FLAGGED')[:16]}"

        pill_w = 260
        px1 = (w - pill_w) // 2
        px2 = px1 + pill_w
        cv2.rectangle(out, (px1, 8), (px2, 44), status_color, -1)
        cv2.putText(out, status_text, (px1 + 10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)

        dg = fusion["dg_data"]
        radar_x, radar_y, radar_size = 15, h - 85, 70
        cv2.rectangle(out, (radar_x, radar_y), (radar_x + radar_size, radar_y + radar_size), (20, 25, 30), -1)
        cv2.rectangle(out, (radar_x, radar_y), (radar_x + radar_size, radar_y + radar_size), (80, 100, 120), 1)

        sz_x1 = radar_x + int(radar_size * 0.22)
        sz_y1 = radar_y + int(radar_size * 0.20)
        sz_x2 = radar_x + int(radar_size * 0.78)
        sz_y2 = radar_y + int(radar_size * 0.85)
        cv2.rectangle(out, (sz_x1, sz_y1), (sz_x2, sz_y2), (40, 70, 50), -1)

        gx = radar_x + int(dg["gaze_x"] * radar_size)
        gy = radar_y + int(dg["gaze_y"] * radar_size)
        gaze_color = (0, 255, 120) if dg["study_zone_active"] else (50, 50, 255)
        cv2.circle(out, (gx, gy), 4, gaze_color, -1)
        cv2.putText(out, "DG Gaze Radar", (radar_x, radar_y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 220, 240), 1, cv2.LINE_AA)

        gauge_w, gauge_h = 140, 18
        gx1 = w - gauge_w - 15
        gy1 = h - 35
        cv2.rectangle(out, (gx1, gy1), (gx1 + gauge_w, gy1 + gauge_h), (30, 30, 30), -1)
        fill_w = int((focus / 100.0) * gauge_w)
        cv2.rectangle(out, (gx1, gy1), (gx1 + fill_w, gy1 + gauge_h), status_color, -1)
        cv2.rectangle(out, (gx1, gy1), (gx1 + gauge_w, gy1 + gauge_h), (120, 120, 120), 1)
        cv2.putText(out, f"Focus Index: {focus:.0f}%", (gx1, gy1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (230, 230, 230), 1, cv2.LINE_AA)

        return out

    def release(self):
        self.stream.release()

    def set_simulation_scenario(self, scenario_name: str):
        if hasattr(self.stream, "set_simulation_scenario"):
            self.stream.set_simulation_scenario(scenario_name)
