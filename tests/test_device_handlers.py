"""
Live-side tests for the device and rack commands (Remote Script 1.11.0):
chain addressing, get_rack_info, get_device_parameters value_items,
set_device_parameter by name, set_device_enabled, delete_device,
navigate_device_preset, and load_browser_item waiting for the new device.

Same setup as test_arrangement_handlers.py: ``_Framework`` is stubbed, the
class is built without ``__init__``, and schedule_message runs the task
immediately. Writes Live applies on its next tick (the "Device On" value, the
selected preset, a loaded device) stay pending until a task scheduled with a
delay of 1 or more runs.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

BUNDLED_SCRIPT = (Path(__file__).resolve().parents[1] / "MCP_Server"
                  / "bundled_ableton_remote_script" / "AbletonMCP_init.py")


def _load_script_module():
    framework = types.ModuleType("_Framework")
    control_surface_mod = types.ModuleType("_Framework.ControlSurface")

    class _StubControlSurface(object):
        def __init__(self, *args, **kwargs):
            pass

    control_surface_mod.ControlSurface = _StubControlSurface
    framework.ControlSurface = control_surface_mod
    sys.modules.setdefault("_Framework", framework)
    sys.modules.setdefault("_Framework.ControlSurface", control_surface_mod)

    spec = importlib.util.spec_from_file_location(
        "ableton_mcp_remote_script_devices_under_test", BUNDLED_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _load_script_module()


# --------------------------------------------------------------------------
# Fake Live object model
# --------------------------------------------------------------------------

class FakeParam(object):
    def __init__(self, name, value=0.0, min=0.0, max=1.0, original_name=None,
                 is_quantized=False, items=None, deferred=False):
        self.name = name
        self.original_name = original_name if original_name is not None else name
        self._value = value
        self.min = min
        self.max = max
        self.is_quantized = is_quantized
        self._items = items or []
        self.deferred = deferred
        self._pending = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.deferred:
            self._pending = value
        else:
            self._value = value

    def settle(self):
        if self._pending is not None:
            self._value = self._pending
            self._pending = None

    @property
    def value_items(self):
        if not self.is_quantized:
            raise RuntimeError("value_items is only available for quantized parameters")
        return tuple(self._items)


def device_on(deferred=True):
    return FakeParam("Device On", 1.0, 0.0, 1.0, is_quantized=True,
                     items=["Off", "On"], deferred=deferred)


class FakeDevice(object):
    can_have_chains = False
    can_have_drum_pads = False

    def __init__(self, name="Operator", class_name="Operator", params=None, live_type=1):
        self.name = name
        self.class_name = class_name
        self.class_display_name = class_name
        self.type = live_type  # Live.Device.DeviceType: 1 instrument, 2 audio effect, 4 MIDI effect
        self.parameters = [device_on()] + list(params or [])

    @property
    def is_active(self):
        return self.parameters[0].value == self.parameters[0].max

    def all_params(self):
        return list(self.parameters)


class FakeChain(object):
    def __init__(self, name, devices=None):
        self.name = name
        self.devices = list(devices or [])
        self.mute = False
        self.solo = False

    def delete_device(self, index):
        if index < 0 or index >= len(self.devices):
            raise RuntimeError("bad index")
        del self.devices[index]


class FakeRack(FakeDevice):
    can_have_chains = True

    def __init__(self, name="Instrument Rack", chains=None, macro_count=8):
        super(FakeRack, self).__init__(
            name, "InstrumentGroupDevice",
            [FakeParam("Macro %d" % (i + 1), float(i), 0.0, 127.0) for i in range(8)])
        self.chains = list(chains or [])
        self.visible_macro_count = macro_count


class FakeDrumPad(object):
    def __init__(self, note, name, chains=None):
        self.note = note
        self.name = name
        self.chains = list(chains or [])
        self.mute = False
        self.solo = False


class FakeDrumRack(FakeRack):
    can_have_drum_pads = True

    def __init__(self, name="Drum Rack"):
        kick = FakeChain("Kick", [FakeDevice("Simpler", "OriginalSimpler")])
        snare = FakeChain("Snare", [FakeDevice("Simpler", "OriginalSimpler")])
        # rack.chains lists the pads' chains, in Live's order (not note order).
        super(FakeDrumRack, self).__init__(name, [snare, kick])
        self.class_name = "DrumGroupDevice"
        self.drum_pads = [FakeDrumPad(n, "Pad %d" % n) for n in range(36, 40)]
        self.drum_pads[0] = FakeDrumPad(36, "Kick", [kick])
        self.drum_pads[2] = FakeDrumPad(38, "Snare", [snare])
        self.drum_pads[2].mute = True


class FakePlugin(FakeDevice):
    def __init__(self, name="Serum", presets=None, selected=0):
        super(FakePlugin, self).__init__(name, "PluginDevice")
        self.presets = list(presets if presets is not None else ["Init", "Bass", "Lead"])
        self._selected = selected
        self._pending_preset = None

    @property
    def selected_preset_index(self):
        return self._selected

    @selected_preset_index.setter
    def selected_preset_index(self, value):
        self._pending_preset = value

    def settle(self):
        if self._pending_preset is not None:
            self._selected = self._pending_preset
            self._pending_preset = None


class FakeTrack(object):
    def __init__(self, name="Track", devices=None):
        self.name = name
        self.devices = list(devices or [])

    def delete_device(self, index):
        if index < 0 or index >= len(self.devices):
            raise RuntimeError("bad index")
        del self.devices[index]


def _walk(devices):
    for device in devices:
        yield device
        for chain in getattr(device, "chains", []) or []:
            for inner in _walk(chain.devices):
                yield inner


class FakeSong(object):
    def __init__(self, tracks):
        self.tracks = tracks
        self.view = types.SimpleNamespace(selected_track=None)
        self.undo_steps = []
        self.events = []
        self.pending_loads = []

    def begin_undo_step(self):
        self.undo_steps.append("begin")
        self.events.append("begin")

    def end_undo_step(self):
        self.undo_steps.append("end")
        self.events.append("end")

    def tick(self):
        self.events.append("tick")
        for device in _walk([d for t in self.tracks for d in t.devices]):
            for param in device.parameters:
                param.settle()
            if hasattr(device, "settle"):
                device.settle()
        still_pending = []
        for ticks_left, track, device in self.pending_loads:
            if ticks_left <= 1:
                track.devices.append(device)
            else:
                still_pending.append((ticks_left - 1, track, device))
        self.pending_loads = still_pending


class FakeBrowser(object):
    """load_item adds the device to the selected track `delay` ticks later."""

    def __init__(self, song, device, delay=1):
        self.song = song
        self.device = device
        self.delay = delay
        self.loaded = []

    def load_item(self, item):
        self.loaded.append(item)
        if self.device is not None:
            self.song.pending_loads.append(
                (self.delay, self.song.view.selected_track, self.device))


def make_instance(script, song, browser=None):
    inst = script.AbletonMCP.__new__(script.AbletonMCP)
    inst._song = song
    inst.log_message = lambda *a, **k: None
    inst.show_message = lambda *a, **k: None
    inst.application = lambda: types.SimpleNamespace(browser=browser)
    inst._find_browser_item_by_uri = (
        lambda _browser, uri: types.SimpleNamespace(name="Item " + uri, uri=uri))

    def schedule_message(delay, task):
        if delay >= 1:
            song.tick()
        task()

    inst.schedule_message = schedule_message
    return inst


def run(inst, command_type, **params):
    return inst._process_command({"type": command_type, "params": params})


def ok(response):
    assert response["status"] == "success", response
    return response["result"]


def error_code(response):
    assert response["status"] == "error", response
    return response["code"]


def rack_song():
    """Track 0: [Operator, Instrument Rack(Bass: [Wavetable, Saturator], Lead: [Analog]),
    Drum Rack, Serum]."""
    wavetable = FakeDevice("Wavetable", "InstrumentVector", [
        FakeParam("Filter Freq", 0.5),
        FakeParam("Osc Type", 1.0, 0.0, 3.0, is_quantized=True,
                  items=["Sine", "Saw", "Square", "Noise"]),
    ])
    saturator = FakeDevice("Saturator", "Saturator", [FakeParam("Drive", 0.2)], live_type=2)
    analog = FakeDevice("Analog", "UltraAnalog")
    rack = FakeRack("Keys Rack", [FakeChain("Bass", [wavetable, saturator]),
                                  FakeChain("Lead", [analog])], macro_count=4)
    operator = FakeDevice("Operator", "Operator", [
        FakeParam("Volume", 0.5),
        FakeParam("Filter Freq", 0.3),
        FakeParam("filter freq", 0.4, original_name="Filter Freq B"),
        FakeParam("Algorithm", 0.0, 0.0, 10.0, is_quantized=True,
                  items=[str(i) for i in range(11)]),
    ])
    return FakeSong([FakeTrack("Synths", [operator, rack, FakeDrumRack(), FakePlugin()])])


# --------------------------------------------------------------------------
# Routing and capabilities
# --------------------------------------------------------------------------

def test_new_commands_are_routed_and_advertised(script):
    inst = make_instance(script, rack_song())
    reads = set(inst._read_handlers({}))
    writes = set(inst._main_thread_handlers({}))
    assert "get_rack_info" in reads
    assert {"set_device_enabled", "delete_device", "navigate_device_preset"} <= writes
    for name in ("get_rack_info", "set_device_enabled", "delete_device",
                 "navigate_device_preset", "device_chain_param", "parameter_name_param"):
        assert name in script.SCRIPT_CAPABILITIES
    undoable = script.AbletonMCP._UNDOABLE_COMMANDS
    assert {"set_device_enabled", "delete_device", "set_device_parameter"} <= undoable
    assert "navigate_device_preset" not in undoable


# --------------------------------------------------------------------------
# Device addressing
# --------------------------------------------------------------------------

def test_chain_addressing(script):
    inst = make_instance(script, rack_song())
    device = ok(run(inst, "get_device_parameters", track_index=0, device_index=1,
                    chain_index=0, chain_device_index=1))["device"]
    assert device["name"] == "Saturator"
    assert device["index"] == 1
    # chain_device_index defaults to 0.
    device = ok(run(inst, "get_device_parameters", track_index=0, device_index=1,
                    chain_index=1))["device"]
    assert device["name"] == "Analog"
    top = ok(run(inst, "get_device_parameters", track_index=0, device_index=1))["device"]
    assert top["name"] == "Keys Rack"


@pytest.mark.parametrize("params,code", [
    ({"device_index": 9}, "device_index_out_of_range"),
    ({"device_index": 1, "chain_device_index": 1}, "invalid_value"),
    ({"device_index": 0, "chain_index": 0}, "not_a_rack"),
    ({"device_index": 1, "chain_index": 2}, "chain_index_out_of_range"),
    ({"device_index": 1, "chain_index": 1, "chain_device_index": 1},
     "device_index_out_of_range"),
    ({"device_index": 0, "track_index": 4}, "track_index_out_of_range"),
])
def test_device_addressing_errors(script, params, code):
    params = dict({"track_index": 0}, **params)
    for command in ("get_device_parameters", "get_rack_info", "set_device_enabled",
                    "delete_device", "navigate_device_preset", "set_device_parameter"):
        extra = {"enabled": False, "direction": "next", "parameter_index": 1, "value": 0.0}
        song = rack_song()
        response = run(make_instance(script, song), command, **dict(extra, **params))
        assert error_code(response) == code, command
        assert len(song.tracks[0].devices) == 4


# --------------------------------------------------------------------------
# get_device_parameters
# --------------------------------------------------------------------------

def test_get_device_parameters_value_items_only_for_quantized(script):
    device = ok(run(make_instance(script, rack_song()), "get_device_parameters",
                    track_index=0, device_index=0))["device"]
    by_name = {p["name"]: p for p in device["parameters"]}
    assert by_name["Algorithm"]["value_items"] == [str(i) for i in range(11)]
    assert by_name["Device On"]["value_items"] == ["Off", "On"]
    assert "value_items" not in by_name["Volume"]
    assert len(device["parameters"]) == 5


def test_snapshot_devices_do_not_carry_value_items(script):
    inst = make_instance(script, rack_song())
    device = inst._serialize_device(inst._song.tracks[0].devices[0], 0)
    assert all("value_items" not in p for p in device["parameters"])


# --------------------------------------------------------------------------
# get_rack_info
# --------------------------------------------------------------------------

def test_get_rack_info_instrument_rack(script):
    info = ok(run(make_instance(script, rack_song()), "get_rack_info",
                  track_index=0, device_index=1))
    assert (info["name"], info["class_name"], info["is_drum_rack"]) == (
        "Keys Rack", "InstrumentGroupDevice", False)
    assert (info["chain_index"], info["chain_device_index"]) == (None, None)
    assert [m["index"] for m in info["macros"]] == [1, 2, 3, 4]
    assert info["macros"][0] == {"index": 1, "name": "Macro 1", "value": 0.0,
                                 "min": 0.0, "max": 127.0}
    assert [c["name"] for c in info["chains"]] == ["Bass", "Lead"]
    bass = info["chains"][0]
    assert bass["devices"][1] == {"index": 1, "name": "Saturator", "class_name": "Saturator",
                                  "type": "audio_effect", "is_active": True,
                                  "is_rack": False}
    assert info["drum_pads"] == []


def test_get_rack_info_drum_rack_lists_filled_pads(script):
    info = ok(run(make_instance(script, rack_song()), "get_rack_info",
                  track_index=0, device_index=2))
    assert info["is_drum_rack"] is True
    assert [c["name"] for c in info["chains"]] == ["Snare", "Kick"]
    assert info["drum_pads"] == [
        {"note": 36, "name": "Kick", "mute": False, "solo": False, "chain_indices": [1]},
        {"note": 38, "name": "Snare", "mute": True, "solo": False, "chain_indices": [0]},
    ]


def test_get_rack_info_nested_rack(script):
    inner = FakeRack("Inner", [FakeChain("A", [FakeDevice("Simpler")])])
    outer = FakeRack("Outer", [FakeChain("X", [FakeDevice("EQ"), inner])])
    song = FakeSong([FakeTrack("T", [outer])])
    info = ok(run(make_instance(script, song), "get_rack_info", track_index=0,
                  device_index=0, chain_index=0, chain_device_index=1))
    assert info["name"] == "Inner"
    assert (info["chain_index"], info["chain_device_index"]) == (0, 1)
    outer_info = ok(run(make_instance(script, song), "get_rack_info",
                        track_index=0, device_index=0))
    assert outer_info["chains"][0]["devices"][1]["is_rack"] is True


def test_get_rack_info_not_a_rack(script):
    for index in (0, 3):
        response = run(make_instance(script, rack_song()), "get_rack_info",
                       track_index=0, device_index=index)
        assert error_code(response) == "not_a_rack"


# --------------------------------------------------------------------------
# set_device_parameter
# --------------------------------------------------------------------------

def test_set_parameter_by_name_is_case_insensitive(script):
    song = rack_song()
    result = ok(run(make_instance(script, song), "set_device_parameter", track_index=0,
                    device_index=0, parameter_name="VOLUME", value=0.9))
    assert result["parameter_index"] == 1
    assert (result["name"], result["old_value"], result["value"]) == ("Volume", 0.5, 0.9)
    assert song.undo_steps == ["begin", "end"]


def test_set_parameter_by_index_still_works(script):
    song = rack_song()
    result = ok(run(make_instance(script, song), "set_device_parameter", track_index=0,
                    device_index=0, parameter_index=4, value=3.0))
    assert (result["parameter_index"], result["name"], result["value"]) == (4, "Algorithm", 3.0)


def test_set_parameter_in_a_chain(script):
    song = rack_song()
    result = ok(run(make_instance(script, song), "set_device_parameter", track_index=0,
                    device_index=1, chain_index=0, chain_device_index=1,
                    parameter_name="drive", value=0.7))
    assert result["parameter_index"] == 1
    saturator = song.tracks[0].devices[1].chains[0].devices[1]
    assert saturator.parameters[1].value == 0.7


def test_set_parameter_name_not_found_lists_names(script):
    response = run(make_instance(script, rack_song()), "set_device_parameter",
                   track_index=0, device_index=0, parameter_name="Cutoff", value=0.1)
    assert error_code(response) == "parameter_not_found"
    assert "Volume" in response["message"] and "Algorithm" in response["message"]


def test_set_parameter_name_not_found_lists_at_most_20_names(script):
    device = FakeDevice("Big", "Big", [FakeParam("P%d" % i) for i in range(30)])
    response = run(make_instance(script, FakeSong([FakeTrack("T", [device])])),
                   "set_device_parameter", track_index=0, device_index=0,
                   parameter_name="nope", value=0.1)
    assert error_code(response) == "parameter_not_found"
    assert "P18" in response["message"]
    assert "P19" not in response["message"]


def test_set_parameter_ambiguous_name(script):
    song = rack_song()
    response = run(make_instance(script, song), "set_device_parameter", track_index=0,
                   device_index=0, parameter_name="filter freq", value=0.1)
    assert error_code(response) == "invalid_value"
    assert "[2, 3]" in response["message"]
    assert song.tracks[0].devices[0].parameters[2].value == 0.3


@pytest.mark.parametrize("params", [
    {"parameter_index": 1, "parameter_name": "Volume"},
    {},
])
def test_set_parameter_needs_exactly_one_of_index_and_name(script, params):
    response = run(make_instance(script, rack_song()), "set_device_parameter",
                   track_index=0, device_index=0, value=0.1, **params)
    assert error_code(response) == "invalid_value"


def test_set_parameter_errors_keep_their_codes(script):
    inst = make_instance(script, rack_song())
    response = run(inst, "set_device_parameter", track_index=0, device_index=0,
                   parameter_index=9, value=0.1)
    assert error_code(response) == "parameter_index_out_of_range"
    response = run(inst, "set_device_parameter", track_index=0, device_index=0,
                   parameter_name="Volume", value=5.0)
    assert error_code(response) == "parameter_value_out_of_range"


# --------------------------------------------------------------------------
# set_device_enabled
# --------------------------------------------------------------------------

def test_set_device_enabled_reads_back_after_the_tick(script):
    song = rack_song()
    inst = make_instance(script, song)
    result = ok(run(inst, "set_device_enabled", track_index=0, device_index=0, enabled=False))
    assert result == {"name": "Operator", "enabled": False, "is_active": False}
    assert song.events == ["begin", "tick", "end"]
    result = ok(run(inst, "set_device_enabled", track_index=0, device_index=0, enabled=True))
    assert result == {"name": "Operator", "enabled": True, "is_active": True}


def test_set_device_enabled_in_a_chain(script):
    song = rack_song()
    result = ok(run(make_instance(script, song), "set_device_enabled", track_index=0,
                    device_index=1, chain_index=1, enabled=False))
    assert result["name"] == "Analog"
    assert song.tracks[0].devices[1].chains[1].devices[0].is_active is False


def test_set_device_enabled_uses_the_original_parameter_name(script):
    device = FakeDevice("Renamed")
    device.parameters[0].name = "Power"   # the user renamed it; original_name stays
    song = FakeSong([FakeTrack("T", [device])])
    result = ok(run(make_instance(script, song), "set_device_enabled",
                    track_index=0, device_index=0, enabled=False))
    assert result["enabled"] is False


def test_set_device_enabled_without_device_on(script):
    device = FakeDevice("Odd")
    device.parameters[0] = FakeParam("Gain", 0.5, original_name="Gain")
    response = run(make_instance(script, FakeSong([FakeTrack("T", [device])])),
                   "set_device_enabled", track_index=0, device_index=0, enabled=False)
    assert error_code(response) == "not_supported"
    assert device.parameters[0].value == 0.5


# --------------------------------------------------------------------------
# delete_device
# --------------------------------------------------------------------------

def test_delete_device_on_the_track(script):
    song = rack_song()
    result = ok(run(make_instance(script, song), "delete_device", track_index=0,
                    device_index=0))
    assert result == {"deleted": "Operator", "track_index": 0, "device_index": 0,
                      "chain_index": None, "chain_device_index": None}
    assert [d.name for d in song.tracks[0].devices] == ["Keys Rack", "Drum Rack", "Serum"]
    assert song.undo_steps == ["begin", "end"]


def test_delete_device_in_a_chain(script):
    song = rack_song()
    result = ok(run(make_instance(script, song), "delete_device", track_index=0,
                    device_index=1, chain_index=0, chain_device_index=1))
    assert result["deleted"] == "Saturator"
    assert (result["chain_index"], result["chain_device_index"]) == (0, 1)
    assert [d.name for d in song.tracks[0].devices[1].chains[0].devices] == ["Wavetable"]
    assert len(song.tracks[0].devices) == 4


# --------------------------------------------------------------------------
# navigate_device_preset
# --------------------------------------------------------------------------

def _preset(inst, direction, **extra):
    return run(inst, "navigate_device_preset", track_index=0, device_index=3,
               direction=direction, **extra)


def test_navigate_presets_reads_back_after_the_tick(script):
    song = rack_song()
    inst = make_instance(script, song)
    assert ok(_preset(inst, "next")) == {
        "name": "Serum", "preset_index": 1, "preset_name": "Bass", "preset_count": 3}
    assert ok(_preset(inst, "next"))["preset_name"] == "Lead"
    assert ok(_preset(inst, "next"))["preset_index"] == 2     # clamped at the end
    assert ok(_preset(inst, "current"))["preset_name"] == "Lead"
    assert ok(_preset(inst, "previous"))["preset_index"] == 1
    assert song.undo_steps == []
    assert "tick" in song.events


def test_navigate_presets_clamps_at_the_start(script):
    inst = make_instance(script, rack_song())
    assert ok(_preset(inst, "previous"))["preset_index"] == 0


def test_navigate_presets_errors(script):
    inst = make_instance(script, rack_song())
    assert error_code(_preset(inst, "sideways")) == "invalid_value"
    response = run(inst, "navigate_device_preset", track_index=0, device_index=0,
                   direction="next")
    assert error_code(response) == "not_supported"
    assert "'Operator' has no presets" in response["message"]
    empty = FakePlugin("Empty", presets=[])
    response = run(make_instance(script, FakeSong([FakeTrack("T", [empty])])),
                   "navigate_device_preset", track_index=0, device_index=0,
                   direction="next")
    assert error_code(response) == "not_supported"


def test_navigate_presets_in_a_chain(script):
    rack = FakeRack("FX", [FakeChain("A", [FakePlugin("Valhalla", ["Hall", "Plate"])])])
    song = FakeSong([FakeTrack("T", [rack])])
    result = ok(run(make_instance(script, song), "navigate_device_preset", track_index=0,
                    device_index=0, chain_index=0, direction="next"))
    assert (result["name"], result["preset_name"]) == ("Valhalla", "Plate")


# --------------------------------------------------------------------------
# load_browser_item / load_instrument_or_effect
# --------------------------------------------------------------------------

@pytest.mark.parametrize("command,uri_key", [
    ("load_browser_item", "item_uri"),
    ("load_instrument_or_effect", "uri"),
])
def test_load_waits_for_the_new_device(script, command, uri_key):
    track = FakeTrack("Keys", [FakeDevice("Reverb", "Reverb")])
    song = FakeSong([track])
    browser = FakeBrowser(song, FakeDevice("Reverb", "Reverb"), delay=3)
    params = {"track_index": 0, uri_key: "query:Reverb"}
    result = ok(run(make_instance(script, song, browser), command, **params))
    assert result == {
        "loaded": True, "item_name": "Item query:Reverb", "track_name": "Keys",
        "uri": "query:Reverb", "new_devices": ["Reverb"],
        "devices_after": ["Reverb", "Reverb"], "devices_changed": True}
    assert song.events.count("tick") == 3
    assert song.view.selected_track is track
    assert song.undo_steps == ["begin", "end"]


def test_load_that_never_changes_the_devices(script):
    song = FakeSong([FakeTrack("Keys", [FakeDevice("Operator")])])
    browser = FakeBrowser(song, None)
    result = ok(run(make_instance(script, song, browser), "load_browser_item",
                    track_index=0, item_uri="query:Nothing"))
    assert result["devices_changed"] is False
    assert result["new_devices"] == []
    assert result["devices_after"] == ["Operator"]
    assert song.events.count("tick") == 30


# --------------------------------------------------------------------------
# Device type from Live's Device.type (1.11.1)
# --------------------------------------------------------------------------

class _LiveEnumValue(int):
    """Boost.Python enum values are ints with a .name."""

    def __new__(cls, value, name):
        obj = int.__new__(cls, value)
        obj.name = name
        return obj


@pytest.mark.parametrize("live_type, expected", [
    (_LiveEnumValue(1, "instrument"), "instrument"),
    (_LiveEnumValue(2, "audio_effect"), "audio_effect"),
    (_LiveEnumValue(4, "midi_effect"), "midi_effect"),
    (_LiveEnumValue(0, "undefined"), "unknown"),
    (2, "audio_effect"),          # plain int, no .name
    (None, "unknown"),
])
def test_device_type_comes_from_live(script, live_type, expected):
    """Chain devices such as Utility reported "unknown": the old code guessed
    from class names, which Live's names don't follow."""
    import types as _types
    device = _types.SimpleNamespace(can_have_drum_pads=False, can_have_chains=False,
                                    type=live_type, class_name="StereoGain",
                                    class_display_name="Utility")
    inst = script.AbletonMCP.__new__(script.AbletonMCP)
    assert inst._get_device_type(device) == expected


def test_racks_and_drum_racks_keep_their_labels(script):
    import types as _types
    inst = script.AbletonMCP.__new__(script.AbletonMCP)
    drum = _types.SimpleNamespace(can_have_drum_pads=True, can_have_chains=True, type=1)
    rack = _types.SimpleNamespace(can_have_drum_pads=False, can_have_chains=True, type=2)
    assert inst._get_device_type(drum) == "drum_machine"
    assert inst._get_device_type(rack) == "rack"
