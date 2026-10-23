import os
import math
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from config import (
    BASE_DIR,
    EAR_SLEEP_THRESHOLD,
    MAR_TALK_THRESHOLD,
    HEAD_POSE_YAW_LIMIT,
    HEAD_POSE_PITCH_UP_LIMIT,
    HEAD_POSE_PITCH_DOWN_LIMIT
)

MODEL_PATH = BASE_DIR / "data" / "models" / "face_landmarker.task"

_GLOBAL_LANDMARKER = None

def get_shared_landmarker():
    global _GLOBAL_LANDMARKER
    if _GLOBAL_LANDMARKER is None and MODEL_PATH.exists():
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=1,
                running_mode=vision.RunningMode.IMAGE
            )
            _GLOBAL_LANDMARKER = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            print(f"[FaceMeshDetector] Shared Landmarker init error: {e}")
            _GLOBAL_LANDMARKER = None
    return _GLOBAL_LANDMARKER

class FaceMeshDetector:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self.landmarker = get_shared_landmarker()
        self.ema_alpha = 0.35
        self.smooth_ear = 0.30
        self.smooth_mar = 0.05
        self.smooth_yaw = 0.0
        self.smooth_pitch = 0.0
        self.smooth_gaze_x = 0.50
        self.smooth_gaze_y = 0.50

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        h, w, c = frame.shape
        annotated_frame = frame.copy()

        result = {
            "face_detected": False,
            "bbox": None,
            "ear": round(self.smooth_ear, 3),
            "mar": round(self.smooth_mar, 3),
            "head_pose": {
                "yaw": round(self.smooth_yaw, 1),
                "pitch": round(self.smooth_pitch, 1),
                "roll": 0.0
            },
            "gaze_angles": {"gaze_yaw": 0.0, "gaze_pitch": 0.0},
            "gaze_coords": (self.smooth_gaze_x, self.smooth_gaze_y),
            "blendshapes": {},
            "facial_expression": "UNKNOWN",
            "annotated_frame": annotated_frame
        }

        if self.landmarker is not None:
            try:
                import mediapipe as mp
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = self.landmarker.detect(mp_image)

                if detection_result.face_landmarks and len(detection_result.face_landmarks) > 0:
                    landmarks = detection_result.face_landmarks[0]
                    result["face_detected"] = True

                    xs = [lm.x * w for lm in landmarks]
                    ys = [lm.y * h for lm in landmarks]
                    min_x, max_x = max(0, int(min(xs))), min(w, int(max(xs)))
                    min_y, max_y = max(0, int(min(ys))), min(h, int(max(ys)))
                    bw = max_x - min_x
                    bh = max_y - min_y
                    result["bbox"] = (min_x, min_y, bw, bh)

                    blendshape_dict = {}
                    if detection_result.face_blendshapes and len(detection_result.face_blendshapes) > 0:
                        for category in detection_result.face_blendshapes[0]:
                            blendshape_dict[category.category_name] = category.score
                    result["blendshapes"] = blendshape_dict

                    blink_l = blendshape_dict.get("eyeBlinkLeft", 0.0)
                    blink_r = blendshape_dict.get("eyeBlinkRight", 0.0)
                    avg_blink = (blink_l + blink_r) / 2.0
                    raw_ear = max(0.0, (1.0 - avg_blink) * 0.35)
                    self.smooth_ear = (1 - self.ema_alpha) * self.smooth_ear + self.ema_alpha * raw_ear
                    result["ear"] = round(self.smooth_ear, 3)

                    jaw_open = blendshape_dict.get("jawOpen", 0.0)
                    mouth_pucker = blendshape_dict.get("mouthPucker", 0.0)
                    mouth_funnel = blendshape_dict.get("mouthFunnel", 0.0)
                    raw_mar = jaw_open + 0.25 * mouth_pucker + 0.15 * mouth_funnel
                    self.smooth_mar = (1 - self.ema_alpha) * self.smooth_mar + self.ema_alpha * raw_mar
                    result["mar"] = round(self.smooth_mar, 3)

                    raw_yaw, raw_pitch, raw_roll = 0.0, 0.0, 0.0
                    if detection_result.facial_transformation_matrixes and len(detection_result.facial_transformation_matrixes) > 0:
                        mat = np.array(detection_result.facial_transformation_matrixes[0])
                        R = mat[:3, :3]
                        raw_pitch = math.atan2(R[2, 1], R[2, 2]) * 180.0 / math.pi
                        raw_yaw = math.atan2(-R[2, 0], math.sqrt(R[2, 1]**2 + R[2, 2]**2)) * 180.0 / math.pi
                        raw_roll = math.atan2(R[1, 0], R[0, 0]) * 180.0 / math.pi
                    else:
                        raw_yaw, raw_pitch, raw_roll = self._estimate_head_pose_pnp(landmarks, w, h)

                    self.smooth_yaw = (1 - self.ema_alpha) * self.smooth_yaw + self.ema_alpha * raw_yaw
                    self.smooth_pitch = (1 - self.ema_alpha) * self.smooth_pitch + self.ema_alpha * raw_pitch

                    result["head_pose"] = {
                        "yaw": round(self.smooth_yaw, 1),
                        "pitch": round(self.smooth_pitch, 1),
                        "roll": round(raw_roll, 1)
                    }

                    look_down_l = blendshape_dict.get("eyeLookDownLeft", 0.0)
                    look_down_r = blendshape_dict.get("eyeLookDownRight", 0.0)
                    look_up_l = blendshape_dict.get("eyeLookUpLeft", 0.0)
                    look_up_r = blendshape_dict.get("eyeLookUpRight", 0.0)
                    look_in_l = blendshape_dict.get("eyeLookInLeft", 0.0)
                    look_out_l = blendshape_dict.get("eyeLookOutLeft", 0.0)
                    look_in_r = blendshape_dict.get("eyeLookInRight", 0.0)
                    look_out_r = blendshape_dict.get("eyeLookOutRight", 0.0)

                    gaze_yaw = ((look_out_l - look_in_l) + (look_in_r - look_out_r)) * 25.0
                    gaze_pitch = (((look_up_l + look_up_r) / 2.0) - ((look_down_l + look_down_r) / 2.0)) * 25.0
                    result["gaze_angles"] = {"gaze_yaw": round(gaze_yaw, 1), "gaze_pitch": round(gaze_pitch, 1)}

                    total_yaw = self.smooth_yaw + gaze_yaw
                    total_pitch = self.smooth_pitch + gaze_pitch
                    raw_gx = max(0.0, min(1.0, 0.5 + (total_yaw / 60.0)))
                    raw_gy = max(0.0, min(1.0, 0.5 - (total_pitch / 45.0)))

                    self.smooth_gaze_x = (1 - self.ema_alpha) * self.smooth_gaze_x + self.ema_alpha * raw_gx
                    self.smooth_gaze_y = (1 - self.ema_alpha) * self.smooth_gaze_y + self.ema_alpha * raw_gy
                    result["gaze_coords"] = (round(self.smooth_gaze_x, 3), round(self.smooth_gaze_y, 3))

                    result["facial_expression"] = self._classify_expression(
                        ear=result["ear"],
                        mar=result["mar"],
                        yaw=self.smooth_yaw,
                        pitch=self.smooth_pitch,
                        blendshapes=blendshape_dict
                    )

                    self._render_overlay(annotated_frame, result, landmarks, w, h)
                    result["annotated_frame"] = annotated_frame
                    return result

            except Exception as e:
                print(f"[FaceMeshDetector] Detection exception: {e}")

        result = self._geometric_detector_fallback(frame, result)
        return result

    def process_synthetic_telemetry(self, frame: np.ndarray, telem: Dict[str, Any]) -> Dict[str, Any]:
        h, w, c = frame.shape
        annotated = frame.copy()

        if telem.get("is_absent", False):
            return {
                "face_detected": False,
                "bbox": None,
                "ear": 0.0,
                "mar": 0.0,
                "head_pose": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
                "gaze_angles": {"gaze_yaw": 0.0, "gaze_pitch": 0.0},
                "gaze_coords": (0.0, 0.0),
                "blendshapes": {},
                "facial_expression": "UNKNOWN",
                "annotated_frame": annotated
            }

        cx, cy = telem["cx"], telem["cy"]
        bx, by, bw, bh = cx - 65, cy - 80, 130, 160
        bx = max(0, min(w - bw, bx))
        by = max(0, min(h - bh, by))

        yaw = telem["yaw"]
        pitch = telem["pitch"]
        roll = telem["roll"]
        ear = telem["ear"]
        mar = telem["mar"]
        gx = telem["gaze_x"]
        gy = telem["gaze_y"]
        expr = telem["expression"]

        self.smooth_ear = ear
        self.smooth_mar = mar
        self.smooth_yaw = yaw
        self.smooth_pitch = pitch
        self.smooth_gaze_x = gx
        self.smooth_gaze_y = gy

        result = {
            "face_detected": True,
            "bbox": (bx, by, bw, bh),
            "ear": ear,
            "mar": mar,
            "head_pose": {"yaw": yaw, "pitch": pitch, "roll": roll},
            "gaze_angles": {"gaze_yaw": yaw * 0.4, "gaze_pitch": pitch * 0.4},
            "gaze_coords": (gx, gy),
            "blendshapes": {},
            "facial_expression": expr,
            "annotated_frame": annotated
        }

        color = (0, 220, 100) if "FOCUSED" in expr else ((255, 180, 0) if "CONFUSED" in expr else ((0, 165, 255) if "DISTRACTED" in expr else ((200, 100, 255) if "DROWSY" in expr else (60, 60, 240))))
        cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), color, 2)

        cv2.circle(annotated, (cx - 22, cy - 10), 3, (0, 255, 255), -1)
        cv2.circle(annotated, (cx + 22, cy - 10), 3, (0, 255, 255), -1)
        cv2.circle(annotated, (cx, cy + 18), 3, (0, 255, 255), -1)
        cv2.circle(annotated, (cx, cy + 42), 3, (0, 255, 255), -1)

        label = f"{expr} (EAR:{ear:.2f} MAR:{mar:.2f})"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(annotated, (bx, max(0, by - 24)), (bx + tw + 10, by), color, -1)
        cv2.putText(annotated, label, (bx + 5, by - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.rectangle(annotated, (w - 180, 10), (w - 10, 50), (20, 20, 20), -1)
        cv2.putText(annotated, f"Pose: Y:{yaw:+.1f} P:{pitch:+.1f}", (w - 170, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 240, 240), 1, cv2.LINE_AA)

        result["annotated_frame"] = annotated
        return result

    def _estimate_head_pose_pnp(self, landmarks, w: int, h: int) -> Tuple[float, float, float]:
        try:
            image_points = np.array([
                (landmarks[1].x * w, landmarks[1].y * h),
                (landmarks[152].x * w, landmarks[152].y * h),
                (landmarks[33].x * w, landmarks[33].y * h),
                (landmarks[263].x * w, landmarks[263].y * h),
                (landmarks[61].x * w, landmarks[61].y * h),
                (landmarks[291].x * w, landmarks[291].y * h)
            ], dtype="double")

            model_points = np.array([
                (0.0, 0.0, 0.0),
                (0.0, -330.0, -65.0),
                (-225.0, 170.0, -135.0),
                (225.0, 170.0, -135.0),
                (-150.0, -150.0, -125.0),
                (150.0, -150.0, -125.0)
            ])

            focal_length = w
            center = (w / 2, h / 2)
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype="double")
            dist_coeffs = np.zeros((4, 1))

            success, rotation_vector, translation_vector = cv2.solvePnP(
                model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
            )

            if success:
                rot_matrix, _ = cv2.Rodrigues(rotation_vector)
                proj_matrix = np.hstack((rot_matrix, translation_vector))
                _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)
                pitch, yaw, roll = euler_angles[0][0], euler_angles[1][0], euler_angles[2][0]
                return yaw, pitch, roll
        except Exception:
            pass
        return 0.0, 0.0, 0.0

    def _classify_expression(self, ear: float, mar: float, yaw: float, pitch: float,
                             blendshapes: Dict[str, float]) -> str:
        if ear < EAR_SLEEP_THRESHOLD or blendshapes.get("eyeBlinkLeft", 0) > 0.75:
            return "DROWSY_SLEEPING"

        if mar > MAR_TALK_THRESHOLD or blendshapes.get("jawOpen", 0) > 0.42:
            return "TALKING_INDISCIPLINE"

        if abs(yaw) > HEAD_POSE_YAW_LIMIT or pitch > HEAD_POSE_PITCH_UP_LIMIT or pitch < HEAD_POSE_PITCH_DOWN_LIMIT:
            return "DISTRACTED_LOOKING_AWAY"

        brow_down = (blendshapes.get("browDownLeft", 0) + blendshapes.get("browDownRight", 0)) / 2.0
        if brow_down > 0.38:
            return "CONFUSED_CONTEMPLATING"

        look_down = (blendshapes.get("eyeLookDownLeft", 0) + blendshapes.get("eyeLookDownRight", 0)) / 2.0
        if look_down > 0.22 or pitch < -8.0:
            return "FOCUSED_READING"

        return "FOCUSED_ATTENTIVE"

    def _geometric_detector_fallback(self, frame: np.ndarray, result: Dict[str, Any]) -> Dict[str, Any]:
        h, w, c = frame.shape
        annotated = frame.copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_cnt = None
        max_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 3000 < area < (w * h * 0.7):
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = float(ch) / cw if cw > 0 else 0
                if 0.8 < aspect_ratio < 2.0 and y > 50 and y + ch < h - 40:
                    if area > max_area:
                        max_area = area
                        best_cnt = cnt

        if best_cnt is not None:
            x, y, bw, bh = cv2.boundingRect(best_cnt)
            result["face_detected"] = True
            result["bbox"] = (x, y, bw, bh)

            face_cx = x + bw // 2
            face_cy = y + bh // 2
            dx = face_cx - (w // 2)
            dy = face_cy - (h // 2 + 20)

            raw_yaw = (dx / (w * 0.5)) * 45.0
            raw_pitch = -(dy / (h * 0.5)) * 35.0
            self.smooth_yaw = (1 - self.ema_alpha) * self.smooth_yaw + self.ema_alpha * raw_yaw
            self.smooth_pitch = (1 - self.ema_alpha) * self.smooth_pitch + self.ema_alpha * raw_pitch

            result["head_pose"] = {"yaw": round(self.smooth_yaw, 1), "pitch": round(self.smooth_pitch, 1), "roll": 0.0}

            face_roi = gray[y:y+bh, x:x+bw]
            if face_roi.size > 0:
                top_half = face_roi[:bh//2, :]
                bottom_half = face_roi[bh//2:, :]

                eye_variance = float(np.std(top_half))
                ear = 0.28 if eye_variance > 18 else 0.12
                self.smooth_ear = (1 - self.ema_alpha) * self.smooth_ear + self.ema_alpha * ear
                result["ear"] = round(self.smooth_ear, 3)

                _, mouth_bin = cv2.threshold(bottom_half, 80, 255, cv2.THRESH_BINARY_INV)
                mouth_pixels = np.count_nonzero(mouth_bin)
                raw_mar = min(1.0, mouth_pixels / (bh * bw * 0.08))
                self.smooth_mar = (1 - self.ema_alpha) * self.smooth_mar + self.ema_alpha * raw_mar
                result["mar"] = round(self.smooth_mar, 3)

                total_yaw = self.smooth_yaw
                total_pitch = self.smooth_pitch
                raw_gx = max(0.0, min(1.0, 0.5 + (total_yaw / 60.0)))
                raw_gy = max(0.0, min(1.0, 0.5 - (total_pitch / 45.0)))
                self.smooth_gaze_x = (1 - self.ema_alpha) * self.smooth_gaze_x + self.ema_alpha * raw_gx
                self.smooth_gaze_y = (1 - self.ema_alpha) * self.smooth_gaze_y + self.ema_alpha * raw_gy
                result["gaze_coords"] = (round(self.smooth_gaze_x, 3), round(self.smooth_gaze_y, 3))

                if self.smooth_ear < 0.18:
                    expr = "DROWSY_SLEEPING"
                elif self.smooth_mar > 0.38:
                    expr = "TALKING_INDISCIPLINE"
                elif abs(self.smooth_yaw) > 22.0:
                    expr = "DISTRACTED_LOOKING_AWAY"
                elif self.smooth_pitch < -16.0:
                    expr = "DISTRACTED_LOOKING_AWAY"
                elif self.smooth_pitch > 10.0:
                    expr = "CONFUSED_CONTEMPLATING"
                else:
                    expr = "FOCUSED_ATTENTIVE"
                result["facial_expression"] = expr

            cv2.rectangle(annotated, (x, y), (x + bw, y + bh), (0, 220, 100), 2)
            cv2.putText(annotated, f"Face: {result['facial_expression']}", (x, max(20, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 100), 2)

        result["annotated_frame"] = annotated
        return result

    def _render_overlay(self, frame: np.ndarray, result: Dict[str, Any], landmarks, w: int, h: int):
        bx, by, bw, bh = result["bbox"]
        expr = result["facial_expression"]

        if "FOCUSED" in expr:
            color = (0, 220, 100)
        elif "CONFUSED" in expr:
            color = (255, 180, 0)
        elif "DISTRACTED" in expr:
            color = (0, 165, 255)
        elif "DROWSY" in expr:
            color = (200, 100, 255)
        else:
            color = (60, 60, 240)

        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, 2)

        key_indices = [1, 33, 133, 362, 263, 61, 291, 199, 152]
        for idx in key_indices:
            if idx < len(landmarks):
                lx = int(landmarks[idx].x * w)
                ly = int(landmarks[idx].y * h)
                cv2.circle(frame, (lx, ly), 3, (0, 255, 255), -1)

        label = f"{expr} (EAR:{result['ear']:.2f} MAR:{result['mar']:.2f})"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(frame, (bx, max(0, by - 24)), (bx + tw + 10, by), color, -1)
        cv2.putText(frame, label, (bx + 5, by - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        yaw = result["head_pose"]["yaw"]
        pitch = result["head_pose"]["pitch"]
        cv2.rectangle(frame, (w - 180, 10), (w - 10, 50), (20, 20, 20), -1)
        cv2.putText(frame, f"Pose: Y:{yaw:+.1f} P:{pitch:+.1f}", (w - 170, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 240, 240), 1, cv2.LINE_AA)
