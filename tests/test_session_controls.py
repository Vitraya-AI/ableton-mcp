"""
Server-side tests for note editing, mixer, scene and session tools, pitch-name
parsing and structured errors. The Ableton socket is mocked, so these run
anywhere — no Ableton, no network.
"""

import asyncio
import inspect
import json

import pytest

import MCP_Server.server as server
from MCP_Server.dataset.trajectory_decorator import MODIFYING_TOOLS


def call(tool, *args, **kwargs):
    """Invoke a tool whether or not @trajectory_tool made it a coroutine."""
    result = tool(*args, **kwargs)
    if inspect.iscoroutine(result):
        return asyncio.run(result)
    return result


class FakeConnection:
    def __init__(self, response=None, raise_exc=None):
        self.response = {} if response is None else response
        self.raise_exc = raise_exc
        self.sent = []

    def send_command(self, command_type, params=None):
        self.sent.append((command_type, params or {}))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.response


@pytest.fixture
def fake_conn(monkeypatch):
    def _make(response=None, raise_exc=None):
        conn = FakeConnection(response=response, raise_exc=raise_exc)
        monkeypatch.setattr(server, "get_ableton_connection", lambda: conn)
        return conn
    return _make


@pytest.fixture(autouse=True)
def _silence_telemetry(monkeypatch):
    class _Dummy:
        def record_event(self, *a, **k):
            pass
    import MCP_Server.telemetry_decorator as td
    monkeypatch.setattr(td, "get_telemetry", lambda: _Dummy(), raising=False)


@pytest.fixture(autouse=True)
def _no_consent_prompt(monkeypatch):
    import MCP_Server.dataset.consent as consent
    monkeypatch.setattr(consent, "maybe_consent_notice", lambda: "")


@pytest.fixture(autouse=True)
def _script_capabilities_available(monkeypatch):
    import MCP_Server.script_handshake as sh
    monkeypatch.setattr(sh, "require_capability", lambda name: None)


# --------------------------------------------------------------------------
# Pitch names
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name, midi", [
    ("C3", 60),      # Ableton's piano roll convention
    ("C-2", 0),
    ("G8", 127),
    ("Eb2", 51),
    ("F#4", 78),
    ("c3", 60),
    ("B#2", 60),
    ("60", 60),
    (60, 60),
    (60.0, 60),
])
def test_parse_pitch_accepts_numbers_and_ableton_note_names(name, midi):
    assert server._parse_pitch(name) == midi


@pytest.mark.parametrize("bad", ["H3", "C", "C#", "G9", "C-3", -1, 128, 60.5, True, None])
def test_parse_pitch_rejects_invalid_or_out_of_range(bad):
    with pytest.raises(ValueError):
        server._parse_pitch(bad)


def test_add_notes_converts_note_names_before_sending(fake_conn):
    conn = fake_conn(response={"note_count": 2})
    call(server.add_notes_to_clip, None, 0, 0, [
        {"pitch": "C1", "start_time": 0.0, "duration": 0.25, "velocity": 100},
        {"pitch": 38, "start_time": 1.0, "duration": 0.25, "velocity": 90,
         "probability": 0.5},
    ])
    _, params = conn.sent[0]
    assert [n["pitch"] for n in params["notes"]] == [36, 38]
    assert params["notes"][1]["probability"] == 0.5


def test_bad_note_name_is_reported_without_contacting_ableton(fake_conn):
    conn = fake_conn()
    out = call(server.add_notes_to_clip, None, 0, 0, [{"pitch": "X9"}])
    assert out.startswith("Error adding notes to clip")
    assert conn.sent == []


# --------------------------------------------------------------------------
# Note editing
# --------------------------------------------------------------------------

def test_modify_clip_notes_sends_ids_and_parsed_pitches(fake_conn):
    conn = fake_conn(response={"modified_count": 1})
    out = call(server.modify_clip_notes, None, 1, 2,
               [{"note_id": 7, "pitch": "D3", "velocity": 64}])
    assert conn.sent == [("modify_clip_notes", {
        "track_index": 1, "clip_index": 2,
        "notes": [{"note_id": 7, "pitch": 62, "velocity": 64}],
    })]
    assert "Modified 1 note" in out


def test_remove_notes_from_clip_sends_window(fake_conn):
    conn = fake_conn(response={"removed_count": 4})
    out = call(server.remove_notes_from_clip, None, 0, 0,
               from_time=4.0, time_span=4.0, from_pitch="C1", pitch_span=1)
    assert conn.sent == [("remove_notes_from_clip", {
        "track_index": 0, "clip_index": 0,
        "from_time": 4.0, "time_span": 4.0, "from_pitch": 36, "pitch_span": 1,
    })]
    assert "Removed 4 note" in out


def test_remove_notes_defaults_cover_the_whole_clip(fake_conn):
    conn = fake_conn(response={"removed_count": 0})
    call(server.remove_notes_from_clip, None, 0, 0)
    _, params = conn.sent[0]
    assert params == {"track_index": 0, "clip_index": 0, "from_time": 0.0,
                      "time_span": -1.0, "from_pitch": 0, "pitch_span": 128}


# --------------------------------------------------------------------------
# Every new tool sends the command its Remote Script handler expects
# --------------------------------------------------------------------------

TOOL_CASES = [
    (server.duplicate_clip, (0, 1, 2), "duplicate_clip",
     {"track_index": 0, "source_clip_index": 1, "dest_clip_index": 2}),
    (server.delete_track, (3,), "delete_track", {"track_index": 3}),
    (server.set_time_signature, (6, 8), "set_time_signature",
     {"numerator": 6, "denominator": 8}),
    (server.undo, (), "undo", {}),
    (server.redo, (), "redo", {}),
    (server.set_track_volume, (0, 0.85), "set_track_volume",
     {"track_index": 0, "value": 0.85}),
    (server.set_track_panning, (0, -0.5), "set_track_panning",
     {"track_index": 0, "value": -0.5}),
    (server.set_track_mute, (0, True), "set_track_mute",
     {"track_index": 0, "value": True}),
    (server.set_track_solo, (0, True), "set_track_solo",
     {"track_index": 0, "value": True}),
    (server.set_track_arm, (0, False), "set_track_arm",
     {"track_index": 0, "value": False}),
    (server.set_send_level, (0, 1, 0.5), "set_send_level",
     {"track_index": 0, "send_index": 1, "value": 0.5}),
    (server.set_master_volume, (0.7,), "set_master_volume", {"value": 0.7}),
    (server.set_master_panning, (0.1,), "set_master_panning", {"value": 0.1}),
    (server.create_scene, (-1,), "create_scene", {"index": -1}),
    (server.fire_scene, (2,), "fire_scene", {"scene_index": 2}),
    (server.delete_scene, (2,), "delete_scene", {"scene_index": 2}),
    (server.set_scene_name, (2, "Chorus"), "set_scene_name",
     {"scene_index": 2, "name": "Chorus"}),
]


@pytest.mark.parametrize("tool, args, command, params", TOOL_CASES,
                         ids=[c[2] for c in TOOL_CASES])
def test_tool_sends_expected_command(fake_conn, tool, args, command, params):
    conn = fake_conn(response={})
    out = call(tool, None, *args)
    assert conn.sent == [(command, params)]
    assert not out.lower().startswith("error")


@pytest.mark.parametrize("tool, args, command, params", TOOL_CASES,
                         ids=[c[2] for c in TOOL_CASES])
def test_tool_reports_missing_capability_without_sending(
        monkeypatch, fake_conn, tool, args, command, params):
    import MCP_Server.script_handshake as sh
    monkeypatch.setattr(sh, "require_capability",
                        lambda name: "Ableton Remote Script missing capability '%s'" % name)
    conn = fake_conn()
    out = call(tool, None, *args)
    assert out == "Ableton Remote Script missing capability '%s'" % command
    assert conn.sent == []


@pytest.mark.parametrize("command", [c[2] for c in TOOL_CASES if c[2] != "fire_scene"]
                         + ["modify_clip_notes", "remove_notes_from_clip"])
def test_mutating_tools_are_snapshotted_by_the_dataset_recorder(command):
    assert command in MODIFYING_TOOLS


def test_undo_reports_when_there_is_nothing_to_undo(fake_conn):
    fake_conn(response={"undone": False, "reason": "Nothing to undo"})
    assert call(server.undo, None) == "Nothing to undo"


def test_get_browser_tree_forwards_max_depth(fake_conn):
    conn = fake_conn(response={"categories": [], "total_folders": 0})
    call(server.get_browser_tree, None, "instruments", 2)
    assert conn.sent == [("get_browser_tree",
                          {"category_type": "instruments", "max_depth": 2})]


# --------------------------------------------------------------------------
# Structured errors
# --------------------------------------------------------------------------

def test_tool_error_includes_machine_readable_code(fake_conn):
    fake_conn(raise_exc=server.AbletonCommandError(
        "Track index out of range", "track_index_out_of_range"))
    out = call(server.set_track_mute, None, 99, True)
    assert out == ("Error setting track mute: Track index out of range "
                   "(code: track_index_out_of_range)")


class FakeSocket:
    """Answers one request with a canned response."""

    def __init__(self, response):
        self._payload = json.dumps(response).encode("utf-8")
        self.sent = []
        self.closed = False

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, _timeout):
        pass

    def recv(self, _size):
        payload, self._payload = self._payload, b""
        return payload

    def close(self):
        self.closed = True


def test_ableton_error_raises_with_code_and_keeps_the_connection():
    """A refused command is a normal answer. It used to fall into the generic
    handler, which threw the socket away and forced a reconnect."""
    sock = FakeSocket({"status": "error", "message": "Scene index out of range",
                       "code": "scene_index_out_of_range"})
    conn = server.AbletonConnection(host="localhost", port=0, sock=sock)

    with pytest.raises(server.AbletonCommandError) as info:
        conn.send_command("fire_scene", {"scene_index": 9})

    assert info.value.code == "scene_index_out_of_range"
    assert info.value.message == "Scene index out of range"
    assert conn.sock is sock
    assert not sock.closed


def test_error_without_code_defaults_to_internal_error():
    sock = FakeSocket({"status": "error", "message": "boom"})
    conn = server.AbletonConnection(host="localhost", port=0, sock=sock)
    with pytest.raises(server.AbletonCommandError) as info:
        conn.send_command("undo")
    assert info.value.code == "internal_error"


def test_handshake_still_detects_legacy_scripts(monkeypatch):
    """Old scripts answer get_script_info with Unknown command; the handshake
    must still recognise that now that errors are AbletonCommandError."""
    from MCP_Server import script_handshake
    monkeypatch.setattr(script_handshake, "_script_info", None)
    monkeypatch.setattr(script_handshake, "_handshake_done", False)

    def send(_command):
        raise server.AbletonCommandError("Unknown command: get_script_info",
                                         "unknown_command")

    info = script_handshake.handshake(send)
    assert info["script_version"] == "legacy"
