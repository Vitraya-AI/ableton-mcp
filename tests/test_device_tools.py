"""
Server-side tests for the Phase 2 device and rack tools, chain addressing,
parameter names, and load_browser_item output. The Ableton socket is mocked.
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
    """Answers each command from a dict of canned responses (a list = one per call)."""

    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.responses.setdefault("get_session_info", {
            "signature_numerator": 4, "signature_denominator": 4})
        self.sent = []

    def send_command(self, command_type, params=None):
        self.sent.append((command_type, params or {}))
        response = self.responses.get(command_type, {})
        if isinstance(response, list):
            return response.pop(0)
        return response

    def commands(self):
        return [c for c, _ in self.sent]

    def last(self, command_type):
        return [p for c, p in self.sent if c == command_type][-1]


@pytest.fixture
def fake_conn(monkeypatch):
    def _make(responses=None):
        conn = FakeConnection(responses)
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
# Chain addressing, shared by every device tool
# --------------------------------------------------------------------------

DEVICE_TOOLS = [
    ("get_device_parameters", lambda **kw: call(server.get_device_parameters, None, 1, 2, **kw), {}),
    ("set_device_parameter", lambda **kw: call(
        server.set_device_parameter, None, 1, 2, 0.5, parameter_index=3, **kw),
     {"value": 0.5, "parameter_index": 3}),
    ("get_rack_info", lambda **kw: call(server.get_rack_info, None, 1, 2, **kw), {}),
    ("set_device_enabled", lambda **kw: call(server.set_device_enabled, None, 1, 2, False, **kw),
     {"enabled": False}),
    ("delete_device", lambda **kw: call(server.delete_device, None, 1, 2, **kw), {}),
    ("navigate_device_preset", lambda **kw: call(
        server.navigate_device_preset, None, 1, 2, "next", **kw), {"direction": "next"}),
]


@pytest.mark.parametrize("command, invoke, extra", DEVICE_TOOLS)
def test_top_level_device_sends_no_chain_params(fake_conn, command, invoke, extra):
    conn = fake_conn()
    invoke()
    assert conn.sent == [(command, {"track_index": 1, "device_index": 2, **extra})]


@pytest.mark.parametrize("command, invoke, extra", DEVICE_TOOLS)
def test_chain_params_sent_when_used(fake_conn, command, invoke, extra):
    conn = fake_conn()
    invoke(chain_index=0, chain_device_index=3)
    assert conn.sent == [(command, {"track_index": 1, "device_index": 2, **extra,
                                    "chain_index": 0, "chain_device_index": 3})]


@pytest.mark.parametrize("command, invoke, extra", DEVICE_TOOLS)
def test_chain_index_alone(fake_conn, command, invoke, extra):
    conn = fake_conn()
    invoke(chain_index=1)
    params = conn.last(command)
    assert params["chain_index"] == 1
    assert "chain_device_index" not in params


@pytest.mark.parametrize("command, invoke, extra", DEVICE_TOOLS)
def test_chain_device_index_needs_chain_index(fake_conn, command, invoke, extra):
    conn = fake_conn()
    out = invoke(chain_device_index=1)
    assert out.startswith("Error")
    assert "chain_index" in out
    assert conn.sent == []


@pytest.mark.parametrize("command, invoke, extra", DEVICE_TOOLS)
def test_chain_params_need_capability(fake_conn, without_capability, command, invoke, extra):
    conn = fake_conn()
    without_capability("device_chain_param")
    out = invoke(chain_index=0)
    assert "device_chain_param" in out
    assert conn.sent == []


@pytest.mark.parametrize("command, invoke, extra", DEVICE_TOOLS)
def test_top_level_works_without_chain_capability(fake_conn, without_capability,
                                                  command, invoke, extra):
    conn = fake_conn()
    without_capability("device_chain_param")
    invoke()
    assert conn.commands() == [command]


# --------------------------------------------------------------------------
# set_device_parameter by name
# --------------------------------------------------------------------------

def test_set_device_parameter_by_name(fake_conn):
    conn = fake_conn({"set_device_parameter": {
        "name": "Filter Freq", "old_value": 0.2, "value": 0.7, "parameter_index": 5}})
    out = call(server.set_device_parameter, None, 0, 1, 0.7, parameter_name="filter freq")
    assert conn.sent == [("set_device_parameter", {
        "track_index": 0, "device_index": 1, "value": 0.7, "parameter_name": "filter freq"})]
    assert out == "Set Filter Freq (parameter 5) 0.2 → 0.7"


def test_set_device_parameter_by_index_output(fake_conn):
    fake_conn({"set_device_parameter": {"name": "Dry/Wet", "old_value": 1.0, "value": 0.5}})
    out = call(server.set_device_parameter, None, 0, 1, 0.5, parameter_index=2)
    assert out == "Set Dry/Wet (parameter 2) 1.0 → 0.5"


@pytest.mark.parametrize("kwargs", [{}, {"parameter_index": 1, "parameter_name": "Gain"}])
def test_set_device_parameter_needs_exactly_one(fake_conn, kwargs):
    conn = fake_conn()
    out = call(server.set_device_parameter, None, 0, 1, 0.5, **kwargs)
    assert out.startswith("Error setting device parameter")
    assert "exactly one" in out
    assert conn.sent == []


def test_parameter_name_needs_capability(fake_conn, without_capability):
    conn = fake_conn()
    without_capability("parameter_name_param")
    out = call(server.set_device_parameter, None, 0, 1, 0.5, parameter_name="Gain")
    assert "parameter_name_param" in out
    assert conn.sent == []


def test_parameter_index_works_without_name_capability(fake_conn, without_capability):
    conn = fake_conn()
    without_capability("parameter_name_param")
    call(server.set_device_parameter, None, 0, 1, 0.5, parameter_index=0)
    assert conn.commands() == ["set_device_parameter"]


# --------------------------------------------------------------------------
# New tools: outputs
# --------------------------------------------------------------------------

RACK = {
    "track_index": 0, "device_index": 0, "chain_index": None, "chain_device_index": None,
    "name": "Drum Rack", "class_name": "DrumGroupDevice", "is_drum_rack": True,
    "macros": [{"index": 1, "name": "Macro 1", "value": 0.0, "min": 0.0, "max": 127.0}],
    "chains": [{"index": 0, "name": "Kick", "mute": False, "solo": False,
                "devices": [{"index": 0, "name": "Simpler", "class_name": "OriginalSimpler",
                             "type": "instrument", "is_active": True, "is_rack": False}]}],
    "drum_pads": [{"note": 36, "name": "Kick", "mute": False, "solo": False,
                   "chain_indices": [0]}],
}


def test_get_rack_info_returns_json(fake_conn):
    fake_conn({"get_rack_info": RACK})
    assert json.loads(call(server.get_rack_info, None, 0, 0)) == RACK


def test_get_rack_info_missing_capability(fake_conn, without_capability):
    conn = fake_conn()
    without_capability("get_rack_info")
    assert "missing capability 'get_rack_info'" in call(server.get_rack_info, None, 0, 0)
    assert conn.sent == []


def test_set_device_enabled_output(fake_conn):
    fake_conn({"set_device_enabled": {"name": "Reverb", "enabled": False, "is_active": False}})
    out = call(server.set_device_enabled, None, 1, 2, False, chain_index=0)
    assert out == "'Reverb' is now off (track 1, device 2, chain 0, chain device 0)"


def test_set_device_enabled_reports_inactive_parent(fake_conn):
    fake_conn({"set_device_enabled": {"name": "Reverb", "enabled": True, "is_active": False}})
    out = call(server.set_device_enabled, None, 1, 2, True)
    assert out.startswith("'Reverb' is now on (track 1, device 2)")
    assert "inactive" in out


def test_delete_device_output(fake_conn):
    fake_conn({"delete_device": {"deleted": "Saturator", "track_index": 1, "device_index": 2,
                                 "chain_index": None, "chain_device_index": None}})
    out = call(server.delete_device, None, 1, 2)
    assert out == "Deleted 'Saturator' (track 1, device 2). Use undo to restore it."
    assert "undo" in server.delete_device.__doc__


def test_navigate_device_preset_output(fake_conn):
    fake_conn({"navigate_device_preset": {"name": "Serum", "preset_index": 2,
                                          "preset_name": "Bass 3", "preset_count": 10}})
    out = call(server.navigate_device_preset, None, 0, 0, "previous")
    assert out == "'Serum' preset 3 of 10: 'Bass 3'"
    assert "VST/AU" in server.navigate_device_preset.__doc__


def test_navigate_device_preset_default_is_current(fake_conn):
    conn = fake_conn()
    call(server.navigate_device_preset, None, 0, 0)
    assert conn.last("navigate_device_preset")["direction"] == "current"


def test_navigate_device_preset_bad_direction(fake_conn):
    conn = fake_conn()
    out = call(server.navigate_device_preset, None, 0, 0, "forward")
    assert out.startswith("Error navigating device presets")
    assert conn.sent == []


# --------------------------------------------------------------------------
# load_instrument_or_effect / load_drum_kit output
# --------------------------------------------------------------------------

def test_load_reports_new_devices(fake_conn):
    fake_conn({"load_browser_item": {
        "loaded": True, "item_name": "Drift", "track_name": "1-MIDI", "uri": "u",
        "new_devices": ["Drift"], "devices_after": ["Drift"], "devices_changed": True}})
    out = call(server.load_instrument_or_effect, None, 1, "u")
    assert out == "Loaded 'Drift' on track 1. New devices: Drift"


def test_load_reports_unchanged_device_list(fake_conn):
    fake_conn({"load_browser_item": {
        "loaded": True, "item_name": "Drift", "new_devices": [],
        "devices_after": ["EQ Eight"], "devices_changed": False}})
    out = call(server.load_instrument_or_effect, None, 1, "u")
    assert out.startswith("Loaded 'Drift' on track 1.")
    assert "may still be in progress" in out
    assert "EQ Eight" in out


def test_load_unchanged_on_empty_track(fake_conn):
    fake_conn({"load_browser_item": {
        "loaded": True, "item_name": "Drift", "new_devices": [],
        "devices_after": [], "devices_changed": False}})
    out = call(server.load_instrument_or_effect, None, 1, "u")
    assert "Devices on track: (none)" in out
    assert not out.endswith("Devices on track: ")


def test_load_replaced_device_same_name(fake_conn):
    fake_conn({"load_browser_item": {
        "loaded": True, "item_name": "Drift", "new_devices": [],
        "devices_after": ["Drift"], "devices_changed": True}})
    out = call(server.load_instrument_or_effect, None, 1, "u")
    assert out == "Loaded 'Drift' on track 1. Devices on track: Drift"


def test_load_from_older_script(fake_conn):
    fake_conn({"load_browser_item": {"loaded": True}})
    out = call(server.load_instrument_or_effect, None, 1, "query:Synths#Drift")
    assert out.startswith("Loaded 'query:Synths#Drift' on track 1.")
    assert "get_track_info" in out


def test_load_failed(fake_conn):
    fake_conn({"load_browser_item": {"loaded": False}})
    out = call(server.load_instrument_or_effect, None, 1, "u")
    assert out == "Failed to load instrument with URI 'u'"


def test_load_drum_kit_reports_devices(fake_conn):
    conn = fake_conn({
        "load_browser_item": [
            {"loaded": True, "item_name": "Drum Rack", "new_devices": ["Drum Rack"],
             "devices_after": ["Drum Rack"], "devices_changed": True},
            {"loaded": True, "item_name": "808 Kit", "new_devices": ["808 Kit"],
             "devices_after": ["808 Kit"], "devices_changed": True},
        ],
        "get_browser_items_at_path": {"items": [
            {"name": "808 Kit", "uri": "kit-uri", "is_loadable": True}]},
    })
    out = call(server.load_drum_kit, None, 0, "rack-uri", "drums/808")
    assert conn.commands() == ["load_browser_item", "get_browser_items_at_path",
                               "load_browser_item"]
    assert conn.last("load_browser_item")["item_uri"] == "kit-uri"
    assert out == "Loaded drum rack and kit '808 Kit' on track 0. New devices: 808 Kit"


# --------------------------------------------------------------------------
# Plumbing
# --------------------------------------------------------------------------

def test_new_modifying_tools_are_recorded():
    assert {"set_device_enabled", "delete_device", "navigate_device_preset"} <= MODIFYING_TOOLS
    assert "get_rack_info" not in MODIFYING_TOOLS


def test_new_param_keys():
    for key in ("chain_index", "chain_device_index", "parameter_name", "direction"):
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
    ("get_rack_info", 10.0),
    ("set_device_enabled", 15.0),
    ("delete_device", 15.0),
    ("navigate_device_preset", 15.0),
])
def test_socket_timeouts(command, expected):
    sock = TimeoutRecordingSocket({"status": "success", "result": {}})
    conn = server.AbletonConnection(host="localhost", port=0, sock=sock)
    conn.send_command(command, {})
    assert sock.timeouts == [expected]


def test_tools_registered():
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    for name in ["get_rack_info", "set_device_enabled", "delete_device",
                 "navigate_device_preset"]:
        assert name in tools
    for name in ["get_device_parameters", "set_device_parameter"]:
        props = tools[name].inputSchema["properties"]
        assert {"chain_index", "chain_device_index"} <= set(props)
    props = tools["set_device_parameter"].inputSchema
    assert "parameter_name" in props["properties"]
    assert "parameter_index" not in props.get("required", [])
