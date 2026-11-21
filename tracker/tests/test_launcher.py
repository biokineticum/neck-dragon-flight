import os
import shutil
import subprocess
from unittest.mock import Mock, patch

import pytest

from tracker import launch_game


def test_tracker_stays_alive_until_game_exits():
    tracker = Mock()
    tracker.poll.return_value = None
    game = Mock()
    game.wait.side_effect = [subprocess.TimeoutExpired("godot", 0.5), 0]

    with patch.object(launch_game.subprocess, "Popen", side_effect=[tracker, game]) as popen:
        assert launch_game.launch("godot.exe") == 0

    assert popen.call_args_list[0].args[0][1] == "-u"
    tracker.terminate.assert_called_once()
    tracker.wait.assert_called_once()


def test_failed_tracker_is_reported_without_stopping_game(capsys):
    tracker = Mock()
    tracker.poll.return_value = 1
    game = Mock()
    game.wait.side_effect = [subprocess.TimeoutExpired("godot", 0.5), 0]

    with patch.object(launch_game.subprocess, "Popen", side_effect=[tracker, game]):
        assert launch_game.launch("godot.exe") == 0

    assert "webcam tracker stopped" in capsys.readouterr().err
    tracker.terminate.assert_not_called()


def test_tracker_is_stopped_when_godot_fails_to_launch(capsys):
    tracker = Mock()
    tracker.poll.return_value = None
    with patch.object(launch_game.subprocess, "Popen", side_effect=[tracker, OSError("missing")]):
        assert launch_game.launch("missing.exe") == 1

    assert "missing" in capsys.readouterr().err
    tracker.terminate.assert_called_once()


@pytest.mark.skipif(os.name != "nt" or shutil.which("godot") is None, reason="Windows Godot launcher required")
def test_real_godot_cmd_with_spaces_in_executable_and_project_paths(tmp_path):
    godot = shutil.which("godot")
    if not godot.lower().endswith((".cmd", ".bat")):
        pytest.skip("Godot is not a batch launcher")
    project = tmp_path / "project with spaces"
    project.mkdir()
    (project / "tracker").mkdir()
    (project / "tracker" / "head_tracker.py").write_text("import time\ntime.sleep(30)\n")
    (project / "project.godot").write_text(
        'config_version=5\n[application]\nconfig/name="Launcher test"\n'
        'run/main_scene="res://main.tscn"\n'
        '[rendering]\nrenderer/rendering_method="gl_compatibility"\n'
    )
    (project / "main.gd").write_text("extends Node\nfunc _ready():\n\tget_tree().quit()\n")
    (project / "main.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n'
        '[ext_resource type="Script" path="res://main.gd" id="1"]\n'
        '[node name="Main" type="Node"]\nscript = ExtResource("1")\n'
    )
    launcher_dir = tmp_path / "launcher with spaces"
    launcher_dir.mkdir()
    launcher = launcher_dir / "godot.cmd"
    shutil.copyfile(godot, launcher)
    with patch.object(launch_game, "PROJECT_DIR", project):
        assert launch_game.launch(str(launcher)) == 0
