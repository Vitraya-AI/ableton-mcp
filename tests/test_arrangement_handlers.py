"""
Live-side tests for the arrangement commands (Remote Script 1.10.0):
get_arrangement_info, cue_point, set_arrangement_loop,
create_arrangement_midi_clip, create_arrangement_audio_clip,
set_clip_properties, and the view parameter on the note tools and delete_clip.

Same setup as test_remote_script_handlers.py: ``_Framework`` is stubbed, the
class is built without ``__init__``, schedule_message runs the task
immediately, and the Live object model is replaced with small fakes.

Like Live, the fakes apply some writes (the playhead, loop settings, a few
clip properties) only on the next tick: they stay pending until
schedule_message runs a task scheduled with a delay of 1 or more.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

BUNDLED_SCRIPT = (Path(__file__).resolve().parents[1] / "MCP_Server"
                  / "bundled_ableton_remote_script" / "AbletonMCP_init.py")

NEW_COMMANDS = [
    "get_arrangement_info", "cue_point", "set_arrangement_loop",
    "create_arrangement_midi_clip", "create_arrangement_audio_clip",
    "set_clip_properties",
]
UNDOABLE = [
    "set_arrangement_loop", "create_arrangement_midi_clip",
    "create_arrangement_audio_clip", "set_clip_properties",
]


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
        "ableton_mcp_remote_script_arrangement_under_test", BUNDLED_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _load_script_module()


@pytest.fixture(autouse=True)
def no_live(monkeypatch):
    """Notes go through the legacy set_notes path unless a test injects Live."""
    monkeypatch.delitem(sys.modules, "Live", raising=False)


# --------------------------------------------------------------------------
# Fake Live object model
# --------------------------------------------------------------------------

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
    """A clip whose loop/marker setters reject start >= end, like Live."""

    # Writes Live applies on the next tick.
    PENDING = ("muted", "color")

    def __init__(self, name="Clip", length=4.0, start_time=0.0, notes=None,
                 is_midi_clip=True, span=None):
        self._pending = {}
        self._span = span
        self.name = name
        self.length = length
        self.start_time = start_time
        self.notes = list(notes or [])
        self.is_midi_clip = is_midi_clip
        self.is_audio_clip = not is_midi_clip
        self.muted = False
        self.color = 0
        self.looping = True
        self._loop_start = 0.0
        self._loop_end = length
        self._start_marker = 0.0
        self._end_marker = length
        self.gain = 0.5
        self.pitch_coarse = 0
        self.pitch_fine = 0.0
        self.warping = True
        self.warp_mode = 0
        self.settle()
        self.set_log = []

    def __setattr__(self, key, value):
        if key in self.PENDING:
            self._pending[key] = value
        else:
            object.__setattr__(self, key, value)
        if not key.startswith("_") and key != "set_log" and hasattr(self, "set_log"):
            self.set_log.append(key)

    def settle(self):
        for key, value in self._pending.items():
            object.__setattr__(self, key, value)
        self._pending.clear()

    @property
    def end_time(self):
        """Timeline end; a looped clip can span more than its loop length."""
        return self.start_time + (self._span if self._span is not None else self.length)

    def _pair(self, low, high):
        if low >= high:
            raise RuntimeError("Invalid marker order")

    @property
    def loop_start(self):
        return self._loop_start

    @loop_start.setter
    def loop_start(self, value):
        self._pair(value, self._loop_end)
        self._loop_start = value

    @property
    def loop_end(self):
        return self._loop_end

    @loop_end.setter
    def loop_end(self, value):
        self._pair(self._loop_start, value)
        self._loop_end = value

    @property
    def start_marker(self):
        return self._start_marker

    @start_marker.setter
    def start_marker(self, value):
        self._pair(value, self._end_marker)
        self._start_marker = value

    @property
    def end_marker(self):
        return self._end_marker

    @end_marker.setter
    def end_marker(self, value):
        self._pair(self._start_marker, value)
        self._end_marker = value

    # Note API
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
        for pitch, start, duration, velocity, _mute in notes:
            self.notes.append(FakeNote(len(self.notes) + 1, pitch, start, duration, velocity))


class FakeClipSlot(object):
    def __init__(self, clip=None):
        self.clip = clip

    @property
    def has_clip(self):
        return self.clip is not None

    def create_clip(self, length):
        self.clip = FakeClip("", length)

    def delete_clip(self):
        self.clip = None


class FakeTrack(object):
    def __init__(self, name="Track", midi=True, slots=2):
        self.name = name
        self.clip_slots = [FakeClipSlot() for _ in range(slots)]
        self.has_midi_input = midi
        self.has_audio_input = not midi
        self.is_foldable = False
        self._arrangement = []
        self.duplicate_fails = False

    @property
    def arrangement_clips(self):
        return tuple(sorted(self._arrangement, key=lambda c: c.start_time))

    def add_arrangement_clip(self, clip):
        self._arrangement.append(clip)
        return clip

    def duplicate_clip_to_arrangement(self, clip, time):
        if self.duplicate_fails:
            raise RuntimeError("duplicate failed")
        copy = FakeClip(clip.name, clip.length, time, list(clip.notes))
        # Live 11 moves the playhead to the duplicated clip.
        self.song.current_song_time = time
        return self.add_arrangement_clip(copy)

    def delete_clip(self, clip):
        self._arrangement.remove(clip)


class Live12Track(FakeTrack):
    def create_midi_clip(self, start, length):
        return self.add_arrangement_clip(FakeClip("", length, start))


class AudioTrack(FakeTrack):
    def __init__(self, name="Audio"):
        super(AudioTrack, self).__init__(name, midi=False)
        self.imports = []

    def create_audio_clip(self, path, time):
        self.imports.append((path, time))
        self.add_arrangement_clip(FakeClip("sample", 8.0, time, is_midi_clip=False))
        # Live moves the playhead to the imported clip.
        self.song.current_song_time = time


class GroupTrack(FakeTrack):
    @property
    def arrangement_clips(self):
        raise RuntimeError("group tracks have no arrangement clips")


class FakeCue(object):
    def __init__(self, song, name, time):
        self.song = song
        self.name = name
        self.time = time

    def jump(self):
        self.song.current_song_time = self.time


class ReadOnlyNameCue(FakeCue):
    """Live 11: CuePoint.name is Get/Listen only."""

    def __init__(self, song, name, time):
        self.song = song
        self._name = name
        self.time = time

    @property
    def name(self):
        return self._name


class FakeSong(object):
    # Writes Live applies on the next tick.
    PENDING = ("current_song_time", "loop", "loop_start", "loop_length")

    def __init__(self, tracks=None):
        object.__setattr__(self, "_pending", {})
        self.tracks = tracks if tracks is not None else [FakeTrack("Midi")]
        for track in self.tracks:
            track.song = self
        self.cue_points = []
        self.current_song_time = 0.0
        self.song_length = 64.0
        self.loop = False
        self.loop_start = 0.0
        self.loop_length = 16.0
        self.tempo = 120.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.undo_steps = []
        self.events = []
        self.cue_select_fails = False
        self.playhead_stuck = False
        self.toggle_ignored = False
        self.cue_class = FakeCue
        # When set, applying a playhead move shortens the song to this length.
        self.shrink_on_move = None
        self.settle()

    def __setattr__(self, key, value):
        if key == "current_song_time" and value > getattr(self, "song_length", value):
            raise RuntimeError("Cannot set the Songtime behind the Songlength")
        if key in self.PENDING:
            if not (key == "current_song_time" and getattr(self, "playhead_stuck", False)):
                self._pending[key] = value
        else:
            object.__setattr__(self, key, value)

    def settle(self):
        """Apply pending writes, as Live does on its next tick."""
        moved = "current_song_time" in self._pending
        for key, value in self._pending.items():
            object.__setattr__(self, key, value)
        self._pending.clear()
        if moved and getattr(self, "shrink_on_move", None) is not None:
            self.song_length = self.shrink_on_move
        for track in self.tracks:
            clips = [slot.clip for slot in track.clip_slots if slot.clip is not None]
            clips.extend(track._arrangement)
            for clip in clips:
                clip.settle()

    def tick(self):
        self.events.append("tick")
        self.settle()

    def begin_undo_step(self):
        self.undo_steps.append("begin")
        self.events.append("begin")

    def end_undo_step(self):
        self.undo_steps.append("end")
        self.events.append("end")

    def add_cue(self, name, time):
        self.cue_points.append(self.cue_class(self, name, time))

    # Cue operations use the applied playhead, not a pending write.
    def _cue_here(self):
        for cue in self.cue_points:
            if cue.time == self.current_song_time:
                return cue
        return None

    def is_cue_point_selected(self):
        return not self.cue_select_fails and self._cue_here() is not None

    def set_or_delete_cue(self):
        self.events.append("toggle")
        if self.toggle_ignored:
            return
        cue = self._cue_here()
        if cue is not None:
            self.cue_points.remove(cue)
        else:
            self.add_cue("", self.current_song_time)

    def _cue_times(self):
        return sorted(c.time for c in self.cue_points)

    def jump_to_next_cue(self):
        later = [t for t in self._cue_times() if t > self.current_song_time]
        if later:
            self.current_song_time = later[0]

    def jump_to_prev_cue(self):
        earlier = [t for t in self._cue_times() if t < self.current_song_time]
        if earlier:
            self.current_song_time = earlier[-1]


def make_instance(script, song):
    inst = script.AbletonMCP.__new__(script.AbletonMCP)
    inst._song = song
    inst.log_message = lambda *a, **k: None
    inst.show_message = lambda *a, **k: None

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


# --------------------------------------------------------------------------
# Routing and capabilities
# --------------------------------------------------------------------------

def test_new_commands_are_routed_and_advertised(script):
    inst = make_instance(script, FakeSong())
    reads = set(inst._read_handlers({}))
    writes = set(inst._main_thread_handlers({}))
    assert "get_arrangement_info" in reads
    for name in NEW_COMMANDS:
        assert name in script.SCRIPT_CAPABILITIES
        if name != "get_arrangement_info":
            assert name in writes
    assert "clip_view_param" in script.SCRIPT_CAPABILITIES


def test_undoable_set(script):
    for name in UNDOABLE:
        assert name in script.AbletonMCP._UNDOABLE_COMMANDS
    assert "cue_point" not in script.AbletonMCP._UNDOABLE_COMMANDS
    assert script.AbletonMCP._MAIN_THREAD_TIMEOUTS["create_arrangement_audio_clip"] == 60.0


# --------------------------------------------------------------------------
# get_arrangement_info
# --------------------------------------------------------------------------

def test_get_arrangement_info(script):
    midi = FakeTrack("Keys")
    midi.add_arrangement_clip(FakeClip("B", 4.0, 8.0))
    muted = midi.add_arrangement_clip(FakeClip("A", 2.0, 0.0))
    muted.muted = True
    group = GroupTrack("Group")
    group.is_foldable = True
    song = FakeSong([midi, AudioTrack("Vox"), group])
    song.add_cue("Chorus", 16.0)
    song.add_cue("Intro", 0.0)
    song.loop = True
    song.settle()

    info = ok(run(make_instance(script, song), "get_arrangement_info"))
    assert info["loop"] == {"enabled": True, "start": 0.0, "length": 16.0}
    assert info["song_length"] == 64.0
    assert (info["signature_numerator"], info["signature_denominator"]) == (4, 4)
    assert info["cue_points"] == [
        {"index": 0, "name": "Intro", "time": 0.0},
        {"index": 1, "name": "Chorus", "time": 16.0}]
    keys = info["tracks"][0]
    assert keys["is_midi_track"] and not keys["is_audio_track"]
    assert [c["name"] for c in keys["clips"]] == ["A", "B"]
    assert keys["clips"][0] == {"index": 0, "name": "A", "start_time": 0.0,
                                "end_time": 2.0, "length": 2.0, "loop_length": 2.0,
                                "is_midi_clip": True, "muted": True}
    assert info["tracks"][1]["is_audio_track"]
    assert info["tracks"][2]["is_group_track"]
    assert info["tracks"][2]["clips"] == []


# --------------------------------------------------------------------------
# cue_point
# --------------------------------------------------------------------------

def _cue_song():
    song = FakeSong()
    song.add_cue("Verse", 8.0)
    song.add_cue("Intro", 0.0)
    song.add_cue("verse", 24.0)
    song.current_song_time = 4.0
    song.settle()
    return song


def test_cue_jump_by_name_is_case_insensitive_and_first_in_time(script):
    song = _cue_song()
    result = ok(run(make_instance(script, song), "cue_point", action="jump", name="VERSE"))
    assert result["cue"] == {"name": "Verse", "time": 8.0}
    assert result["current_song_time"] == 8.0
    assert song.undo_steps == []


def test_cue_jump_by_nearest_time(script):
    song = _cue_song()
    result = ok(run(make_instance(script, song), "cue_point", action="jump", time=20.0))
    assert result["cue"]["time"] == 24.0


def test_cue_next_and_previous(script):
    song = _cue_song()
    inst = make_instance(script, song)
    result = ok(run(inst, "cue_point", action="next"))
    assert result["cue"] == {"name": "Verse", "time": 8.0}
    result = ok(run(inst, "cue_point", action="previous"))
    assert result["cue"] == {"name": "Intro", "time": 0.0}
    assert result["action"] == "previous"
    assert song.undo_steps == []


def test_cue_delete_by_time_restores_playhead_in_one_undo_step(script):
    song = _cue_song()
    result = ok(run(make_instance(script, song), "cue_point", action="delete", time=8.0005))
    assert result["cue"] == {"name": "Verse", "time": 8.0}
    assert sorted(c.time for c in song.cue_points) == [0.0, 24.0]
    assert song.current_song_time == 4.0
    assert result["current_song_time"] == 4.0
    assert song.undo_steps == ["begin", "end"]


def test_cue_delete_needs_exact_time(script):
    song = _cue_song()
    response = run(make_instance(script, song), "cue_point", action="delete", time=9.0)
    assert error_code(response) == "cue_not_found"
    assert len(song.cue_points) == 3


def test_cue_delete_when_cue_cannot_be_selected(script):
    song = _cue_song()
    song.cue_select_fails = True
    response = run(make_instance(script, song), "cue_point", action="delete", name="Intro")
    assert error_code(response) == "internal_error"
    assert "could not select cue" in response["message"]
    assert len(song.cue_points) == 3
    assert "toggle" not in song.events
    song.settle()
    assert song.current_song_time == 4.0


@pytest.mark.parametrize("params,code", [
    ({"action": "jump", "name": "Bridge"}, "cue_not_found"),
    ({"action": "jump"}, "invalid_value"),
    ({"action": "delete"}, "invalid_value"),
    ({"action": "rewind"}, "invalid_value"),
])
def test_cue_point_errors(script, params, code):
    assert error_code(run(make_instance(script, _cue_song()), "cue_point", **params)) == code


def test_cue_jump_with_no_cues(script):
    response = run(make_instance(script, FakeSong()), "cue_point", action="jump", time=0.0)
    assert error_code(response) == "cue_not_found"


# --------------------------------------------------------------------------
# set_arrangement_loop
# --------------------------------------------------------------------------

def test_set_arrangement_loop(script):
    song = FakeSong()
    result = ok(run(make_instance(script, song), "set_arrangement_loop",
                    enabled=True, start=8.0, length=4.0))
    assert result == {"enabled": True, "start": 8.0, "length": 4.0}
    assert song.undo_steps == ["begin", "end"]


def test_set_arrangement_loop_keeps_unspecified_fields(script):
    song = FakeSong()
    result = ok(run(make_instance(script, song), "set_arrangement_loop", enabled=True))
    assert result == {"enabled": True, "start": 0.0, "length": 16.0}


@pytest.mark.parametrize("params", [{"start": -1.0}, {"length": 0.0}, {"length": -2.0}])
def test_set_arrangement_loop_rejects_bad_ranges(script, params):
    song = FakeSong()
    response = run(make_instance(script, song), "set_arrangement_loop", enabled=True, **params)
    assert error_code(response) == "invalid_value"
    assert song.loop is False


# --------------------------------------------------------------------------
# create_arrangement_midi_clip
# --------------------------------------------------------------------------

NOTES = [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100},
         {"pitch": 64, "start_time": 1.0, "duration": 1.0, "velocity": 90}]


def test_midi_clip_live11_session_fallback(script):
    track = FakeTrack("Keys")
    track.clip_slots[0].clip = FakeClip("occupied")
    track.add_arrangement_clip(FakeClip("Earlier", 4.0, 0.0))
    song = FakeSong([track])
    result = ok(run(make_instance(script, song), "create_arrangement_midi_clip",
                    track_index=0, start=8.0, length=4.0, notes=NOTES, name="Hook"))
    assert result == {"track_index": 0, "clip_index": 1, "name": "Hook",
                      "start_time": 8.0, "end_time": 12.0, "note_count": 2,
                      "method": "session_fallback", "playhead_restored": True}
    new = track.arrangement_clips[1]
    assert [(n.pitch, n.start_time) for n in new.notes] == [(60, 0.0), (64, 1.0)]
    # The temporary Session clip is gone; the occupied slot is untouched.
    assert track.clip_slots[1].clip is None
    assert track.clip_slots[0].clip.name == "occupied"
    assert song.undo_steps == ["begin", "end"]


def test_midi_clip_fallback_deletes_temp_clip_when_duplicating_fails(script):
    track = FakeTrack("Keys")
    track.duplicate_fails = True
    song = FakeSong([track])
    response = run(make_instance(script, song), "create_arrangement_midi_clip",
                   track_index=0, start=0.0, length=4.0, notes=NOTES)
    assert error_code(response) == "internal_error"
    assert all(slot.clip is None for slot in track.clip_slots)
    assert track.arrangement_clips == ()
    assert song.undo_steps == ["begin", "end"]


def test_midi_clip_fallback_without_free_slot(script):
    track = FakeTrack("Keys", slots=1)
    track.clip_slots[0].clip = FakeClip("occupied")
    response = run(make_instance(script, FakeSong([track])), "create_arrangement_midi_clip",
                   track_index=0, start=0.0, length=4.0)
    assert error_code(response) == "no_free_clip_slot"


def test_midi_clip_live12_create_midi_clip(script):
    track = Live12Track("Keys", slots=0)
    track.add_arrangement_clip(FakeClip("Later", 4.0, 16.0))
    result = ok(run(make_instance(script, FakeSong([track])), "create_arrangement_midi_clip",
                    track_index=0, start=4.0, length=8.0, notes=NOTES, name="Pad"))
    assert result["method"] == "create_midi_clip"
    assert result["clip_index"] == 0
    assert (result["name"], result["start_time"], result["end_time"]) == ("Pad", 4.0, 12.0)
    assert len(track.arrangement_clips[0].notes) == 2


def test_midi_clip_uses_add_new_notes_when_available(script, monkeypatch):
    class Spec(object):
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    live = types.ModuleType("Live")
    live.Clip = types.SimpleNamespace(MidiNoteSpecification=Spec)
    monkeypatch.setitem(sys.modules, "Live", live)
    added = []

    class SpecClip(FakeClip):
        def add_new_notes(self, specs):
            added.extend(specs)
            return [1]

    class SpecSlot(FakeClipSlot):
        def create_clip(self, length):
            self.clip = SpecClip("", length)

    track = FakeTrack("Keys")
    track.clip_slots = [SpecSlot()]
    result = ok(run(make_instance(script, FakeSong([track])), "create_arrangement_midi_clip",
                    track_index=0, start=0.0, length=4.0,
                    notes=[dict(NOTES[0], probability=0.5)]))
    assert result["note_count"] == 1
    assert added[0].kwargs["probability"] == 0.5


@pytest.mark.parametrize("start,length,allow,code", [
    (2.0, 4.0, False, "clip_overlap"),     # starts inside
    (0.0, 8.0, False, "clip_overlap"),     # covers it
    (-1.0, 4.0, False, "invalid_value"),
    (8.0, 0.0, False, "invalid_value"),
])
def test_midi_clip_rejections(script, start, length, allow, code):
    track = FakeTrack("Keys")
    track.add_arrangement_clip(FakeClip("Existing", 4.0, 4.0))
    response = run(make_instance(script, FakeSong([track])), "create_arrangement_midi_clip",
                   track_index=0, start=start, length=length, allow_overlap=allow)
    assert error_code(response) == code
    if code == "clip_overlap":
        assert "Existing" in response["message"]
    assert len(track.arrangement_clips) == 1


def test_midi_clip_touching_is_not_overlap_and_allow_overlap(script):
    track = FakeTrack("Keys")
    track.add_arrangement_clip(FakeClip("Existing", 4.0, 4.0))
    inst = make_instance(script, FakeSong([track]))
    ok(run(inst, "create_arrangement_midi_clip", track_index=0, start=8.0, length=4.0))
    ok(run(inst, "create_arrangement_midi_clip", track_index=0, start=5.0, length=1.0,
           allow_overlap=True))
    assert len(track.arrangement_clips) == 3


def test_midi_clip_needs_midi_track(script):
    response = run(make_instance(script, FakeSong([AudioTrack()])),
                   "create_arrangement_midi_clip", track_index=0, start=0.0, length=4.0)
    assert error_code(response) == "not_midi_track"


def test_midi_clip_track_index(script):
    response = run(make_instance(script, FakeSong()), "create_arrangement_midi_clip",
                   track_index=5, start=0.0, length=4.0)
    assert error_code(response) == "track_index_out_of_range"


# --------------------------------------------------------------------------
# create_arrangement_audio_clip
# --------------------------------------------------------------------------

@pytest.fixture
def wav(tmp_path):
    path = tmp_path / "loop.wav"
    path.write_bytes(b"RIFF")
    return str(path)


def test_audio_clip(script, wav):
    track = AudioTrack()
    track.add_arrangement_clip(FakeClip("Earlier", 4.0, 0.0, is_midi_clip=False))
    song = FakeSong([track])
    result = ok(run(make_instance(script, song), "create_arrangement_audio_clip",
                    track_index=0, path=wav, start=16.0))
    assert track.imports == [(wav, 16.0)]
    assert result == {"track_index": 0, "clip_index": 1, "name": "sample",
                      "start_time": 16.0, "end_time": 24.0, "length": 8.0,
                      "playhead_restored": True}
    assert song.undo_steps == ["begin", "end"]


def test_audio_clip_overlap_only_counts_a_clip_covering_start(script, wav):
    track = AudioTrack()
    track.add_arrangement_clip(FakeClip("Existing", 4.0, 4.0, is_midi_clip=False))
    inst = make_instance(script, FakeSong([track]))
    response = run(inst, "create_arrangement_audio_clip", track_index=0, path=wav, start=6.0)
    assert error_code(response) == "clip_overlap"
    # Starts before the existing clip: allowed (length is unknown before import).
    ok(run(inst, "create_arrangement_audio_clip", track_index=0, path=wav, start=0.0))
    ok(run(inst, "create_arrangement_audio_clip", track_index=0, path=wav, start=6.0,
           allow_overlap=True))


@pytest.mark.parametrize("path_kind,code", [
    ("empty", "invalid_audio_file"),
    ("relative", "invalid_audio_file"),
    ("missing", "invalid_audio_file"),
])
def test_audio_clip_path_checks(script, wav, tmp_path, path_kind, code):
    path = {"empty": "", "relative": "loop.wav",
            "missing": str(tmp_path / "nope.wav")}[path_kind]
    response = run(make_instance(script, FakeSong([AudioTrack()])),
                   "create_arrangement_audio_clip", track_index=0, path=path, start=0.0)
    assert error_code(response) == code


def test_audio_clip_other_errors(script, wav):
    inst = make_instance(script, FakeSong([AudioTrack(), FakeTrack("Midi", midi=False)]))
    for start in (-1.0, 1576801.0):
        response = run(inst, "create_arrangement_audio_clip", track_index=0, path=wav,
                       start=start)
        assert error_code(response) == "invalid_value"
    # Audio track without Track.create_audio_clip.
    response = run(inst, "create_arrangement_audio_clip", track_index=1, path=wav, start=0.0)
    assert error_code(response) == "not_supported"
    midi_inst = make_instance(script, FakeSong([FakeTrack("Keys")]))
    response = run(midi_inst, "create_arrangement_audio_clip", track_index=0, path=wav,
                   start=0.0)
    assert error_code(response) == "not_audio_track"


# --------------------------------------------------------------------------
# set_clip_properties
# --------------------------------------------------------------------------

def _song_with_session_clip(clip):
    track = FakeTrack("Keys")
    track.clip_slots[0].clip = clip
    return FakeSong([track])


def test_set_clip_properties_reads_values_back(script):
    clip = FakeClip("Old", 8.0)
    song = _song_with_session_clip(clip)
    result = ok(run(make_instance(script, song), "set_clip_properties",
                    track_index=0, clip_index=0,
                    properties={"name": "New", "muted": True, "color": 255,
                                "looping": False}))
    assert result == {"properties": {"name": "New", "muted": True, "color": 255,
                                     "looping": False}}
    assert song.undo_steps == ["begin", "end"]


def test_set_clip_properties_moves_loop_past_current_end(script):
    # loop 0..8 -> 12..16: loop_start=12 first would be >= the current end.
    clip = FakeClip("C", 8.0)
    result = ok(run(make_instance(script, _song_with_session_clip(clip)),
                    "set_clip_properties", track_index=0, clip_index=0,
                    properties={"loop_start": 12.0, "loop_end": 16.0}))
    assert result["properties"] == {"loop_start": 12.0, "loop_end": 16.0}
    assert [k for k in clip.set_log if k.startswith("loop_")] == ["loop_end", "loop_start"]


def test_set_clip_properties_moves_markers_before_current_start(script):
    clip = FakeClip("C", 8.0)
    clip.start_marker = 4.0
    clip.end_marker = 8.0
    clip.set_log[:] = []
    result = ok(run(make_instance(script, _song_with_session_clip(clip)),
                    "set_clip_properties", track_index=0, clip_index=0,
                    properties={"end_marker": 2.0, "start_marker": 1.0}))
    assert result["properties"] == {"end_marker": 2.0, "start_marker": 1.0}
    assert clip.set_log == ["start_marker", "end_marker"]


@pytest.mark.parametrize("properties,code", [
    ({}, "invalid_value"),
    (None, "invalid_value"),
    ({"tempo": 1}, "invalid_value"),
    ({"loop_start": 4.0, "loop_end": 2.0}, "invalid_value"),
    ({"color": "red"}, "invalid_value"),
    ({"gain": 0.5}, "not_audio_clip"),
    ({"name": "x", "warp_mode": 1}, "not_audio_clip"),
])
def test_set_clip_properties_errors(script, properties, code):
    clip = FakeClip("Keep", 8.0)
    response = run(make_instance(script, _song_with_session_clip(clip)),
                   "set_clip_properties", track_index=0, clip_index=0,
                   properties=properties)
    assert error_code(response) == code
    assert clip.name == "Keep"


def test_set_clip_properties_unknown_key_lists_allowed(script):
    response = run(make_instance(script, _song_with_session_clip(FakeClip())),
                   "set_clip_properties", track_index=0, clip_index=0,
                   properties={"tempo": 1})
    for key in ("name", "loop_start", "warp_mode"):
        assert key in response["message"]


def test_set_clip_properties_audio_clip_in_arrangement(script):
    track = AudioTrack()
    clip = track.add_arrangement_clip(FakeClip("A", 8.0, 0.0, is_midi_clip=False))
    result = ok(run(make_instance(script, FakeSong([track])), "set_clip_properties",
                    track_index=0, clip_index=0, view="arrangement",
                    properties={"gain": 0.8, "pitch_coarse": -12, "pitch_fine": 25.0,
                                "warping": False, "warp_mode": 4}))
    assert result["properties"] == {"gain": 0.8, "pitch_coarse": -12, "pitch_fine": 25.0,
                                    "warping": False, "warp_mode": 4}
    assert clip.warp_mode == 4


# --------------------------------------------------------------------------
# view parameter
# --------------------------------------------------------------------------

def _arrangement_song():
    """Session slot 0 and arrangement clip 1 both exist, with different notes."""
    track = FakeTrack("Keys")
    track.clip_slots[0].clip = FakeClip("Session", 4.0, notes=[FakeNote(1, 48, 0.0)])
    track.add_arrangement_clip(FakeClip("Arr A", 4.0, 0.0, notes=[FakeNote(1, 36, 0.0)]))
    track.add_arrangement_clip(FakeClip("Arr B", 4.0, 8.0, notes=[
        FakeNote(1, 60, 0.0), FakeNote(2, 62, 1.0)]))
    return FakeSong([track])


def test_view_get_clip_notes(script):
    song = _arrangement_song()
    inst = make_instance(script, song)
    result = ok(run(inst, "get_clip_notes", track_index=0, clip_index=1, view="arrangement"))
    assert result["clip_name"] == "Arr B"
    assert [n["pitch"] for n in result["notes"]] == [60, 62]
    session = ok(run(inst, "get_clip_notes", track_index=0, clip_index=0))
    assert session["clip_name"] == "Session"
    assert ok(run(inst, "get_clip_notes", track_index=0, clip_index=0,
                  view="session")) == session


def test_view_add_notes(script):
    song = _arrangement_song()
    result = ok(run(make_instance(script, song), "add_notes_to_clip", track_index=0,
                    clip_index=0, view="arrangement", notes=[NOTES[0]]))
    assert result == {"note_count": 1}
    assert len(song.tracks[0].arrangement_clips[0].notes) == 2
    assert len(song.tracks[0].clip_slots[0].clip.notes) == 1


def test_view_modify_notes(script):
    song = _arrangement_song()
    result = ok(run(make_instance(script, song), "modify_clip_notes", track_index=0,
                    clip_index=1, view="arrangement",
                    notes=[{"note_id": 2, "velocity": 50}]))
    assert result["modified_count"] == 1
    assert song.tracks[0].arrangement_clips[1].notes[1].velocity == 50


def test_view_remove_notes(script):
    song = _arrangement_song()
    result = ok(run(make_instance(script, song), "remove_notes_from_clip", track_index=0,
                    clip_index=1, view="arrangement", from_time=0.5))
    assert result["removed_count"] == 1
    assert [n.pitch for n in song.tracks[0].arrangement_clips[1].notes] == [60]


def test_view_clear_notes(script):
    song = _arrangement_song()
    result = ok(run(make_instance(script, song), "clear_notes_from_clip", track_index=0,
                    clip_index=1, view="arrangement"))
    assert result["cleared_count"] == 2
    assert result["clip_name"] == "Arr B"
    assert len(song.tracks[0].clip_slots[0].clip.notes) == 1


def test_view_delete_clip(script):
    song = _arrangement_song()
    result = ok(run(make_instance(script, song), "delete_clip", track_index=0,
                    clip_index=0, view="arrangement"))
    assert result == {"deleted": True}
    assert [c.name for c in song.tracks[0].arrangement_clips] == ["Arr B"]
    assert song.tracks[0].clip_slots[0].clip is not None
    assert song.undo_steps == ["begin", "end"]


def test_view_session_delete_unchanged(script):
    song = _arrangement_song()
    inst = make_instance(script, song)
    assert ok(run(inst, "delete_clip", track_index=0, clip_index=1)) == {
        "deleted": False, "reason": "Clip slot was already empty"}
    assert ok(run(inst, "delete_clip", track_index=0, clip_index=0,
                  view="session")) == {"deleted": True}
    assert len(song.tracks[0].arrangement_clips) == 2


@pytest.mark.parametrize("command,extra", [
    ("get_clip_notes", {}),
    ("add_notes_to_clip", {"notes": []}),
    ("modify_clip_notes", {"notes": []}),
    ("remove_notes_from_clip", {}),
    ("clear_notes_from_clip", {}),
    ("delete_clip", {}),
    ("set_clip_properties", {"properties": {"name": "x"}}),
])
def test_view_errors(script, command, extra):
    inst = make_instance(script, _arrangement_song())
    response = run(inst, command, track_index=0, clip_index=2, view="arrangement", **extra)
    assert error_code(response) == "clip_index_out_of_range"
    response = run(inst, command, track_index=0, clip_index=0, view="clip", **extra)
    assert error_code(response) == "invalid_value"


def test_view_arrangement_on_group_track(script):
    song = FakeSong([GroupTrack("Group")])
    response = run(make_instance(script, song), "get_clip_notes", track_index=0,
                   clip_index=0, view="arrangement")
    assert error_code(response) == "clip_index_out_of_range"


# --------------------------------------------------------------------------
# Multi-tick commands: Live applies writes on the next tick
# --------------------------------------------------------------------------

def _one_undo_step_around_ticks(song):
    """One begin/end pair, opened before the first tick and closed after the last."""
    assert song.undo_steps == ["begin", "end"]
    assert song.events[0] == "begin"
    assert song.events[-1] == "end"
    assert "tick" in song.events


def test_create_locator_toggles_at_the_target_not_the_old_playhead(script):
    song = FakeSong()
    song.current_song_time = 32.0
    song.settle()
    result = ok(run(make_instance(script, song), "create_locator", name="Intro", time=0.0))
    assert result == {"success": True, "time": 0.0, "name": "Intro",
                      "requested_name": "Intro", "name_applied": True,
                      "playhead_restored": True}
    assert [(c.name, c.time) for c in song.cue_points] == [("Intro", 0.0)]
    assert song.current_song_time == 32.0
    assert song.events.count("toggle") == 1
    _one_undo_step_around_ticks(song)


def test_create_locator_renames_an_existing_cue_without_toggling(script):
    song = _cue_song()
    result = ok(run(make_instance(script, song), "create_locator", name="Drop", time=8.0))
    assert result["name"] == "Drop"
    assert len(song.cue_points) == 3
    assert "toggle" not in song.events
    assert song.current_song_time == 4.0


def test_create_locator_reports_a_cue_that_never_appears(script):
    song = FakeSong()
    song.current_song_time = 32.0
    song.settle()
    song.toggle_ignored = True
    response = run(make_instance(script, song), "create_locator", name="X", time=16.0)
    assert error_code(response) == "internal_error"
    assert "Failed to create cue at time 16.0" in response["message"]
    song.settle()
    assert song.current_song_time == 32.0
    assert song.undo_steps == ["begin", "end"]


def test_create_locator_never_toggles_when_the_playhead_does_not_move(script):
    song = FakeSong()
    song.current_song_time = 32.0
    song.settle()
    song.playhead_stuck = True
    response = run(make_instance(script, song), "create_locator", name="X", time=0.0)
    assert error_code(response) == "timeout"
    assert "toggle" not in song.events
    assert song.cue_points == []


def test_cue_delete_removes_only_the_target_and_spans_one_undo_step(script):
    song = _cue_song()
    song.song_length = 500.0
    song.add_cue("Outro", 462.0)
    song.current_song_time = 462.0
    song.settle()
    result = ok(run(make_instance(script, song), "cue_point", action="delete", name="Intro"))
    assert result["playhead_restored"] is True
    assert result["cue"] == {"name": "Intro", "time": 0.0}
    assert sorted(c.time for c in song.cue_points) == [8.0, 24.0, 462.0]
    assert song.events.count("toggle") == 1
    assert song.current_song_time == 462.0
    assert result["current_song_time"] == 462.0
    _one_undo_step_around_ticks(song)


def test_cue_delete_never_toggles_when_the_playhead_does_not_move(script):
    song = _cue_song()
    song.playhead_stuck = True
    response = run(make_instance(script, song), "cue_point", action="delete", name="Verse")
    assert response["status"] == "error"
    assert "toggle" not in song.events
    assert sorted(c.time for c in song.cue_points) == [0.0, 8.0, 24.0]


def test_cue_next_reports_where_live_landed(script):
    song = _cue_song()
    song.song_length = 500.0
    song.add_cue("Outro", 462.0)
    song.current_song_time = 32.0
    song.settle()
    result = ok(run(make_instance(script, song), "cue_point", action="next"))
    assert result["cue"] == {"name": "Outro", "time": 462.0}
    assert result["current_song_time"] == 462.0
    assert song.undo_steps == []


def test_cue_jump_waits_for_the_playhead(script):
    song = _cue_song()
    result = ok(run(make_instance(script, song), "cue_point", action="jump", name="verse"))
    assert result["current_song_time"] == 8.0


def test_set_arrangement_loop_reads_back_the_applied_values(script):
    song = FakeSong()
    result = ok(run(make_instance(script, song), "set_arrangement_loop",
                    enabled=True, start=16.0, length=8.0))
    assert result == {"enabled": True, "start": 16.0, "length": 8.0}
    _one_undo_step_around_ticks(song)


def test_midi_clip_fallback_restores_the_playhead(script):
    song = FakeSong([FakeTrack("Keys")])
    song.current_song_time = 2.0
    song.settle()
    result = ok(run(make_instance(script, song), "create_arrangement_midi_clip",
                    track_index=0, start=16.0, length=4.0, notes=NOTES))
    assert result["method"] == "session_fallback"
    assert song.current_song_time == 2.0
    _one_undo_step_around_ticks(song)


def test_set_clip_properties_reads_back_after_live_applies(script):
    clip = FakeClip("C", 4.0)
    song = _song_with_session_clip(clip)
    result = ok(run(make_instance(script, song), "set_clip_properties",
                    track_index=0, clip_index=0,
                    properties={"muted": True, "color": 1234}))
    assert result["properties"] == {"muted": True, "color": 1234}
    _one_undo_step_around_ticks(song)


def test_arrangement_info_length_is_the_timeline_length(script):
    track = FakeTrack("Keys")
    track.add_arrangement_clip(FakeClip("Looped", 4.0, 16.0, span=8.0))
    info = ok(run(make_instance(script, FakeSong([track])), "get_arrangement_info"))
    clip = info["tracks"][0]["clips"][0]
    assert (clip["start_time"], clip["end_time"]) == (16.0, 24.0)
    assert clip["length"] == 8.0
    assert clip["loop_length"] == 4.0


def test_a_wait_that_never_succeeds_is_a_timeout(script):
    song = FakeSong()
    inst = make_instance(script, song)
    outcome = inst._run_on_main_thread(
        "set_arrangement_loop", lambda: inst._wait_for(lambda: False, max_ticks=3))
    assert outcome["status"] == "error"
    assert outcome["code"] == "timeout"
    assert song.events.count("tick") == 3
    # The undo step still closes when the command fails mid-way.
    assert song.undo_steps == ["begin", "end"]


def test_a_wait_can_report_failure_instead_of_raising(script):
    inst = make_instance(script, FakeSong())

    def handler():
        done = yield from inst._wait_for(lambda: False, max_ticks=2, raise_on_timeout=False)
        return {"done": done}

    assert inst._run_on_main_thread("cue_point", handler) == {
        "status": "success", "result": {"done": False}}


def test_generator_results_are_the_return_value(script):
    inst = make_instance(script, FakeSong())

    def handler():
        yield
        yield
        return {"answer": 42}

    assert inst._run_on_main_thread("cue_point", handler) == {
        "status": "success", "result": {"answer": 42}}


def test_plain_commands_run_in_one_tick(script):
    song = _arrangement_song()
    ok(run(make_instance(script, song), "delete_clip", track_index=0, clip_index=0))
    assert song.events == ["begin", "end"]


# --------------------------------------------------------------------------
# Locator names, playhead restore limits, set_current_song_time
# --------------------------------------------------------------------------

def test_create_locator_reports_a_rename_live_11_refuses(script):
    song = FakeSong()
    song.cue_class = ReadOnlyNameCue
    response = run(make_instance(script, song), "create_locator", name="Verse", time=16.0)
    result = ok(response)
    assert result["time"] == 16.0
    assert result["name"] == ""
    assert result["requested_name"] == "Verse"
    assert result["name_applied"] is False
    assert len(song.cue_points) == 1


def test_create_locator_rename_of_existing_cue_on_live_11(script):
    song = FakeSong()
    song.cue_class = ReadOnlyNameCue
    song.add_cue("1", 8.0)
    result = ok(run(make_instance(script, song), "create_locator", name="Drop", time=8.0))
    assert (result["name"], result["name_applied"]) == ("1", False)
    assert "playhead_restored" not in result
    assert "toggle" not in song.events


def test_create_locator_without_name_counts_as_applied(script):
    song = FakeSong()
    song.cue_class = ReadOnlyNameCue
    result = ok(run(make_instance(script, song), "create_locator", name="", time=4.0))
    assert result["requested_name"] is None
    assert result["name_applied"] is True


def test_create_locator_name_applied_when_names_are_writable(script):
    song = FakeSong()
    song.add_cue("1", 8.0)
    result = ok(run(make_instance(script, song), "create_locator", name="Drop", time=8.0))
    assert (result["name"], result["name_applied"]) == ("Drop", True)


def test_midi_clip_succeeds_when_the_song_shrinks_below_the_old_playhead(script):
    song = FakeSong([FakeTrack("Keys")])
    song.song_length = 280.0
    song.current_song_time = 248.0
    song.settle()
    song.shrink_on_move = 232.0
    result = ok(run(make_instance(script, song), "create_arrangement_midi_clip",
                    track_index=0, start=16.0, length=4.0))
    assert result["clip_index"] == 0
    assert result["playhead_restored"] is False
    assert song.current_song_time == 232.0
    assert song.undo_steps == ["begin", "end"]


def test_create_locator_succeeds_when_the_song_shrinks(script):
    song = FakeSong()
    song.song_length = 280.0
    song.current_song_time = 248.0
    song.settle()
    song.shrink_on_move = 232.0
    result = ok(run(make_instance(script, song), "create_locator", name="A", time=16.0))
    assert result["playhead_restored"] is False
    assert [c.time for c in song.cue_points] == [16.0]


def test_cue_delete_succeeds_when_the_song_shrinks(script):
    song = _cue_song()
    song.song_length = 280.0
    song.current_song_time = 248.0
    song.settle()
    song.shrink_on_move = 232.0
    result = ok(run(make_instance(script, song), "cue_point", action="delete", name="Intro"))
    assert result["playhead_restored"] is False
    assert sorted(c.time for c in song.cue_points) == [8.0, 24.0]


def test_audio_clip_restores_the_playhead(script, wav):
    track = AudioTrack()
    song = FakeSong([track])
    song.current_song_time = 40.0
    song.settle()
    result = ok(run(make_instance(script, song), "create_arrangement_audio_clip",
                    track_index=0, path=wav, start=32.0))
    assert result["playhead_restored"] is True
    assert song.current_song_time == 40.0
    _one_undo_step_around_ticks(song)


def test_set_current_song_time_reads_back_after_the_tick(script):
    song = FakeSong()
    song.current_song_time = 16.0
    song.settle()
    result = ok(run(make_instance(script, song), "set_current_song_time", time=40.0))
    assert result == {"current_song_time": 40.0}
    assert song.undo_steps == []
