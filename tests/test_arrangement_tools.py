"""
Server-side tests for the Phase 1 arrangement tools and the `view` parameter
on the clip tools. The Ableton socket is mocked — no Ableton, no network.
"""

import asyncio
import inspect
import json

import pytest

import MCP_Server.server as server
from MCP_Server.dataset.trajectory_decorator import MODIFYING_TOOLS, _PARAM_KEYS


def call(tool, *args, **kwargs):
    """Invoke a tool whether or not @trajectory_tool made it a coroutine."""
    result = tool(*args, **kwargs)
    if inspect.iscoroutine(result):
        return asyncio.run(result)
    return result


class FakeConnection:
    """Answers each command from a dict of canned responses."""

    def __init__(self, responses=None, signature=(4, 4)):
        self.responses = dict(responses or {})
        self.responses.setdefault("get_session_info", {
            "signature_numerator": signature[0],
            "signature_denominator": signature[1],
        })
        self.sent = []

    def send_command(self, command_type, params=None):
        self.sent.append((command_type, params or {}))
        return self.responses.get(command_type, {})

    def commands(self):
        return [c for c, _ in self.sent]

    def last(self, command_type):
        return [p for c, p in self.sent if c == command_type][-1]


@pytest.fixture
def fake_conn(monkeypatch):
    def _make(responses=None, signature=(4, 4)):
        conn = FakeConnection(responses, signature)
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


@pytest.fixture
def without_capability(monkeypatch):
    """Make one capability missing, keeping the rest available."""
    import MCP_Server.script_handshake as sh

    def _set(missing_name):
        monkeypatch.setattr(
            sh, "require_capability",
            lambda name: f"missing capability '{name}'" if name == missing_name else None,
        )
    return _set


# --------------------------------------------------------------------------
# get_arrangement_info
# --------------------------------------------------------------------------

ARRANGEMENT_INFO = {
    "song_length": 48.0,
    "current_song_time": 6.0,
    "loop": {"enabled": False, "start": 0.0, "length": 16.0},
    "tempo": 120.0,
    "signature_numerator": 3,
    "signature_denominator": 4,
    "cue_points": [{"index": 0, "name": "Intro", "time": 0.0},
                   {"index": 1, "name": "Verse", "time": 12.0}],
    "tracks": [
        {"index": 0, "name": "Bass", "is_midi_track": True, "is_audio_track": False,
         "is_group_track": False,
         "clips": [{"index": 0, "name": "A", "start_time": 3.0, "end_time": 7.5,
                    "length": 4.5, "is_midi_clip": True, "muted": False}]},
        {"index": 1, "name": "Group", "is_midi_track": False, "is_audio_track": False,
         "is_group_track": True, "clips": []},
    ],
}


def test_get_arrangement_info_adds_bars(fake_conn):
    conn = fake_conn({"get_arrangement_info": json.loads(json.dumps(ARRANGEMENT_INFO))})
    out = json.loads(call(server.get_arrangement_info, None))
    assert conn.commands() == ["get_arrangement_info"]
    assert out["current_bar"] == 3.0
    assert [c["bar"] for c in out["cue_points"]] == [1.0, 5.0]
    clip = out["tracks"][0]["clips"][0]
    assert (clip["start_bar"], clip["end_bar"]) == (2.0, 3.5)
    assert out["tracks"][1]["clips"] == []
    assert out["tempo"] == 120.0


def test_get_arrangement_info_6_8(fake_conn):
    info = json.loads(json.dumps(ARRANGEMENT_INFO))
    info["signature_numerator"], info["signature_denominator"] = 6, 8
    fake_conn({"get_arrangement_info": info})
    out = json.loads(call(server.get_arrangement_info, None))
    # 6/8 bar = 3 beats
    assert out["current_bar"] == 3.0
    assert out["tracks"][0]["clips"][0]["end_bar"] == 3.5


def test_get_arrangement_info_missing_capability(fake_conn, without_capability):
    conn = fake_conn()
    without_capability("get_arrangement_info")
    out = call(server.get_arrangement_info, None)
    assert "missing capability" in out
    assert conn.sent == []


# --------------------------------------------------------------------------
# cue_point
# --------------------------------------------------------------------------

def test_cue_point_jump_by_name(fake_conn):
    conn = fake_conn({"cue_point": {"action": "jump", "cue": {"name": "Verse", "time": 12.0},
                                    "current_song_time": 12.0}})
    out = call(server.cue_point, None, "jump", name="verse")
    assert conn.sent == [("cue_point", {"action": "jump", "name": "verse", "time": None})]
    assert "Verse" in out and "12.0" in out


def test_cue_point_bar_converts_with_signature(fake_conn):
    conn = fake_conn(signature=(3, 4))
    call(server.cue_point, None, "delete", bar=5)
    assert conn.commands() == ["get_session_info", "cue_point"]
    assert conn.last("cue_point")["time"] == 12.0


def test_cue_point_next_without_position(fake_conn):
    conn = fake_conn({"cue_point": {"action": "next", "cue": None, "current_song_time": 8.0}})
    out = call(server.cue_point, None, "next")
    assert conn.commands() == ["cue_point"]
    assert "8.0" in out


@pytest.mark.parametrize("kwargs", [
    {"action": "skip"},
    {"action": "jump", "time": 4.0, "bar": 2},
    {"action": "jump", "bar": 0.5},
])
def test_cue_point_validation(fake_conn, kwargs):
    conn = fake_conn()
    out = call(server.cue_point, None, **kwargs)
    assert out.startswith("Error")
    assert "cue_point" not in conn.commands()


# --------------------------------------------------------------------------
# set_arrangement_loop
# --------------------------------------------------------------------------

def test_set_arrangement_loop_beats(fake_conn):
    conn = fake_conn({"set_arrangement_loop": {"enabled": True, "start": 4.0, "length": 8.0}})
    out = call(server.set_arrangement_loop, None, True, start=4.0, length=8.0)
    assert conn.sent == [("set_arrangement_loop",
                          {"enabled": True, "start": 4.0, "length": 8.0})]
    assert "on" in out


def test_set_arrangement_loop_enable_only(fake_conn):
    conn = fake_conn()
    call(server.set_arrangement_loop, None, False)
    assert conn.sent == [("set_arrangement_loop",
                          {"enabled": False, "start": None, "length": None})]


def test_set_arrangement_loop_bars_in_6_8(fake_conn):
    conn = fake_conn(signature=(6, 8))
    call(server.set_arrangement_loop, None, True, start_bar=3, length_bars=2)
    assert conn.commands() == ["get_session_info", "set_arrangement_loop"]
    assert conn.last("set_arrangement_loop") == {"enabled": True, "start": 6.0, "length": 6.0}


@pytest.mark.parametrize("kwargs", [
    {"start": 0.0, "start_bar": 1},
    {"length": 4.0, "length_bars": 1},
    {"length": 0},
    {"length_bars": -1},
    {"start": -1.0},
    {"start_bar": 0},
])
def test_set_arrangement_loop_validation(fake_conn, kwargs):
    conn = fake_conn()
    out = call(server.set_arrangement_loop, None, True, **kwargs)
    assert out.startswith("Error setting arrangement loop")
    assert "set_arrangement_loop" not in conn.commands()


# --------------------------------------------------------------------------
# create_arrangement_midi_clip
# --------------------------------------------------------------------------

def test_create_arrangement_midi_clip_beats(fake_conn):
    conn = fake_conn({"create_arrangement_midi_clip": {
        "track_index": 1, "clip_index": 2, "name": "Riff", "start_time": 8.0,
        "end_time": 12.0, "note_count": 2, "method": "session_fallback"}})
    out = call(server.create_arrangement_midi_clip, None, 1, start=8.0, length=4.0,
               notes=[{"pitch": "C3", "start_time": 0, "duration": 1, "velocity": 100},
                      {"pitch": 64, "start_time": 1, "duration": 1, "velocity": 90}],
               name="Riff")
    # No bar argument, so no time-signature lookup
    assert conn.commands() == ["create_arrangement_midi_clip"]
    params = conn.last("create_arrangement_midi_clip")
    assert params["track_index"] == 1
    assert (params["start"], params["length"]) == (8.0, 4.0)
    assert [n["pitch"] for n in params["notes"]] == [60, 64]
    assert params["name"] == "Riff"
    assert params["allow_overlap"] is False
    assert "index 2" in out and "temporary Session clip" in out


def test_create_arrangement_midi_clip_bars_in_3_4(fake_conn):
    conn = fake_conn(signature=(3, 4))
    call(server.create_arrangement_midi_clip, None, 0, start_bar=3, length_bars=2,
         allow_overlap=True)
    params = conn.last("create_arrangement_midi_clip")
    assert (params["start"], params["length"]) == (6.0, 6.0)
    assert params["notes"] == []
    assert params["allow_overlap"] is True


def test_create_arrangement_midi_clip_mixed_units(fake_conn):
    conn = fake_conn(signature=(7, 8))
    call(server.create_arrangement_midi_clip, None, 0, start=2.0, length_bars=2)
    assert conn.commands() == ["get_session_info", "create_arrangement_midi_clip"]
    params = conn.last("create_arrangement_midi_clip")
    assert (params["start"], params["length"]) == (2.0, 7.0)


@pytest.mark.parametrize("kwargs", [
    {"length": 4.0},
    {"start": 0.0},
    {"start": 0.0, "start_bar": 1, "length": 4.0},
    {"start": 0.0, "length": 4.0, "length_bars": 1},
    {"start": 0.0, "length": 0.0},
    {"start_bar": 0.5, "length": 4.0},
    {"start": 0.0, "length": 4.0, "notes": [{"pitch": "H2"}]},
])
def test_create_arrangement_midi_clip_validation(fake_conn, kwargs):
    conn = fake_conn()
    out = call(server.create_arrangement_midi_clip, None, 0, **kwargs)
    assert out.startswith("Error creating arrangement MIDI clip")
    assert "create_arrangement_midi_clip" not in conn.commands()


def test_argument_errors_skip_signature_lookup(fake_conn):
    conn = fake_conn()
    call(server.create_arrangement_midi_clip, None, 0, start=0.0, start_bar=1, length_bars=1)
    assert conn.sent == []


# --------------------------------------------------------------------------
# create_arrangement_audio_clip
# --------------------------------------------------------------------------

def test_create_arrangement_audio_clip(fake_conn):
    conn = fake_conn({"create_arrangement_audio_clip": {
        "track_index": 2, "clip_index": 0, "name": "loop", "start_time": 16.0,
        "end_time": 24.0, "length": 8.0}})
    out = call(server.create_arrangement_audio_clip, None, 2, "/tmp/loop.wav", start=16.0)
    assert conn.sent == [("create_arrangement_audio_clip", {
        "track_index": 2, "path": "/tmp/loop.wav", "start": 16.0, "allow_overlap": False})]
    assert "'loop'" in out and "8.0" in out


def test_create_arrangement_audio_clip_bar(fake_conn):
    conn = fake_conn(signature=(6, 8))
    call(server.create_arrangement_audio_clip, None, 2, "/tmp/loop.wav", start_bar=2)
    assert conn.last("create_arrangement_audio_clip")["start"] == 3.0


@pytest.mark.parametrize("kwargs", [{}, {"start": 1.0, "start_bar": 1}, {"start": -2.0}])
def test_create_arrangement_audio_clip_validation(fake_conn, kwargs):
    conn = fake_conn()
    out = call(server.create_arrangement_audio_clip, None, 2, "/tmp/loop.wav", **kwargs)
    assert out.startswith("Error creating arrangement audio clip")
    assert "create_arrangement_audio_clip" not in conn.commands()


# --------------------------------------------------------------------------
# set_clip_properties
# --------------------------------------------------------------------------

def test_set_clip_properties(fake_conn):
    conn = fake_conn({"set_clip_properties": {"properties": {"name": "Verse", "looping": True}}})
    out = call(server.set_clip_properties, None, 1, 3, {"name": "Verse", "looping": True},
               view="arrangement")
    assert conn.sent == [("set_clip_properties", {
        "track_index": 1, "clip_index": 3, "view": "arrangement",
        "properties": {"name": "Verse", "looping": True}})]
    assert "arrangement clip 3" in out and "Verse" in out


def test_set_clip_properties_default_view(fake_conn):
    conn = fake_conn()
    call(server.set_clip_properties, None, 0, 0, {"muted": True})
    assert conn.last("set_clip_properties")["view"] == "session"


def test_set_clip_properties_bad_view(fake_conn):
    conn = fake_conn()
    out = call(server.set_clip_properties, None, 0, 0, {"muted": True}, view="Arrangement")
    assert out.startswith("Error setting clip properties")
    assert conn.sent == []


# --------------------------------------------------------------------------
# view parameter on the clip tools
# --------------------------------------------------------------------------

VIEW_TOOLS = [
    ("get_clip_notes", lambda **kw: call(server.get_clip_notes, None, 1, 2, **kw)),
    ("add_notes_to_clip", lambda **kw: call(
        server.add_notes_to_clip, None, 1, 2,
        [{"pitch": "C3", "start_time": 0, "duration": 1, "velocity": 100}], **kw)),
    ("modify_clip_notes", lambda **kw: call(
        server.modify_clip_notes, None, 1, 2, [{"note_id": 1, "velocity": 50}], **kw)),
    ("remove_notes_from_clip", lambda **kw: call(server.remove_notes_from_clip, None, 1, 2, **kw)),
    ("clear_notes_from_clip", lambda **kw: call(server.clear_notes_from_clip, None, 1, 2, **kw)),
    ("delete_clip", lambda **kw: call(server.delete_clip, None, 1, 2, **kw)),
]


@pytest.mark.parametrize("command, invoke", VIEW_TOOLS)
def test_session_view_is_not_sent(fake_conn, command, invoke):
    conn = fake_conn()
    invoke()
    invoke(view="session")
    assert conn.commands() == [command, command]
    assert all("view" not in params for _, params in conn.sent)


@pytest.mark.parametrize("command, invoke", VIEW_TOOLS)
def test_arrangement_view_is_sent(fake_conn, command, invoke):
    conn = fake_conn()
    out = invoke(view="arrangement")
    assert conn.commands() == [command]
    params = conn.last(command)
    assert params["view"] == "arrangement"
    assert (params["track_index"], params["clip_index"]) == (1, 2)
    assert not out.startswith("Error")


@pytest.mark.parametrize("command, invoke", VIEW_TOOLS)
def test_arrangement_view_needs_clip_view_param(fake_conn, without_capability, command, invoke):
    conn = fake_conn()
    without_capability("clip_view_param")
    out = invoke(view="arrangement")
    assert "clip_view_param" in out
    assert conn.sent == []


@pytest.mark.parametrize("command, invoke", VIEW_TOOLS)
def test_bad_view_rejected(fake_conn, command, invoke):
    conn = fake_conn()
    out = invoke(view="timeline")
    assert out.startswith("Error")
    assert "timeline" in out
    assert conn.sent == []


def test_arrangement_label_in_messages(fake_conn):
    fake_conn({"clear_notes_from_clip": {"cleared_count": 3, "clip_name": "A"}})
    out = call(server.clear_notes_from_clip, None, 1, 2, view="arrangement")
    assert out == "Cleared 3 note(s) from clip 'A' (track 1, arrangement clip 2)"


# --------------------------------------------------------------------------
# Plumbing
# --------------------------------------------------------------------------

NEW_MODIFYING = ["cue_point", "set_arrangement_loop", "create_arrangement_midi_clip",
                 "create_arrangement_audio_clip", "set_clip_properties"]


def test_new_modifying_tools_are_recorded():
    assert set(NEW_MODIFYING) <= MODIFYING_TOOLS
    assert "get_arrangement_info" not in MODIFYING_TOOLS


def test_new_param_keys():
    for key in ("start", "start_bar", "length_bars", "view", "action",
                "allow_overlap", "enabled", "bar"):
        assert key in _PARAM_KEYS
    assert len(_PARAM_KEYS) == len(set(_PARAM_KEYS))


class TimeoutRecordingSocket:
    def __init__(self, response):
        self._payload = json.dumps(response).encode("utf-8")
        self.timeouts = []

    def sendall(self, data):
        pass

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def recv(self, _size):
        payload, self._payload = self._payload, b""
        return payload


@pytest.mark.parametrize("command, expected", [
    ("get_arrangement_info", 10.0),
    ("cue_point", 15.0),
    ("set_arrangement_loop", 15.0),
    ("create_arrangement_midi_clip", 15.0),
    ("set_clip_properties", 15.0),
    ("create_arrangement_audio_clip", 65.0),
])
def test_socket_timeouts(command, expected):
    sock = TimeoutRecordingSocket({"status": "success", "result": {}})
    conn = server.AbletonConnection(host="localhost", port=0, sock=sock)
    conn.send_command(command, {})
    assert sock.timeouts == [expected]


def test_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    by_name = {t.name: t for t in tools}
    for name in ["get_arrangement_info", "cue_point", "set_arrangement_loop",
                 "create_arrangement_midi_clip", "create_arrangement_audio_clip",
                 "set_clip_properties"]:
        assert name in by_name
    for name in ["get_clip_notes", "add_notes_to_clip", "modify_clip_notes",
                 "remove_notes_from_clip", "clear_notes_from_clip", "delete_clip"]:
        assert "view" in by_name[name].inputSchema["properties"]
