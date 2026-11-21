from types import SimpleNamespace
from unittest.mock import Mock, patch

from tracker.head_tracker import HeadTracker


def test_camera_failure_releases_resources_and_returns_failure(capsys):
    face_mesh = Mock()
    mediapipe = SimpleNamespace(
        solutions=SimpleNamespace(
            face_mesh=SimpleNamespace(FaceMesh=Mock(return_value=face_mesh))
        )
    )
    camera = Mock()
    camera.isOpened.return_value = False
    tracker = HeadTracker({"camera_id": 3, "preview": False})

    with patch.dict("sys.modules", {"mediapipe": mediapipe}), \
            patch("tracker.head_tracker.cv2.VideoCapture", return_value=camera) as capture:
        assert tracker.run() is False

    assert all(call.args[0] == 3 for call in capture.call_args_list)
    assert camera.release.call_count == capture.call_count
    face_mesh.close.assert_called_once()
    assert "camera 3" in capsys.readouterr().err


def test_camera_without_frames_reports_failure(capsys):
    face_mesh = Mock()
    mediapipe = SimpleNamespace(
        solutions=SimpleNamespace(
            face_mesh=SimpleNamespace(FaceMesh=Mock(return_value=face_mesh))
        )
    )
    camera = Mock()
    camera.isOpened.return_value = True
    camera.read.return_value = (False, None)
    tracker = HeadTracker({"preview": False})
    with patch.dict("sys.modules", {"mediapipe": mediapipe}), \
            patch("tracker.head_tracker.cv2.VideoCapture", return_value=camera), \
            patch("tracker.head_tracker.time.monotonic", side_effect=[0.0, 6.0]):
        assert tracker.run() is False

    camera.release.assert_called_once()
    face_mesh.close.assert_called_once()
    assert "stopped delivering frames" in capsys.readouterr().err
