import numpy as np
import pytest
from core.camera import VideoStreamHandler
from core.face_mesh_detector import FaceMeshDetector
from core.dg_fusion import DGFusionEngine
from core.study_detector import StudyDetectorPipeline

def test_synthetic_camera_stream():
    stream = VideoStreamHandler(source="synthetic")
    ret, frame = stream.read_frame()
    assert ret is True
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    stream.release()

def test_face_mesh_detector():
    detector = FaceMeshDetector()
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res = detector.process_frame(dummy_frame)
    assert "face_detected" in res
    assert "ear" in res
    assert "mar" in res
    assert "head_pose" in res
    assert "facial_expression" in res
    assert "annotated_frame" in res

def test_dg_fusion_focused():
    fusion = DGFusionEngine()
    cv_res = {
        "face_detected": True,
        "ear": 0.30,
        "mar": 0.05,
        "head_pose": {"yaw": 2.0, "pitch": -2.0, "roll": 0.0},
        "facial_expression": "FOCUSED_ATTENTIVE"
    }
    dg_packet = {
        "timestamp": 12345.0,
        "gaze_x": 0.50,
        "gaze_y": 0.50,
        "study_zone_active": True,
        "fixation_duration_ms": 1500,
        "gesture_state": "ACTIVE_STUDY_READING",
        "dg_focus_score": 92.0
    }
    out = fusion.fuse(cv_res, dg_packet)
    assert out["is_studying"] is True
    assert out["focus_score"] >= 70.0
    assert out["indiscipline_flag"] is False

def test_dg_fusion_talking_indiscipline():
    fusion = DGFusionEngine()
    cv_res = {
        "face_detected": True,
        "ear": 0.28,
        "mar": 0.65,
        "head_pose": {"yaw": 25.0, "pitch": 0.0, "roll": 0.0},
        "facial_expression": "TALKING_INDISCIPLINE"
    }
    dg_packet = {
        "timestamp": 12345.0,
        "gaze_x": 0.85,
        "gaze_y": 0.50,
        "study_zone_active": False,
        "fixation_duration_ms": 100,
        "gesture_state": "VERBAL_INTERACTION",
        "dg_focus_score": 20.0
    }
    for _ in range(20):
        out = fusion.fuse(cv_res, dg_packet)
    assert out["indiscipline_flag"] is True
    assert out["indiscipline_type"] == "TALKING_DISRUPTION"

def test_study_pipeline_step():
    pipeline = StudyDetectorPipeline(camera_source="synthetic", student_id="STU-101")
    res = pipeline.step()
    assert res["success"] is True
    assert "fusion_result" in res
    assert "focus_score" in res["fusion_result"]
    pipeline.release()
