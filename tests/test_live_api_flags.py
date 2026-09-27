"""live_api_available / live_version read the cached get_script_info."""

import pytest

from MCP_Server import script_handshake
from MCP_Server.remote_script_install import EXPECTED_REMOTE_SCRIPT_VERSION


@pytest.fixture(autouse=True)
def reset_handshake(monkeypatch):
    monkeypatch.setattr(script_handshake, "_script_info", None)
    monkeypatch.setattr(script_handshake, "_handshake_done", False)


def _handshake_with(result):
    return script_handshake.handshake(lambda _command: result)


def test_no_handshake():
    assert script_handshake.live_api_available("track_create_midi_clip") is False
    assert script_handshake.live_version() is None


def test_flags_and_version_present():
    _handshake_with({
        "script_version": EXPECTED_REMOTE_SCRIPT_VERSION,
        "capabilities": ["get_script_info"],
        "live_version": {"major": 11, "minor": 3, "bugfix": 42, "string": "11.3.42"},
        "live_api": {"track_create_midi_clip": False, "song_begin_undo_step": True},
    })
    assert script_handshake.live_api_available("song_begin_undo_step") is True
    assert script_handshake.live_api_available("track_create_midi_clip") is False
    assert script_handshake.live_api_available("plugin_device_presets") is False
    assert script_handshake.live_version() == (11, 3, 42)


def test_unknown_live_info():
    _handshake_with({
        "script_version": EXPECTED_REMOTE_SCRIPT_VERSION,
        "capabilities": [],
        "live_version": None,
        "live_api": {},
    })
    assert script_handshake.live_api_available("song_begin_undo_step") is False
    assert script_handshake.live_version() is None


def test_older_script_without_fields():
    _handshake_with({"script_version": "1.8.1", "capabilities": []})
    assert script_handshake.live_api_available("song_begin_undo_step") is False
    assert script_handshake.live_version() is None


def test_malformed_version():
    _handshake_with({
        "script_version": EXPECTED_REMOTE_SCRIPT_VERSION,
        "live_version": {"major": 11, "minor": "x"},
        "live_api": {"song_begin_undo_step": "yes"},
    })
    assert script_handshake.live_version() is None
    assert script_handshake.live_api_available("song_begin_undo_step") is False


def test_legacy_script():
    def send(_command):
        raise Exception("Unknown command: get_script_info")

    info = script_handshake.handshake(send)
    assert info["script_version"] == "legacy"
    assert script_handshake.live_api_available("song_begin_undo_step") is False
    assert script_handshake.live_version() is None
