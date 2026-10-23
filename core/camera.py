import cv2
import time
import math
import threading
import numpy as np
from typing import Optional, Tuple

class VideoStreamHandler:
    def __init__(self, source=0, width: int = 640, height: int = 480):
        self.source = source
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_synthetic = False
        self.synthetic_frame_count = 0
        self.start_time = time.time()
        self.scenario = "auto"
        
        self.latest_frame: Optional[np.ndarray] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        self._init_source()

    def set_simulation_scenario(self, scenario_name: str):
        self.scenario = scenario_name.lower().strip()

    def _init_source(self):
        if isinstance(self.source, str) and self.source.lower() == "synthetic":
            self.is_synthetic = True
            return

        try:
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                self.is_synthetic = True
            else:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.is_synthetic = True
                    self.cap.release()
                    self.cap = None
                else:
                    self.is_running = True
                    self.latest_frame = frame
                    self.thread = threading.Thread(target=self._capture_worker, daemon=True)
                    self.thread.start()
        except Exception:
            self.is_synthetic = True

    def _capture_worker(self):
        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.01)
            time.sleep(0.01)

    def read_frame(self) -> Tuple[bool, np.ndarray]:
        if not self.is_synthetic and self.cap and self.cap.isOpened():
            for _ in range(10):
                with self.lock:
                    if self.latest_frame is not None:
                        return True, self.latest_frame.copy()
                time.sleep(0.01)

        frame = self._generate_synthetic_student_frame()
        return True, frame

    def _generate_synthetic_student_frame(self) -> np.ndarray:
        self.synthetic_frame_count += 1
        t = time.time() - self.start_time

        mode = self.scenario
        if mode == "auto":
            cycle_time = t % 49.0
            if cycle_time < 8.0:
                mode = "focused"
            elif cycle_time < 15.0:
                mode = "thinking"
            elif cycle_time < 22.0:
                mode = "talking"
            elif cycle_time < 30.0:
                mode = "swinging"
            elif cycle_time < 37.0:
                mode = "drowsy"
            elif cycle_time < 44.0:
                mode = "phone"
            else:
                mode = "absent"

        img = np.full((self.height, self.width, 3), (238, 240, 244), dtype=np.uint8)

        cv2.rectangle(img, (30, 20), (self.width - 30, 145), (40, 60, 42), -1)
        cv2.rectangle(img, (26, 16), (self.width - 26, 149), (90, 60, 40), 4)
        cv2.putText(img, "Eagle's Eye AI - Math & Physics Lecture Series", (50, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 245, 220), 1, cv2.LINE_AA)
        cv2.putText(img, "Kinematics: v = u + at | Energy: E = mc^2 | d/dx[cos x] = -sin x", (50, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 215, 180), 1, cv2.LINE_AA)

        clock_cx, clock_cy = self.width - 70, 75
        cv2.circle(img, (clock_cx, clock_cy), 22, (255, 255, 255), -1)
        cv2.circle(img, (clock_cx, clock_cy), 22, (100, 100, 100), 2)
        cv2.line(img, (clock_cx, clock_cy), (clock_cx + 10, clock_cy - 10), (40, 40, 40), 2)
        cv2.line(img, (clock_cx, clock_cy), (clock_cx, clock_cy + 12), (200, 50, 50), 1)

        cv2.rectangle(img, (0, 365), (self.width, self.height), (150, 120, 85), -1)
        cv2.line(img, (0, 365), (self.width, 365), (110, 85, 55), 3)

        cv2.rectangle(img, (180, 385), (460, 470), (250, 250, 252), -1)
        cv2.rectangle(img, (178, 383), (462, 472), (60, 65, 75), 2)
        for line_y in range(400, 465, 12):
            cv2.line(img, (190, line_y), (450, line_y), (210, 225, 240), 1)
        cv2.putText(img, "[ Calculus Notes & Active LMS Workspace ]", (205, 425),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 100, 120), 1, cv2.LINE_AA)

        chair_cx = 320
        cv2.rectangle(img, (chair_cx - 60, 220), (chair_cx + 60, 340), (130, 140, 155), -1)
        cv2.rectangle(img, (chair_cx - 60, 220), (chair_cx + 60, 340), (80, 90, 105), 2)

        base_cx, base_cy = 320, 260
        dx, dy = 0, 0
        eye_open = 1.0
        mouth_open = 0.0
        gaze_offset_x = 0
        gaze_offset_y = 0
        tilt_angle = 0.0
        state_badge = ""
        speech_bubble = None
        show_phone = False
        is_absent = False

        if mode == "focused":
            state_badge = "1. FOCUSED STUDY (Reading notes, high attention)"
            dx = int(math.sin(self.synthetic_frame_count * 0.06) * 2)
            dy = int(math.cos(self.synthetic_frame_count * 0.04) * 2)
            eye_open = 0.88 + 0.08 * math.sin(self.synthetic_frame_count * 0.1)
            mouth_open = 0.02
            gaze_offset_y = 4

        elif mode == "thinking":
            state_badge = "2. PROBLEM SOLVING (Thinking, brow furrowed)"
            dx = int(math.sin(self.synthetic_frame_count * 0.03) * 4)
            dy = -8
            eye_open = 0.92
            mouth_open = 0.04
            tilt_angle = 6.0
            gaze_offset_x = 4
            gaze_offset_y = -5

        elif mode == "talking":
            state_badge = "3. TALKING / CHATTING (Turned to peer, active mouth)"
            dx = -55 + int(math.sin(self.synthetic_frame_count * 0.12) * 4)
            dy = -4
            tilt_angle = -5.0
            eye_open = 0.90
            mouth_open = 0.48 + 0.35 * abs(math.sin(self.synthetic_frame_count * 0.40))
            gaze_offset_x = -8
            speech_bubble = "Psst... what's #3?"

        elif mode == "swinging":
            state_badge = "4. RESTLESS SWINGING (Head & body swinging back/forth)"
            swing_phase = math.sin(self.synthetic_frame_count * 0.14)
            dx = int(swing_phase * 52)
            dy = -int(abs(swing_phase) * 6)
            tilt_angle = swing_phase * 15.0
            eye_open = 0.95
            mouth_open = 0.08
            gaze_offset_x = int(swing_phase * 10)

        elif mode == "drowsy":
            state_badge = "5. DROWSY / SLEEPING (Head drooping on desk, eyes shut)"
            dx = int(math.sin(self.synthetic_frame_count * 0.02) * 3)
            dy = 28 + int(math.sin(self.synthetic_frame_count * 0.03) * 4)
            tilt_angle = 10.0
            eye_open = 0.0
            mouth_open = 0.18
            gaze_offset_y = 6

        elif mode == "phone":
            state_badge = "6. CONCEALED PHONE (Head pitched down at lap)"
            dx = int(math.sin(self.synthetic_frame_count * 0.04) * 3)
            dy = 38
            eye_open = 0.85
            mouth_open = 0.02
            gaze_offset_y = 12
            show_phone = True

        elif mode == "absent":
            state_badge = "7. STUDENT ABSENT (Left seat during study session)"
            is_absent = True

        synth_yaw = round((dx / 55.0) * 38.0, 1)
        synth_pitch = round(-(dy / 45.0) * 32.0, 1)
        synth_roll = round(tilt_angle, 1)
        synth_ear = round(max(0.04, min(0.35, 0.32 * eye_open)), 3)
        synth_mar = round(max(0.02, min(0.95, mouth_open)), 3)
        synth_gx = round(max(0.05, min(0.95, 0.50 + (dx / 110.0) + (gaze_offset_x / 25.0))), 3)
        synth_gy = round(max(0.05, min(0.95, 0.52 - (dy / 85.0) + (gaze_offset_y / 25.0))), 3)

        if is_absent:
            synth_expr = "UNKNOWN"
        elif mode == "drowsy":
            synth_expr = "DROWSY_SLEEPING"
        elif mode == "talking":
            synth_expr = "TALKING_INDISCIPLINE"
        elif mode == "swinging" or mode == "phone":
            synth_expr = "DISTRACTED_LOOKING_AWAY"
        elif mode == "thinking":
            synth_expr = "CONFUSED_CONTEMPLATING"
        else:
            synth_expr = "FOCUSED_ATTENTIVE"

        self.last_synthetic_telemetry = {
            "mode": mode,
            "is_absent": is_absent,
            "cx": base_cx + dx,
            "cy": base_cy + dy,
            "yaw": synth_yaw,
            "pitch": synth_pitch,
            "roll": synth_roll,
            "ear": synth_ear,
            "mar": synth_mar,
            "gaze_x": synth_gx,
            "gaze_y": synth_gy,
            "expression": synth_expr
        }

        if is_absent:
            cv2.rectangle(img, (220, 270), (420, 320), (220, 50, 50), 2)
            cv2.putText(img, "SEAT VACANT / ABSENT", (230, 302),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 30, 30), 2, cv2.LINE_AA)
        else:
            cx = base_cx + dx
            cy = base_cy + dy

            body_cx = cx
            body_cy = cy + 130
            cv2.ellipse(img, (body_cx, body_cy), (115, 75), int(tilt_angle * 0.5), 0, 360, (50, 75, 130), -1)
            cv2.line(img, (cx - 30, cy + 65), (cx, cy + 90), (240, 240, 245), 4)
            cv2.line(img, (cx + 30, cy + 65), (cx, cy + 90), (240, 240, 245), 4)

            cv2.ellipse(img, (cx, cy), (65, 80), int(tilt_angle), 0, 360, (190, 215, 235), -1)
            cv2.ellipse(img, (cx, cy), (65, 80), int(tilt_angle), 0, 360, (140, 160, 180), 2)

            cv2.ellipse(img, (cx, cy - 38), (66, 45), int(tilt_angle), 180, 360, (30, 30, 40), -1)

            lex, ley = cx - 22, cy - 10
            rex, rey = cx + 22, cy - 10
            cv2.rectangle(img, (lex - 14, ley - 10), (lex + 14, ley + 10), (50, 50, 60), 2)
            cv2.rectangle(img, (rex - 14, rey - 10), (rex + 14, rey + 10), (50, 50, 60), 2)
            cv2.line(img, (lex + 14, ley), (rex - 14, rey), (50, 50, 60), 2)

            if eye_open > 0.3:
                cv2.ellipse(img, (lex, ley), (10, int(7 * eye_open)), int(tilt_angle), 0, 360, (255, 255, 255), -1)
                cv2.ellipse(img, (rex, rey), (10, int(7 * eye_open)), int(tilt_angle), 0, 360, (255, 255, 255), -1)
                px = int(gaze_offset_x + dx * 0.05)
                py = int(gaze_offset_y)
                cv2.circle(img, (lex + px, ley + py), 4, (40, 30, 20), -1)
                cv2.circle(img, (rex + px, rey + py), 4, (40, 30, 20), -1)
            else:
                cv2.line(img, (lex - 10, ley), (lex + 10, ley), (40, 30, 20), 2)
                cv2.line(img, (rex - 10, rey), (rex + 10, rey), (40, 30, 20), 2)

            if mode == "thinking":
                cv2.line(img, (lex - 10, ley - 13), (lex + 12, ley - 8), (30, 30, 30), 2)
                cv2.line(img, (rex - 12, ley - 8), (rex + 10, ley - 13), (30, 30, 30), 2)
            else:
                cv2.line(img, (lex - 12, ley - 12), (lex + 10, ley - 11), (30, 30, 30), 2)
                cv2.line(img, (rex - 10, rey - 11), (rex + 12, rey - 12), (30, 30, 30), 2)

            cv2.line(img, (cx, cy), (cx - 2, cy + 18), (140, 160, 180), 2)
            cv2.line(img, (cx - 2, cy + 18), (cx + 5, cy + 18), (140, 160, 180), 2)

            my = cy + 42
            mouth_h = max(2, int(18 * mouth_open))
            cv2.ellipse(img, (cx, my), (16, mouth_h), int(tilt_angle), 0, 360, (80, 50, 160), -1)

            if speech_bubble:
                cv2.rectangle(img, (cx - 150, cy - 90), (cx - 30, cy - 50), (255, 255, 255), -1)
                cv2.rectangle(img, (cx - 150, cy - 90), (cx - 30, cy - 50), (60, 60, 60), 1)
                cv2.putText(img, speech_bubble, (cx - 142, cy - 66),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (20, 20, 20), 1, cv2.LINE_AA)
                cv2.ellipse(img, (cx - 25, cy + 42), (12, 16), 0, -45, 45, (220, 60, 60), 2)
                cv2.ellipse(img, (cx - 32, cy + 42), (18, 22), 0, -45, 45, (220, 60, 60), 2)

            if mode == "drowsy":
                z_offset = (self.synthetic_frame_count % 30)
                cv2.putText(img, "Z", (cx + 35, cy - 20 - z_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 80, 200), 2, cv2.LINE_AA)
                cv2.putText(img, "z", (cx + 50, cy - 35 - z_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 100, 220), 2, cv2.LINE_AA)
                cv2.putText(img, "z", (cx + 60, cy - 50 - z_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 120, 240), 1, cv2.LINE_AA)

            if show_phone:
                phone_x, phone_y = cx - 15, 395
                cv2.rectangle(img, (phone_x, phone_y), (phone_x + 35, phone_y + 55), (20, 20, 25), -1)
                cv2.rectangle(img, (phone_x + 2, phone_y + 2), (phone_x + 33, phone_y + 53), (60, 180, 255), -1)
                cv2.putText(img, "CHAT", (phone_x + 5, phone_y + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.rectangle(img, (10, 10), (450, 42), (15, 20, 25), -1)
        cv2.line(img, (10, 42), (450, 42), (0, 220, 180), 2)
        cv2.putText(img, f"SIMULATION: {state_badge[:38]}", (16, 31),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 220), 1, cv2.LINE_AA)

        return img

    def release(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.3)
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
