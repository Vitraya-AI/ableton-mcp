# Extended Features Port — Plan

Status: **Phase 0 done (Remote Script 1.9.0); next is Phase 1** (written 2026-09-26). Work happens on the
`extended-features` branch. This document is the hand-off: a new session should
be able to start Phase 0 from here without the conversation that produced it.

## Goal

Bring the useful parts of `ableton-mcp-extended` (local copy at
`~/claude/ableton-mcp-extended`, upstream `uisato/ableton-mcp-extended`) into
this fork, adapted to this fork's conventions and to **Ableton Live 11.3**,
which is what the user runs.

Scope chosen by the user: **Phase 0 (groundwork), Phase 1 (arrangement),
Phase 2 (devices and racks).** Phases 3–4 below are recorded for later, not
part of this effort.

## Where things stand

- `main` has the spec improvements (PR #1): note editing by note ID, mixer,
  scenes, undo/redo, structured error codes, per-command undo steps, group-track
  fields. Remote Script **1.8.1**, verified end to end on Live 11.3 with
  `docs/manual-smoke-tests.md`.
- `extended-features` = `main` + `c254b61` (uv.lock regenerated in the current
  uv format; plain `uv run` no longer rewrites it).
- 189 tests pass: `uv run --with pytest python -m pytest -q`.
- The dataset/telemetry code from upstream is kept but hidden from the model by
  `MCP_Server/dataset_visibility.py`, so the fork stays mergeable with upstream.

## Decisions (and why)

| Decision | Reason |
|---|---|
| **Keep 0-based indices** | The extended repo is 1-based. Switching would break all 56 existing tools and diverge from upstream. |
| **Consolidate tools** | The extended repo's one-tool-per-action split is not required by Live (e.g. its enable/disable tools call one handler). Every tool costs context in every session, so group actions where it reads naturally. |
| **Positions in beats**, with an optional `bar` input | Existing tools use beats. `bar` matches Live's ruler (bar 1 = beat 0) and is converted server-side using the time signature. |
| **Check Live's API at runtime, not by assumption** | Public references don't state the exact Live build, and one conflicts with the fork (see below). Tools must gate optional APIs on what the running Live actually has. |
| **Don't copy the structure-void reference into the repo** | It is CC BY-NC-SA 4.0. Cite it; generate our own API dump from the user's Live instead (Phase 0). |
| **Skip** 1-based indexing, the UDP hybrid server (mostly placeholder handlers), the XY mouse controller (demo), ElevenLabs (a separate MCP server — add it alongside if wanted), `get_track_volume` (covered by `get_track_info`), `get_track_deletion_status` (last-track guard already exists), view zoom/scroll controls (little use to an AI) | Low value, already covered, or harmful to compatibility. |

## Live API findings (Live 11.3)

Sources: runtime captures at
`https://midiremotescripts.structure-void.com/reference/live11/Live.<Module>.runtime/`
and the generated 11→12 diff at
`https://midiremotescripts.structure-void.com/guides/runtime-changes-11-to-12/`
("Added in Live 12" = absent on Live 11).

Every Live API call in the extended Remote Script was checked, class by class,
against the "Added in Live 12" list:

| API | Live 11.3 | Consequence |
|---|---|---|
| `Track.create_midi_clip(start, length)` | ❌ Live 12 only | Arrangement MIDI clips need a fallback on 11 (see Phase 1). |
| `Track.create_audio_clip` / `ClipSlot.create_audio_clip` | ⚠️ Conflicting | Listed in the "Live 11" capture; the fork's `create_audio_clip` docstring says 12.0.5+. Resolve with the Phase 0 probe. Not needed for phases 0–2. |
| `Track.duplicate_clip_to_arrangement`, `Track.delete_clip`, `Track.arrangement_clips` | ✅ | |
| `Song.cue_points`, `set_or_delete_cue`, `jump_to_next_cue`, `jump_to_prev_cue`, `CuePoint.jump` | ✅ | |
| `Song.loop`, `loop_start`, `loop_length`, `song_length`, `back_to_arranger` | ✅ | (`Track.back_to_arranger` is Live 12; the extended repo uses the Song one.) |
| `Clip`: `muted`, `color`, `looping`, `loop_start/end`, `start_marker`, `gain`, `pitch_coarse/fine`, `warping`, `warp_mode`, `is_arrangement_clip` | ✅ | |
| `Clip.automation_envelope`, `create_automation_envelope`, `clear_envelope`, `clear_all_envelopes`; `AutomationEnvelope.insert_step`, `value_at_time` | ✅ | Phase 4 is feasible on 11 (`insert_step` moved to `Envelope` in 12 — handle both). |
| `Song.begin_undo_step` / `end_undo_step` | ✅ | Verified live on 11.3 (1.8.1 undo fix). |
| `Device.parameters`, `can_have_chains`, `can_have_drum_pads`, `class_name`; `RackDevice.chains`, `drum_pads`, `visible_drum_pads`; `Chain.devices`, `Chain.delete_device`; `Track.delete_device`; `DrumPad.note/chains/mute/solo` | ✅ | |
| `Device.is_active` | ✅ read-only | Toggle a device with its "Device On" parameter (`parameters[0]`), as the extended repo does. |
| `PluginDevice.presets`, `selected_preset_index` | ✅ | Preset browsing only exists for plugin devices. |

## Phase 0 — Groundwork ✅ done (Remote Script 1.9.0)

Implemented as specified below, plus a server fix: `receive_full_response`
no longer resets every command's socket timeout to 15 s, so each command
keeps its own (reads 10 s, edits 15 s, `create_audio_clip` 65 s,
`dump_live_api` 60 s). Helpers now available: `script_handshake.live_api_available(flag)`,
`script_handshake.live_version()`, and `MCP_Server/timing.py`
(`resolve_position`, `resolve_length`, `bar_to_beat`, `beat_to_bar`).
**Still to do in Live:** run the Phase 0 smoke checks and the API dump; record
whether `ClipSlot.create_audio_clip` exists on 11.3.

1. **Live version and API flags in the handshake.** `get_script_info` gains
   `live_version` (from `Live.Application.get_application().get_major_version()`
   / `get_minor_version()` / `get_bugfix_version()`) and `live_api` flags, e.g.
   `track_create_midi_clip`, `track_create_audio_clip`,
   `clip_slot_create_audio_clip`, `envelope_insert_step`,
   `song_begin_undo_step`. Probe with `hasattr` on the class
   (`Live.Track.Track`, etc.), guarded so a missing `Live` module (tests) yields
   an empty dict. The server exposes these through `get_remote_script_info`.
2. **API dump command (developer only).** A read command `dump_live_api` that
   walks the `Live` module (classes, members, Boost.Python docstrings, which
   carry signatures) and returns JSON. A small server-side script or tool
   writes it to a **gitignored** `docs/live-api/` folder, giving an exact spec
   for the user's Live build. Not advertised as a normal MCP tool (keep it out
   of the tool list, or hide it like the dataset tools).
3. **Bar ↔ beat helpers** in `server.py`: `bar_to_beat(bar, numerator,
   denominator)` / `beat_to_bar(...)` using the song's current time signature
   (fetched once per call from `get_session_info`). Beats per bar =
   `numerator * 4 / denominator`. Bar 1 = beat 0. Reject bar < 1.

## Phase 1 — Arrangement (Remote Script 1.9.1)

Existing arrangement tools in the fork, keep as they are: `create_locator`,
`duplicate_to_arrangement`, `get_arrangement_clips`, `set_arrangement_time`,
`set_arrangement_clip_name`, `switch_to_arrangement_view`. Arrangement clips
are addressed by their index in `track.arrangement_clips` (ordered by start
time), matching `get_arrangement_clips`.

| New / changed | Behaviour |
|---|---|
| `get_arrangement_info` (new, read) | Song length, loop (on/start/length), tempo, time signature, cue points (name + time, sorted), and per track: name, index, and its arrangement clips (index, name, start, end, length, is_midi, muted). One call gives an overview of the whole timeline. |
| `cue_point(action, name=None, time=None)` (new) | `action`: `jump` (by name or nearest time), `next`, `previous`, `delete` (by name or time). `create_locator` stays for creating. Deleting uses `set_or_delete_cue` after moving to the cue's time, restoring the playhead afterwards. |
| `set_arrangement_loop(enabled, start=None, length=None, start_bar=None, length_bars=None)` (new) | Validates length > 0 and start ≥ 0. |
| `create_arrangement_midi_clip(track_index, start, length, notes=None, name=None)` (new; `start_bar`/`length_bars` alternatives) | Live 12: `track.create_midi_clip`. **Live 11 fallback:** find an empty Session slot on that track (error `no_free_clip_slot` if none, or create a scene and remove it afterwards), `create_clip(length)`, add notes, `track.duplicate_clip_to_arrangement(clip, start)`, delete the temporary Session clip — all inside one undo step. Refuse overlapping an existing arrangement clip unless `allow_overlap=True` (extended's `_check_overlap` idea). Returns the new clip's arrangement index. MIDI tracks only. |
| Note tools gain `view="session" \| "arrangement"` | `get_clip_notes`, `add_notes_to_clip`, `modify_clip_notes`, `remove_notes_from_clip`, `clear_notes_from_clip`. With `view="arrangement"`, `clip_index` indexes `track.arrangement_clips`. One shared resolver in the Remote Script (`_resolve_clip(track_index, clip_index, view)`). Default stays `session`, so existing callers are unaffected. |
| `delete_clip` gains `view` | Arrangement deletion uses `track.delete_clip(clip)`. |
| `set_clip_properties(track_index, clip_index, properties, view="session")` (new) | Sets several properties in one call from an allowlist: `name`, `muted`, `color`, `looping`, `loop_start`, `loop_end`, `start_marker`, `end_marker`, `gain`, `pitch_coarse`, `pitch_fine`, `warping`, `warp_mode`. Audio-only keys (`gain`, `pitch_*`, `warp*`) error with a clear code on MIDI clips. Unknown keys → `invalid_value` listing the allowed ones. Returns the values read back. |

## Phase 2 — Devices and racks (Remote Script 1.10.0)

**Device addressing inside racks.** Add optional `chain_index` and
`chain_device_index` to `get_device_parameters`, `set_device_parameter`,
`set_device_enabled`, `delete_device`. Resolution:
`track.devices[device_index]` → if `chain_index` given, it must be a rack
(`can_have_chains`), then `chains[chain_index].devices[chain_device_index or 0]`.
The extended repo only reaches the first device in a chain; this reaches any.
One resolver: `_resolve_device(track_index, device_index, chain_index=None,
chain_device_index=None)` raising `CommandError` with
`device_index_out_of_range` / `chain_index_out_of_range` / `not_a_rack`.
(Nested racks deeper than one level: out of scope, note it in docstrings.)

| New | Behaviour |
|---|---|
| `get_rack_info(track_index, device_index)` (read) | For a rack: macros (name, value, min, max), chains (index, name, mute, solo, devices with index/name/class_name/type), and for drum racks the **filled** pads only (note, name, mute, solo, chain devices). Replaces extended's `get_chain_info` + `get_drum_pad_info`, and exposes the fork's existing `_inspect_rack` data (merge rather than duplicate). |
| `set_device_enabled(track_index, device_index, enabled, chain_index=None, chain_device_index=None)` | Sets the "Device On" parameter (`parameters[0]`) to its max/min. Verify the parameter's name is "Device On" and error otherwise rather than silently changing another parameter. |
| `delete_device(track_index, device_index, chain_index=None, chain_device_index=None)` | `track.delete_device(i)` or `chain.delete_device(i)`. Returns the deleted device's name. |
| `navigate_device_preset(track_index, device_index, direction="current", ...)` | `next` / `previous` / `current` (read). Plugin devices only (`presets` exists); others → `invalid_value` "has no presets". |

Consider (only if cheap): `set_device_parameter` accepting a parameter
**name** as an alternative to `parameter_index`.

## Later (not in this effort)

- **Phase 3 — third-party plugins:** `list_external_plugins` /
  `load_external_plugin`. The extended repo walks the browser with one socket
  request per folder (up to 2,000); do the walk inside the Remote Script in a
  single request, cache server-side. Optional friendly parameter aliases
  (`MCP_Server/plugin_aliases.py` in the extended repo).
- **Phase 4 — automation points:** write real curves with
  `AutomationEnvelope.insert_step` (Live 11) / `Envelope.insert_step` (Live 12)
  for Session and Arrangement clips; read with `value_at_time`. The extended
  repo only creates/clears empty envelopes.
- Server reconnect-and-retry for **read** commands after Live restarts (first
  call currently fails once). Deferred by the user.

## Conventions checklist (every new command)

Remote Script (`AbletonMCP_Remote_Script/__init__.py`):
- [ ] Handler method; raise `CommandError(message, code)` for expected failures.
- [ ] Add to `_read_handlers` or `_main_thread_handlers`.
- [ ] Editing commands: add to `_UNDOABLE_COMMANDS` (one undo step each).
- [ ] Add to `SCRIPT_CAPABILITIES`.
- [ ] Python 3.7 syntax only (Live 11's interpreter): no f-strings, no walrus.
      Check: `python3 -c "import ast;ast.parse(open(p).read(), feature_version=(3,7))"`.
- [ ] Bump `SCRIPT_VERSION` and `EXPECTED_REMOTE_SCRIPT_VERSION`
      (`MCP_Server/remote_script_install.py`) together.
- [ ] Copy to `MCP_Server/bundled_ableton_remote_script/AbletonMCP_init.py`
      (a test enforces they are identical).

Server (`MCP_Server/server.py`):
- [ ] Tool with `@mcp.tool()`, `@telemetry_tool` or `@rich_telemetry_tool`
      (names/notes), `@trajectory_tool`, and a trailing `user_prompt: str = ""`
      parameter (hidden from the model automatically).
- [ ] Send through `_send_gated(...)` so old Remote Scripts get a clear
      "missing capability" message.
- [ ] Mutating commands: add to `is_modifying_command`; add the tool name to
      `MODIFYING_TOOLS` in `MCP_Server/dataset/trajectory_decorator.py`; add any
      new structural parameter names to `_PARAM_KEYS` there.
- [ ] Pitches through `_parse_pitch` / `_parse_note_pitches`.

Tests and verification:
- [ ] Server-side tests (pattern: `tests/test_session_controls.py`).
- [ ] Remote Script tests with fake Live objects (pattern:
      `tests/test_remote_script_handlers.py`); extend the fakes as needed.
- [ ] Confirm new tests fail against the previous Remote Script.
- [ ] Add Live checks to `docs/manual-smoke-tests.md`; the tester runs them
      after `ableton-mcp-install-script` + restarting Live.
- [ ] One commit per phase.

## Working environment notes

- Repo: `/Volumes/ADrive/Gits/ableton-mcp-vitraya`. `origin` =
  `Vitraya-AI/ableton-mcp` (the user's fork). `upstream` =
  `ahujasid/ableton-mcp`, push disabled. **Never open PRs against ahujasid** —
  GitHub's "Compare & pull request" on a fork defaults to the parent.
- Commits must be authored as **codycrypto** (repo-local
  `user.email = 85378149+codycrypto@users.noreply.github.com`, credential
  username pinned). The global git identity is the user's work account.
- Server log (Claude Desktop): `~/Library/Logs/Claude/mcp-server-AbletonMCP.log`.
  Useful for timings and reconnects.
- Install the Remote Script into Live:
  `uv --directory /Volumes/ADrive/Gits/ableton-mcp-vitraya run ableton-mcp-install-script`,
  then restart Live. Handshake must report the new version.
- The README is updated once at the end of the day's work, not per change.
