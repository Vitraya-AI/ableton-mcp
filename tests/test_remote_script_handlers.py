"""
Live-side tests for the command handlers: routing, validation, error codes,
note editing, mixer, scenes and the browser tree depth.

The Remote Script runs inside Live's interpreter, so ``_Framework`` is stubbed,
the class is built without ``__init__`` (which would open a socket), and the
Live object model is replaced with small fakes. schedule_message runs the task
immediately, standing in for Live's main thread.
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
        "ableton_mcp_remote_script_handlers_under_test", BUNDLED_SCRIPT)
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
    def __init__(self, name="Param", value=0.0, min=0.0, max=1.0):
        self.name = name
        self.value = value
        self.min = min
        self.max = max


class FakeMixer(object):
    def __init__(self, sends=1):
        self.volume = FakeParam("Volume", 0.85, 0.0, 1.0)
        self.panning = FakeParam("Pan", 0.0, -1.0, 1.0)
        self.sends = [FakeParam("Send %d" % i, 0.0, 0.0, 1.0) for i in range(sends)]


class FakeNote(object):
    def __init__(self, note_id, pitch, start_time, duration=0.25, velocity=100):
        self.note_id = note_id
        self.pitch = pitch
        self.start_time = start_time
        self.duration = duration
        self.velocity = velocity
        self.mute = False
        self.probability = 1.0
        self.velocity_deviation = 0.0
        self.release_velocity = 64.0


class FakeClip(object):
    is_midi_clip = True

    def __init__(self, notes=None, length=4.0, name="Clip"):
        self.notes = list(notes or [])
        self.length = length
        self.name = name
        self.applied = None
        self.set_notes_calls = []

    def _in(self, n, from_pitch, pitch_span, from_time, time_span):
        return (from_pitch <= n.pitch < from_pitch + pitch_span
                and from_time <= n.start_time < from_time + time_span)

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        return [n for n in self.notes
                if self._in(n, from_pitch, pitch_span, from_time, time_span)]

    def remove_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        self.notes = [n for n in self.notes
                      if not self._in(n, from_pitch, pitch_span, from_time, time_span)]

    def apply_note_modifications(self, vector):
        self.applied = vector

    def set_notes(self, notes):
        self.set_notes_calls.append(notes)


class FakeClipSlot(object):
    def __init__(self, clip=None):
        self.clip = clip

    @property
    def has_clip(self):
        return self.clip is not None

    def duplicate_clip_to(self, other):
        other.clip = FakeClip(list(self.clip.notes), self.clip.length, self.clip.name)


class FakeTrack(object):
    def __init__(self, name="Track", slots=4, can_be_armed=True):
        self.name = name
        self.clip_slots = [FakeClipSlot() for _ in range(slots)]
        self.mixer_device = FakeMixer()
        self.devices = []
        self.mute = False
        self.solo = False
        self.can_be_armed = can_be_armed
        self._arm = False
        self.is_foldable = False
        self.is_grouped = False
        self.has_audio_input = False
        self.has_midi_input = True

    @property
    def arm(self):
        if not self.can_be_armed:
            raise RuntimeError("Master and Return Tracks have no 'Arm' state!")
        return self._arm

    @arm.setter
    def arm(self, value):
        if not self.can_be_armed:
            raise RuntimeError("Master and Return Tracks have no 'Arm' state!")
        self._arm = value


class FakeScene(object):
    def __init__(self, name=""):
        self.name = name
        self.fired = False

    def fire(self):
        self.fired = True


class FakeSong(object):
    def __init__(self, tracks=2, scenes=2):
        self.tracks = [FakeTrack("Track %d" % i) for i in range(tracks)]
        self.return_tracks = []
        self.scenes = [FakeScene("Scene %d" % i) for i in range(scenes)]
        self.master_track = types.SimpleNamespace(mixer_device=FakeMixer(sends=0))
        self.tempo = 120.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.can_undo = True
        self.can_redo = False
        self.undo_calls = 0
        self.undo_steps = []

    def begin_undo_step(self):
        self.undo_steps.append("begin")

    def end_undo_step(self):
        self.undo_steps.append("end")

    def delete_track(self, index):
        del self.tracks[index]

    def create_scene(self, index):
        scene = FakeScene("")
        if index == -1:
            self.scenes.append(scene)
        else:
            self.scenes.insert(index, scene)

    def delete_scene(self, index):
        del self.scenes[index]

    def undo(self):
        self.undo_calls += 1


def make_instance(script, song=None, application=None):
    inst = script.AbletonMCP.__new__(script.AbletonMCP)
    inst._song = song or FakeSong()
    inst.application = lambda: application
    inst.log_message = lambda *a, **k: None
    inst.show_message = lambda *a, **k: None
    inst.schedule_message = lambda _delay, task: task()
    return inst


def run(inst, command_type, **params):
    return inst._process_command({"type": command_type, "params": params})


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

# Every command the fork routed before the dispatch table refactor.
PREVIOUSLY_ROUTED = [
    "add_notes_to_clip", "clear_notes_from_clip", "create_audio_clip",
    "create_audio_track", "create_clip", "create_locator", "create_midi_track",
    "delete_clip", "drain_passive_events", "duplicate_session_clip_to_arrangement",
    "fire_clip", "get_arrangement_clips", "get_browser_item",
    "get_browser_items_at_path", "get_browser_tree", "get_clip_notes",
    "get_device_parameters", "get_script_info", "get_session_info",
    "get_session_snapshot", "get_track_info", "inspect_rack", "load_browser_item",
    "load_instrument_or_effect", "map_rack_magnitude", "set_arrangement_clip_name",
    "set_clip_name", "set_current_song_time", "set_device_parameter", "set_tempo",
    "set_track_name", "start_playback", "stop_clip", "stop_playback",
    "switch_to_arrangement_view",
]


def _routed(inst):
    return set(inst._read_handlers({})) | set(inst._main_thread_handlers({}))


def test_every_previously_routed_command_is_still_routed(script):
    missing = set(PREVIOUSLY_ROUTED) - _routed(make_instance(script))
    assert not missing


def test_every_advertised_capability_is_routed(script):
    """The handshake advertises SCRIPT_CAPABILITIES; each must be callable."""
    advertised = set(script.SCRIPT_CAPABILITIES) - {"error_codes"}
    assert not advertised - _routed(make_instance(script))


def test_commands_that_modify_live_run_on_the_main_thread(script):
    inst = make_instance(script)
    reads = set(inst._read_handlers({}))
    for command in ("set_track_volume", "modify_clip_notes", "create_scene",
                    "delete_track", "undo", "set_device_parameter"):
        assert command not in reads


def test_unknown_command_has_code(script):
    response = run(make_instance(script), "no_such_command")
    assert response["status"] == "error"
    assert response["code"] == "unknown_command"


# --------------------------------------------------------------------------
# Error codes
# --------------------------------------------------------------------------

@pytest.mark.parametrize("command, params, code", [
    ("set_track_mute", {"track_index": 9, "value": True}, "track_index_out_of_range"),
    ("set_track_volume", {"track_index": 0, "value": 1.5}, "value_out_of_range"),
    ("set_track_panning", {"track_index": 0, "value": -2.0}, "value_out_of_range"),
    ("set_send_level", {"track_index": 0, "send_index": 5, "value": 0.5},
     "send_index_out_of_range"),
    ("fire_scene", {"scene_index": 7}, "scene_index_out_of_range"),
    ("modify_clip_notes", {"track_index": 0, "clip_index": 0, "notes": []},
     "clip_slot_empty"),
    ("remove_notes_from_clip", {"track_index": 0, "clip_index": 99},
     "clip_index_out_of_range"),
    # Existing handlers raise plain exceptions; codes come from the message.
    ("set_track_name", {"track_index": 42, "name": "x"}, "track_index_out_of_range"),
    ("fire_clip", {"track_index": 0, "clip_index": 0}, "clip_slot_empty"),
])
def test_failures_carry_machine_readable_codes(script, command, params, code):
    response = run(make_instance(script), command, **params)
    assert response["status"] == "error"
    assert response["code"] == code


def test_device_parameter_out_of_range_is_rejected_not_clamped(script):
    song = FakeSong()
    param = FakeParam("Cutoff", 0.5, 0.0, 1.0)
    song.tracks[0].devices = [types.SimpleNamespace(name="Filter", parameters=[param])]
    response = run(make_instance(script, song), "set_device_parameter",
                   track_index=0, device_index=0, parameter_index=0, value=3.0)
    assert response["code"] == "parameter_value_out_of_range"
    assert param.value == 0.5


def test_device_parameter_in_range_is_set(script):
    song = FakeSong()
    param = FakeParam("Cutoff", 0.5, 0.0, 1.0)
    song.tracks[0].devices = [types.SimpleNamespace(name="Filter", parameters=[param])]
    response = run(make_instance(script, song), "set_device_parameter",
                   track_index=0, device_index=0, parameter_index=0, value=0.25)
    assert response["status"] == "success"
    assert response["result"]["old_value"] == 0.5
    assert param.value == 0.25


# --------------------------------------------------------------------------
# Note editing
# --------------------------------------------------------------------------

def _song_with_clip(notes, length=8.0):
    song = FakeSong()
    song.tracks[0].clip_slots[0].clip = FakeClip(notes, length)
    return song


def test_modify_clip_notes_edits_matching_ids_in_place(script):
    notes = [FakeNote(1, 36, 0.0), FakeNote(2, 38, 1.0)]
    song = _song_with_clip(notes)
    response = run(make_instance(script, song), "modify_clip_notes",
                   track_index=0, clip_index=0,
                   notes=[{"note_id": 2, "velocity": 64, "probability": 0.5}])
    assert response["status"] == "success"
    assert response["result"]["modified_count"] == 1
    clip = song.tracks[0].clip_slots[0].clip
    assert (notes[1].velocity, notes[1].probability) == (64, 0.5)
    assert notes[0].velocity == 100
    # The vector Live handed out goes back, not a rebuilt list.
    assert [n.note_id for n in clip.applied] == [1, 2]


def test_modify_clip_notes_rejects_unknown_ids_without_applying(script):
    song = _song_with_clip([FakeNote(1, 36, 0.0)])
    response = run(make_instance(script, song), "modify_clip_notes",
                   track_index=0, clip_index=0, notes=[{"note_id": 99, "velocity": 1}])
    assert response["code"] == "note_id_not_found"
    assert song.tracks[0].clip_slots[0].clip.applied is None


def test_modify_clip_notes_requires_note_id(script):
    song = _song_with_clip([FakeNote(1, 36, 0.0)])
    response = run(make_instance(script, song), "modify_clip_notes",
                   track_index=0, clip_index=0, notes=[{"velocity": 1}])
    assert response["code"] == "invalid_value"


def test_remove_notes_from_clip_only_removes_the_window(script):
    notes = [FakeNote(1, 36, 0.0), FakeNote(2, 36, 4.0), FakeNote(3, 42, 4.0)]
    song = _song_with_clip(notes)
    response = run(make_instance(script, song), "remove_notes_from_clip",
                   track_index=0, clip_index=0,
                   from_time=4.0, time_span=4.0, from_pitch=36, pitch_span=1)
    assert response["result"]["removed_count"] == 1
    remaining = song.tracks[0].clip_slots[0].clip.notes
    assert [n.note_id for n in remaining] == [1, 3]


def test_remove_notes_negative_span_runs_to_clip_end(script):
    notes = [FakeNote(1, 36, 0.0), FakeNote(2, 36, 2.0), FakeNote(3, 36, 7.5)]
    song = _song_with_clip(notes, length=8.0)
    response = run(make_instance(script, song), "remove_notes_from_clip",
                   track_index=0, clip_index=0, from_time=2.0, time_span=-1.0)
    assert response["result"]["removed_count"] == 2
    assert [n.note_id for n in song.tracks[0].clip_slots[0].clip.notes] == [1]


def test_add_notes_uses_set_notes_when_live_api_is_unavailable(script, monkeypatch):
    monkeypatch.delitem(sys.modules, "Live", raising=False)
    song = _song_with_clip([])
    response = run(make_instance(script, song), "add_notes_to_clip",
                   track_index=0, clip_index=0,
                   notes=[{"pitch": 60, "start_time": 0.0, "duration": 1.0,
                           "velocity": 100}])
    assert response["result"] == {"note_count": 1}
    clip = song.tracks[0].clip_slots[0].clip
    assert clip.set_notes_calls == [((60, 0.0, 1.0, 100, False),)]


def test_add_notes_uses_add_new_notes_with_extended_fields(script, monkeypatch):
    class Spec(object):
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    live = types.ModuleType("Live")
    live.Clip = types.SimpleNamespace(MidiNoteSpecification=Spec)
    monkeypatch.setitem(sys.modules, "Live", live)

    added = []

    class NewApiClip(FakeClip):
        def add_new_notes(self, specs):
            added.extend(specs)
            return [101 + i for i in range(len(specs))]

    song = FakeSong()
    song.tracks[0].clip_slots[0].clip = NewApiClip()
    response = run(make_instance(script, song), "add_notes_to_clip",
                   track_index=0, clip_index=0,
                   notes=[{"pitch": 36, "start_time": 0.0, "duration": 0.25,
                           "velocity": 100, "probability": 0.5}])
    assert response["result"] == {"note_count": 1, "note_ids": [101]}
    assert added[0].kwargs["probability"] == 0.5
    assert "velocity_deviation" not in added[0].kwargs
    assert song.tracks[0].clip_slots[0].clip.set_notes_calls == []


# --------------------------------------------------------------------------
# Session editing, mixer, scenes
# --------------------------------------------------------------------------

def test_duplicate_clip_refuses_an_occupied_target(script):
    song = _song_with_clip([FakeNote(1, 36, 0.0)])
    song.tracks[0].clip_slots[1].clip = FakeClip()
    response = run(make_instance(script, song), "duplicate_clip",
                   track_index=0, source_clip_index=0, dest_clip_index=1)
    assert response["code"] == "clip_slot_occupied"


def test_duplicate_clip_copies_into_empty_slot(script):
    song = _song_with_clip([FakeNote(1, 36, 0.0)])
    response = run(make_instance(script, song), "duplicate_clip",
                   track_index=0, source_clip_index=0, dest_clip_index=2)
    assert response["status"] == "success"
    assert song.tracks[0].clip_slots[2].has_clip


def test_delete_track_keeps_the_last_track(script):
    song = FakeSong(tracks=1)
    response = run(make_instance(script, song), "delete_track", track_index=0)
    assert response["status"] == "error"
    assert len(song.tracks) == 1


def test_delete_track_removes_it(script):
    song = FakeSong(tracks=3)
    response = run(make_instance(script, song), "delete_track", track_index=1)
    assert response["result"]["name"] == "Track 1"
    assert [t.name for t in song.tracks] == ["Track 0", "Track 2"]


@pytest.mark.parametrize("numerator, denominator", [(7, 3), (0, 4), (100, 4)])
def test_time_signature_validation(script, numerator, denominator):
    song = FakeSong()
    response = run(make_instance(script, song), "set_time_signature",
                   numerator=numerator, denominator=denominator)
    assert response["code"] == "invalid_value"
    assert (song.signature_numerator, song.signature_denominator) == (4, 4)


def test_time_signature_is_set(script):
    song = FakeSong()
    response = run(make_instance(script, song), "set_time_signature",
                   numerator=6, denominator=8)
    assert response["result"] == {"signature_numerator": 6, "signature_denominator": 8}


def test_undo_and_redo_respect_availability(script):
    song = FakeSong()
    inst = make_instance(script, song)
    assert run(inst, "undo")["result"] == {"undone": True}
    assert song.undo_calls == 1
    assert run(inst, "redo")["result"]["redone"] is False


def test_mixer_setters_change_live_state(script):
    song = FakeSong()
    inst = make_instance(script, song)
    track = song.tracks[1]
    run(inst, "set_track_volume", track_index=1, value=0.5)
    run(inst, "set_track_panning", track_index=1, value=-0.25)
    run(inst, "set_track_mute", track_index=1, value=True)
    run(inst, "set_track_solo", track_index=1, value=True)
    run(inst, "set_track_arm", track_index=1, value=True)
    run(inst, "set_send_level", track_index=1, send_index=0, value=0.3)
    run(inst, "set_master_volume", value=0.7)
    run(inst, "set_master_panning", value=0.1)
    assert track.mixer_device.volume.value == 0.5
    assert track.mixer_device.panning.value == -0.25
    assert (track.mute, track.solo, track.arm) == (True, True, True)
    assert track.mixer_device.sends[0].value == 0.3
    assert song.master_track.mixer_device.volume.value == 0.7
    assert song.master_track.mixer_device.panning.value == 0.1


def test_arming_a_group_track_is_a_clear_error(script):
    song = FakeSong()
    song.tracks[0].can_be_armed = False
    response = run(make_instance(script, song), "set_track_arm",
                   track_index=0, value=True)
    assert response["code"] == "track_not_armable"
    assert "cannot be armed" in response["message"]


def test_scene_lifecycle(script):
    song = FakeSong(scenes=1)
    inst = make_instance(script, song)
    assert run(inst, "create_scene", index=-1)["result"]["index"] == 1
    assert run(inst, "set_scene_name", scene_index=1, name="Chorus")["result"]["name"] == "Chorus"
    run(inst, "fire_scene", scene_index=1)
    assert song.scenes[1].fired
    assert run(inst, "delete_scene", scene_index=1)["result"]["name"] == "Chorus"
    assert len(song.scenes) == 1
    # Live refuses to delete the last scene; say so up front.
    assert run(inst, "delete_scene", scene_index=0)["status"] == "error"


def test_session_info_lists_scenes(script):
    song = FakeSong(scenes=2)
    song.scenes[1].name = "Drop"
    info = run(make_instance(script, song), "get_session_info")["result"]
    assert info["scene_count"] == 2
    assert info["scenes"] == [{"index": 0, "name": "Scene 0"},
                              {"index": 1, "name": "Drop"}]


# --------------------------------------------------------------------------
# Browser tree depth
# --------------------------------------------------------------------------

class FakeBrowserItem(object):
    def __init__(self, name, children=()):
        self.name = name
        self.children = list(children)
        self.is_device = False
        self.is_loadable = not children
        self.uri = "uri:" + name


def _deep_browser():
    leaf = FakeBrowserItem("Leaf")
    level3 = FakeBrowserItem("L3", [leaf])
    level2 = FakeBrowserItem("L2", [level3])
    level1 = FakeBrowserItem("L1", [level2])
    root = FakeBrowserItem("instruments", [level1])
    return types.SimpleNamespace(browser=types.SimpleNamespace(instruments=root))


def _depth(node):
    if not node["children"]:
        return 0
    return 1 + max(_depth(c) for c in node["children"])


@pytest.mark.parametrize("requested, expected", [(0, 0), (1, 1), (2, 2), (3, 2), (99, 2)])
def test_browser_tree_depth_is_configurable_and_capped(script, requested, expected):
    inst = make_instance(script, application=_deep_browser())
    tree = inst.get_browser_tree("instruments", requested)
    assert _depth(tree["categories"][0]) == expected


def test_browser_tree_defaults_to_one_level(script):
    inst = make_instance(script, application=_deep_browser())
    response = run(inst, "get_browser_tree", category_type="instruments")
    assert _depth(response["result"]["categories"][0]) == 1


# --------------------------------------------------------------------------
# Undo steps
# --------------------------------------------------------------------------

def test_each_editing_command_is_its_own_undo_step(script):
    """Back-to-back create + delete must stay two undo steps, not cancel out."""
    song = FakeSong(tracks=3)
    inst = make_instance(script, song)
    run(inst, "set_track_name", track_index=0, name="Bass")
    run(inst, "delete_track", track_index=2)
    assert song.undo_steps == ["begin", "end", "begin", "end"]


def test_undo_step_closes_when_the_command_fails(script):
    song = FakeSong()
    response = run(make_instance(script, song), "set_track_volume",
                   track_index=0, value=5.0)
    assert response["status"] == "error"
    assert song.undo_steps == ["begin", "end"]


@pytest.mark.parametrize("command, params", [
    ("undo", {}), ("redo", {}), ("start_playback", {}), ("stop_playback", {}),
    ("fire_scene", {"scene_index": 0}),
])
def test_non_editing_commands_add_no_undo_steps(script, command, params):
    song = FakeSong()
    song.start_playing = song.stop_playing = lambda: None
    song.is_playing = False
    run(make_instance(script, song), command, **params)
    assert song.undo_steps == []


def test_undoable_commands_are_all_routed(script):
    inst = make_instance(script)
    assert not inst._UNDOABLE_COMMANDS - set(inst._main_thread_handlers({}))


def test_live_without_undo_step_api_still_runs_commands(script):
    song = FakeSong()
    song.begin_undo_step = None
    response = run(make_instance(script, song), "set_track_mute",
                   track_index=0, value=True)
    assert response["status"] == "success"
    assert song.tracks[0].mute is True


# --------------------------------------------------------------------------
# Group tracks in get_track_info
# --------------------------------------------------------------------------

def test_track_info_flags_group_tracks(script):
    song = FakeSong(tracks=2)
    group, child = song.tracks
    group.is_foldable = True
    group.has_audio_input = True
    group.can_be_armed = False
    child.is_grouped = True
    inst = make_instance(script, song)

    info = run(inst, "get_track_info", track_index=0)["result"]
    assert (info["is_group_track"], info["is_grouped"], info["can_be_armed"]) == (True, False, False)
    assert info["arm"] is False
    info = run(inst, "get_track_info", track_index=1)["result"]
    assert (info["is_group_track"], info["is_grouped"], info["can_be_armed"]) == (False, True, True)


# --------------------------------------------------------------------------
# create_audio_clip error codes
# --------------------------------------------------------------------------

class FakeAudioSlot(FakeClipSlot):
    def __init__(self, error=None):
        super(FakeAudioSlot, self).__init__()
        self.error = error
        self.created = []

    def create_audio_clip(self, path):
        if self.error:
            raise RuntimeError(self.error)
        self.created.append(path)
        self.clip = types.SimpleNamespace(name="Take", length=8.0, is_audio_clip=True)


def _audio_song(slot):
    song = FakeSong()
    track = song.tracks[0]
    track.has_midi_input = False
    track.has_audio_input = True
    track.clip_slots[0] = slot
    return song


@pytest.mark.parametrize("path", ["", "relative.wav", "/no/such/file.wav"])
def test_create_audio_clip_bad_path_is_invalid_audio_file(script, path):
    slot = FakeAudioSlot()
    response = run(make_instance(script, _audio_song(slot)), "create_audio_clip",
                   track_index=0, clip_index=0, path=path)
    assert response["code"] == "invalid_audio_file"
    assert slot.created == []


def test_live_rejecting_the_file_is_invalid_audio_file(script, tmp_path):
    wav = tmp_path / "not-audio.wav"
    wav.write_text("text")
    slot = FakeAudioSlot("The provided path does not appear to point to a valid audio file")
    response = run(make_instance(script, _audio_song(slot)), "create_audio_clip",
                   track_index=0, clip_index=0, path=str(wav))
    assert response["code"] == "invalid_audio_file"


def test_create_audio_clip_imports_an_existing_file(script, tmp_path):
    wav = tmp_path / "take.wav"
    wav.write_bytes(b"RIFF")
    slot = FakeAudioSlot()
    response = run(make_instance(script, _audio_song(slot)), "create_audio_clip",
                   track_index=0, clip_index=0, path=str(wav))
    assert response["status"] == "success"
    assert slot.created == [str(wav)]
