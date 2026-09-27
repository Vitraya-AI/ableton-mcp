"""
Live-side tests for the Live version / API flags in get_script_info and the
developer-only dump_live_api command.

Same setup as test_remote_script_handlers.py: ``_Framework`` is stubbed, the
class is built without ``__init__``, and a fake ``Live`` module is injected
into sys.modules.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

BUNDLED_SCRIPT = (Path(__file__).resolve().parents[1] / "MCP_Server"
                  / "bundled_ableton_remote_script" / "AbletonMCP_init.py")

FLAGS = (
    "track_create_midi_clip", "track_create_audio_clip",
    "clip_slot_create_audio_clip", "song_begin_undo_step",
    "clip_automation_envelope", "automation_envelope_insert_step",
    "envelope_insert_step", "plugin_device_presets", "cue_point_set_name",
)


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
        "ableton_mcp_remote_script_probe_under_test", BUNDLED_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _load_script_module()


def make_instance(script):
    inst = script.AbletonMCP.__new__(script.AbletonMCP)
    inst._song = None
    inst.log_message = lambda *a, **k: None
    inst.show_message = lambda *a, **k: None
    inst.schedule_message = lambda _delay, task: task()
    return inst


def run(inst, command_type, **params):
    return inst._process_command({"type": command_type, "params": params})


# --------------------------------------------------------------------------
# Fake Live module
# --------------------------------------------------------------------------

class FakeApplication(object):
    def get_major_version(self):
        return 11

    def get_minor_version(self):
        return 3

    def get_bugfix_version(self):
        return 42


def _module(name, **attrs):
    mod = types.ModuleType("Live." + name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def fake_live_11():
    """Roughly Live 11.3: no Track.create_midi_clip, no Live.Envelope."""

    class Song(object):
        """This class represents a Live set."""

        class View(object):
            """Song view."""

            @property
            def selected_track(self):
                """The selected track."""

        def __init__(self):
            """__init__( (object)arg1) -> None :\n    Raises an exception."""

        def create_scene(self, index):
            """create_scene( (Song)arg1, (int)arg2) -> Scene"""

        def begin_undo_step(self):
            """begin_undo_step( (Song)arg1) -> None"""

        @property
        def tempo(self):
            """Get/Set the tempo in BPM."""

        def _private_helper(self):
            """Hidden."""

        long_doc = property(lambda self: None, doc="x" * 5000)
        answer = 42

    class CuePoint(object):
        """A locator."""

        # Live 11: Get/Listen only.
        name = property(lambda self: "1", doc="Get/Listen to the name.")

        def jump(self):
            """jump( (CuePoint)arg1) -> None"""

    class Track(object):
        def create_audio_clip(self):
            pass

    class ClipSlot(object):
        def create_audio_clip(self):
            pass

    class Clip(object):
        def automation_envelope(self, parameter):
            pass

    class AutomationEnvelope(object):
        def insert_step(self, time, length, value):
            pass

    class PluginDevice(object):
        presets = property(lambda self: ())

    live = types.ModuleType("Live")
    live.Application = _module(
        "Application", get_application=lambda: FakeApplication())
    live.Song = _module("Song", Song=Song, CuePoint=CuePoint)
    live.Track = _module("Track", Track=Track)
    live.ClipSlot = _module("ClipSlot", ClipSlot=ClipSlot)
    live.Clip = _module("Clip", Clip=Clip, AutomationEnvelope=AutomationEnvelope)
    live.PluginDevice = _module("PluginDevice", PluginDevice=PluginDevice)
    live.not_a_module = 1
    return live


@pytest.fixture
def live(monkeypatch):
    fake = fake_live_11()
    monkeypatch.setitem(sys.modules, "Live", fake)
    return fake


@pytest.fixture
def no_live(monkeypatch):
    monkeypatch.delitem(sys.modules, "Live", raising=False)


# --------------------------------------------------------------------------
# get_script_info
# --------------------------------------------------------------------------

def test_script_info_reports_live_version_and_flags(script, live):
    info = run(make_instance(script), "get_script_info")["result"]
    assert info["live_version"] == {
        "major": 11, "minor": 3, "bugfix": 42, "string": "11.3.42"}
    assert info["live_api"] == {
        "track_create_midi_clip": False,
        "track_create_audio_clip": True,
        "clip_slot_create_audio_clip": True,
        "song_begin_undo_step": True,
        "clip_automation_envelope": True,
        "automation_envelope_insert_step": True,
        "envelope_insert_step": False,
        "plugin_device_presets": True,
        "cue_point_set_name": False,
    }


def test_script_info_flags_follow_the_live_build(script, live):
    live.Track.Track.create_midi_clip = lambda self, start, length: None

    class Envelope(object):
        def insert_step(self, time, length, value):
            pass

    live.Envelope = _module("Envelope", Envelope=Envelope)
    del live.PluginDevice
    cue_point = live.Song.CuePoint
    cue_point.name = property(lambda self: "1", lambda self, value: None)
    flags = run(make_instance(script), "get_script_info")["result"]["live_api"]
    assert flags["track_create_midi_clip"] is True
    assert flags["envelope_insert_step"] is True
    assert flags["plugin_device_presets"] is False
    assert flags["cue_point_set_name"] is True
    assert set(flags) == set(FLAGS)


def test_cue_point_set_name_false_without_cue_point_class(script, live):
    del live.Song.CuePoint
    flags = run(make_instance(script), "get_script_info")["result"]["live_api"]
    assert flags["cue_point_set_name"] is False


def test_script_info_without_live_module(script, no_live):
    response = run(make_instance(script), "get_script_info")
    assert response["status"] == "success"
    assert response["result"]["live_version"] is None
    assert response["result"]["live_api"] == {}


def test_script_info_survives_a_failing_application(script, live):
    def broken():
        raise RuntimeError("no application")

    live.Application.get_application = broken
    response = run(make_instance(script), "get_script_info")
    assert response["status"] == "success"
    assert response["result"]["live_version"] is None
    assert response["result"]["live_api"]["song_begin_undo_step"] is True


# --------------------------------------------------------------------------
# dump_live_api
# --------------------------------------------------------------------------

def test_dump_lists_modules(script, live):
    result = run(make_instance(script), "dump_live_api")["result"]
    assert result["modules"] == [
        "Application", "Clip", "ClipSlot", "PluginDevice", "Song", "Track"]
    assert result["live_version"]["string"] == "11.3.42"


def test_dump_one_module(script, live):
    result = run(make_instance(script), "dump_live_api", module="Song")["result"]
    assert result["module"] == "Song"
    assert result["live_version"]["major"] == 11

    classes = result["classes"]
    assert set(classes) == {"Song", "Song.View", "CuePoint"}

    song = classes["Song"]
    assert song["doc"] == "This class represents a Live set."
    members = song["members"]
    assert members["create_scene"] == {
        "kind": "method", "doc": "create_scene( (Song)arg1, (int)arg2) -> Scene"}
    assert members["tempo"] == {"kind": "property", "doc": "Get/Set the tempo in BPM."}
    assert members["View"] == {"kind": "class", "doc": "Song view."}
    assert members["answer"] == {"kind": "attribute", "doc": None}
    assert members["__init__"]["kind"] == "method"
    assert members["__init__"]["doc"].startswith("__init__( (object)arg1)")
    assert "_private_helper" not in members
    assert not [name for name in members
                if name.startswith("_") and name != "__init__"]
    assert len(members["long_doc"]["doc"]) == 2000

    view = classes["Song.View"]
    assert view["members"]["selected_track"]["kind"] == "property"
    assert classes["CuePoint"]["members"]["jump"]["kind"] == "method"


def test_dump_unknown_module(script, live):
    for name in ("Nope", "not_a_module", "_private"):
        response = run(make_instance(script), "dump_live_api", module=name)
        assert response["status"] == "error"
        assert response["code"] == "invalid_value"
        assert response["message"] == "Unknown Live module: %s" % name


def test_dump_without_live_module(script, no_live):
    response = run(make_instance(script), "dump_live_api", module="Song")
    assert response["status"] == "error"
    assert response["code"] == "internal_error"
    assert response["message"] == "Live module unavailable"


def test_dump_is_a_read_command_and_advertised(script):
    inst = make_instance(script)
    assert "dump_live_api" in inst._read_handlers({})
    assert "dump_live_api" not in inst._main_thread_handlers({})
    assert "dump_live_api" in script.SCRIPT_CAPABILITIES
