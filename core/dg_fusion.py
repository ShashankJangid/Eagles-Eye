import time
import math
from typing import Dict, Any, Optional

from config import (
    WEIGHT_CV_EXPRESSION,
    WEIGHT_DG_GAZE,
    WEIGHT_HEAD_POSE,
    STUDY_FOCUS_THRESHOLD,
    DISTRACTION_SCORE_THRESHOLD
)

class DGFusionEngine:
    def __init__(self):
        self.last_dg_packet: Optional[Dict[str, Any]] = None
        self.consecutive_distraction_frames = 0
        self.consecutive_drowsy_frames = 0
        self.consecutive_talking_frames = 0
        self.consecutive_phone_frames = 0
        self.smooth_focus_score = 85.0
        self.ema_alpha = 0.20

    def generate_simulated_dg_packet(self, cv_result: Dict[str, Any]) -> Dict[str, Any]:
        face_detected = cv_result["face_detected"]
        ear = cv_result["ear"]
        mar = cv_result["mar"]
        head_yaw = cv_result["head_pose"]["yaw"]

        if not face_detected:
            return {
                "timestamp": time.time(),
                "gaze_x": 0.0,
                "gaze_y": 0.0,
                "study_zone_active": False,
                "fixation_duration_ms": 0,
                "gesture_state": "STUDENT_ABSENT",
                "dg_focus_score": 0.0
            }

        gx, gy = cv_result.get("gaze_coords", (0.5, 0.5))
        study_zone_active = (0.20 <= gx <= 0.80) and (0.20 <= gy <= 0.88) and (ear >= 0.18)

        dist_from_center = math.sqrt((gx - 0.50)**2 + (gy - 0.55)**2)
        target_score = max(0.0, 100.0 - (dist_from_center * 140.0))

        if ear < 0.18:
            gesture_state = "IDLE_DROWSY"
            fixation_ms = 0
            dg_score = 10.0
        elif mar > 0.46:
            gesture_state = "VERBAL_INTERACTION"
            fixation_ms = 120
            dg_score = 25.0
        elif abs(head_yaw) > 24.0 or not study_zone_active:
            gesture_state = "OFF_SCREEN_WANDERING"
            fixation_ms = 250
            dg_score = 30.0
        else:
            gesture_state = "ACTIVE_STUDY_READING"
            fixation_ms = 1600
            dg_score = max(75.0, target_score)

        return {
            "timestamp": time.time(),
            "gaze_x": round(gx, 3),
            "gaze_y": round(gy, 3),
            "study_zone_active": study_zone_active,
            "fixation_duration_ms": fixation_ms,
            "gesture_state": gesture_state,
            "dg_focus_score": round(max(0.0, min(100.0, dg_score)), 1)
        }

    def fuse(self, cv_result: Dict[str, Any], external_dg_packet: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        dg = external_dg_packet if external_dg_packet is not None else self.generate_simulated_dg_packet(cv_result)
        self.last_dg_packet = dg

        face_detected = cv_result["face_detected"]
        ear = cv_result["ear"]
        mar = cv_result["mar"]
        head_yaw = cv_result["head_pose"]["yaw"]
        head_pitch = cv_result["head_pose"]["pitch"]
        expr = cv_result["facial_expression"]

        if not face_detected:
            self.smooth_focus_score = 0.0
            return {
                "study_state": "INDISCIPLINE_ABSENT",
                "focus_score": 0.0,
                "is_studying": False,
                "indiscipline_flag": True,
                "indiscipline_type": "ABSENCE_FROM_SEAT",
                "severity": "HIGH",
                "notes": "Student not detected in camera frame during study session.",
                "dg_data": dg
            }

        cv_score = 75.0
        if "FOCUSED" in expr:
            cv_score = 95.0
        elif "CONFUSED" in expr:
            cv_score = 72.0
        elif "DISTRACTED" in expr:
            cv_score = 30.0
        elif "DROWSY" in expr:
            cv_score = 15.0
        elif "TALKING" in expr:
            cv_score = 20.0

        dg_score = dg.get("dg_focus_score", 50.0)

        yaw_penalty = min(50.0, (abs(head_yaw) / 45.0) * 50.0)
        pitch_penalty = min(50.0, (abs(head_pitch) / 35.0) * 50.0)
        pose_score = max(0.0, 100.0 - (yaw_penalty + pitch_penalty))

        raw_fused_focus = (
            WEIGHT_CV_EXPRESSION * cv_score +
            WEIGHT_DG_GAZE * dg_score +
            WEIGHT_HEAD_POSE * pose_score
        )

        self.smooth_focus_score = (1 - self.ema_alpha) * self.smooth_focus_score + self.ema_alpha * raw_fused_focus
        fused_focus = round(max(0.0, min(100.0, self.smooth_focus_score)), 1)

        study_state = "STUDYING_FOCUSED"
        indiscipline_flag = False
        indiscipline_type = None
        severity = "LOW"
        notes = ""

        if ear < 0.18:
            self.consecutive_drowsy_frames += 1
            if self.consecutive_drowsy_frames > 15:
                fused_focus = min(fused_focus, 18.0)
                study_state = "DROWSY_SLEEPING"
                indiscipline_flag = True
                indiscipline_type = "SLEEPING_IN_CLASS"
                severity = "MEDIUM"
                notes = "Prolonged eye closure and head drooping detected."
            else:
                study_state = "STUDYING_PASSIVE"
        else:
            self.consecutive_drowsy_frames = max(0, self.consecutive_drowsy_frames - 2)

        if mar > 0.40 and (abs(head_yaw) > 14.0 or dg["gesture_state"] == "VERBAL_INTERACTION"):
            self.consecutive_talking_frames += 1
            if self.consecutive_talking_frames > 12:
                fused_focus = min(fused_focus, 22.0)
                study_state = "INDISCIPLINE_TALKING"
                indiscipline_flag = True
                indiscipline_type = "TALKING_DISRUPTION"
                severity = "HIGH"
                notes = "Active talking to peer detected during study hours."
            else:
                study_state = "DISTRACTED"
        else:
            self.consecutive_talking_frames = max(0, self.consecutive_talking_frames - 1)

        if not indiscipline_flag and study_state not in ("DROWSY_SLEEPING", "INDISCIPLINE_TALKING"):
            if abs(head_yaw) > 24.0 or not dg["study_zone_active"]:
                self.consecutive_distraction_frames += 1
                if self.consecutive_distraction_frames > 20:
                    study_state = "DISTRACTED_OFFTASK"
                    if self.consecutive_distraction_frames > 60:
                        indiscipline_flag = True
                        indiscipline_type = "PROLONGED_DISTRACTION"
                        severity = "MEDIUM"
                        notes = "Head and gaze turned away from learning area for extended duration."
                else:
                    study_state = "DISTRACTED"
            else:
                self.consecutive_distraction_frames = max(0, self.consecutive_distraction_frames - 2)

        if not indiscipline_flag and (head_pitch < -20.0 or dg.get("gesture_state") == "UNAUTHORIZED_DEVICE"):
            self.consecutive_phone_frames += 1
            if self.consecutive_phone_frames > 12:
                fused_focus = min(fused_focus, 28.0)
                study_state = "INDISCIPLINE_PHONE"
                indiscipline_flag = True
                indiscipline_type = "PHONE_DISTRACTION"
                severity = "HIGH"
                notes = "Head tilted steeply downward toward lap; mobile phone usage suspected."
        else:
            self.consecutive_phone_frames = max(0, self.consecutive_phone_frames - 1)

        if not indiscipline_flag and self.consecutive_drowsy_frames <= 10 and self.consecutive_distraction_frames <= 10 and self.consecutive_talking_frames <= 10:
            if fused_focus >= STUDY_FOCUS_THRESHOLD:
                study_state = "STUDYING_FOCUSED"
            elif fused_focus >= DISTRACTION_SCORE_THRESHOLD:
                study_state = "STUDYING_PASSIVE"
            else:
                study_state = "DISTRACTED"

        is_studying = ("STUDYING" in study_state)

        return {
            "study_state": study_state,
            "focus_score": fused_focus,
            "is_studying": is_studying,
            "indiscipline_flag": indiscipline_flag,
            "indiscipline_type": indiscipline_type,
            "severity": severity,
            "notes": notes,
            "dg_data": dg
        }
