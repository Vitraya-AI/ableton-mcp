# Manual Smoke Tests

The automated tests replace Live with fakes. Run these against a real Live set
before relying on the note-editing, mixer and scene tools, and after any change
to the Remote Script.

## Setup

1. Run `ableton-mcp-install-script`, then restart Live.
2. Open a fresh, empty Live set.
3. Start the MCP server and call `get_remote_script_info`. Confirm it reports
   script version 1.10.1 and `up_to_date: true`. Confirm `live_version` shows
   your Live build and `live_api` lists the version-dependent APIs (on Live 11
   expect `track_create_midi_clip: false`, `song_begin_undo_step: true`,
   `automation_envelope_insert_step: true`).
4. Keep Live visible so you can confirm each change in the UI.

## Note editing (Live 11+ note IDs)

1. Create a MIDI track and a 4-bar clip. Call `add_notes_to_clip` with a few
   notes, using note names for some pitches (`"C3"`, `"Eb3"`) and
   `probability: 0.5` on one note. Confirm the notes land on the right keys
   (C3 = MIDI 60) and the chance marker appears on that note.
2. Call `add_notes_to_clip` again. Confirm the first notes are still there.
3. Call `get_clip_notes`. Confirm each note has a `note_id`.
4. Call `modify_clip_notes` on one note ID, changing `velocity`, then again
   changing `pitch`. Confirm both changes stick and other notes are untouched.
   (Confirmed on Live 11.3: `apply_note_modifications` accepts pitch changes.)
5. Call `remove_notes_from_clip` with a narrow window, for example
   `from_time=4, time_span=4, from_pitch="C3", pitch_span=1`. Confirm only
   matching notes go.
6. Call `clear_notes_from_clip`. Confirm the clip stays but is empty.

## Session editing

1. Call `duplicate_clip` into an empty slot on the same track. Confirm a copy
   appears. Call it again onto that slot and confirm a `clip_slot_occupied`
   error.
2. Call `delete_track` on a track that already existed, then `undo`, then
   `redo`. Confirm Live removes, restores and removes it again.
3. Create a throwaway track and delete it straight away, then call `undo`.
   Confirm the track comes back. Before 1.8.1 each MCP command was not its own
   undo step, so Live merged the create and delete into nothing and undo
   reached one step further back instead. (Confirmed fixed on Live 11.3:
   `Song.begin_undo_step` is available.)
4. Call `set_time_signature` with `3` / `4`. Confirm Live shows 3/4.

## Mixer and devices

1. Call `set_track_volume` with `0.85`. Confirm the fader reads 0 dB.
2. Call `set_track_panning`, `set_track_mute`, `set_track_solo` and
   `set_track_arm`. Confirm each control changes.
3. There is no tool for grouping, so select two tracks in Live and press
   Cmd+G. Call `get_track_info` on the group and confirm `is_group_track: true`
   and `can_be_armed: false`, and `is_grouped: true` on its members. Then call
   `set_track_arm` on the group and confirm a `track_not_armable` error, with
   the next call still answering. (A group also reports `is_audio_track: true`;
   that is Live's `has_audio_input`, so rely on `is_group_track` instead.)
4. Call `set_send_level` on a send whose return track exists (there is no
   tool to add a return track). Confirm the send knob moves.
5. Call `set_master_volume` and `set_master_panning`.
6. Load an instrument, call `get_device_parameters`, then `set_device_parameter`
   inside the reported range. Then try a value above `max` and confirm a
   `parameter_value_out_of_range` error with the parameter unchanged.

## Arrangement (1.10.1)

Start with at least one MIDI track (with an instrument and one empty Session
slot) and one audio track. Clear leftovers from earlier runs first: stray
locators, the loop, test clips. Live restarts to load a new Remote Script, so
rebuild the test tracks after each update.

1. Call `get_arrangement_info`. Confirm song length, loop, time signature,
   cue points and each track's arrangement clips, with bar numbers that match
   Live's ruler. A clip's `length` is its span on the timeline; `loop_length`
   is Live's loop length (they differ for a looped clip).
2. Call `create_arrangement_midi_clip` on the MIDI track with `start_bar=5`,
   `length_bars=2` and a few notes (use note names). Confirm the clip appears
   at bar 5, two bars long, with the notes, and that the temporary Session clip
   is gone. On Live 11 the result ends with `(method: session_fallback)`.
   The playhead must be back where it was before the call.
3. Call it again overlapping that clip: expect `clip_overlap`. Call `undo`
   once and confirm the whole first clip disappears in one step (no leftover
   Session clip).
4. Call `get_clip_notes` / `add_notes_to_clip` / `modify_clip_notes` /
   `remove_notes_from_clip` with `view="arrangement"` on the new clip; confirm
   each change lands on the Arrangement clip, not a Session clip.
5. Call `set_clip_properties` with `view="arrangement"` and
   `{"name": "Verse", "muted": true, "looping": true, "loop_start": 0, "loop_end": 4}`.
   Confirm in Live. Then try `{"gain": 0.5}` on the MIDI clip: expect
   `not_audio_clip`.
6. Call `create_arrangement_audio_clip` on the audio track with a real `.wav`
   at `start_bar=9`. Confirm the clip lands at bar 9. Try a missing file:
   `invalid_audio_file`.
7. Park the playhead somewhere else (e.g. bar 20), then create two locators
   with `create_locator` at bar 1 (time 0) and bar 5 (time 16). Both must land
   at those times with those names — not at the playhead — and the playhead
   must return to bar 20. Then `cue_point` with `jump` by name, `next`,
   `previous` (each reports the cue it actually landed on), and `delete` by
   name: only that locator disappears, no new one appears, jumps add no undo
   steps, and one `undo` restores the deleted locator. (Before 1.10.1 these
   acted at the old playhead position.)
8. Call `set_arrangement_loop` with `start_bar=5`, `length_bars=4`,
   `enabled=true`; confirm the loop brace and that the reply says the loop is
   on.
9. Call `delete_clip` with `view="arrangement"` on the audio clip; confirm it
   is removed from the Arrangement only.

## Scenes

1. Call `get_session_info`. Confirm `scene_count` and `scenes` are present.
2. Call `create_scene`, then `set_scene_name`. Confirm the new row is named.
3. Put clips in that row and call `fire_scene`. Confirm the row launches.
4. Call `delete_scene` and confirm the row is removed.

## Errors and connection

1. Call `create_audio_clip` on an empty audio slot with a path that does not
   exist, then with a text file renamed to `.wav`. Both should end with
   `(code: invalid_audio_file)`. Then a real `.wav`: the clip appears.
2. Call `set_track_mute` with a track index that does not exist. Confirm the
   error ends with `(code: track_index_out_of_range)`.
3. Immediately call `get_session_info`. Confirm it answers without a reconnect:
   the MCP server log (Claude Desktop: `~/Library/Logs/Claude/mcp-server-AbletonMCP.log`)
   shows no new "Connected to Ableton" line.

## Browser

1. Call `get_browser_tree` with `category_type="instruments"` and
   `max_depth=2`. Confirm nested folders come back. On a stock library this
   took 6.4 s and 31 KB; the log line "Received complete response" gives the
   size, and its timestamp against "Sending command" gives the duration.
2. `max_depth` is capped at 2: depth 3 took 9.8 s and 634 KB, against a 10 s
   read timeout. Asking for 3 returns the depth-2 tree with a "max_depth
   capped at 2" line.

## Live API dump (developer)

1. With Live running, run
   `uv --directory /Volumes/ADrive/Gits/ableton-mcp-vitraya run ableton-mcp-dump-live-api`.
   It writes `docs/live-api/<your Live version>/` with one JSON file per
   module and an `index.md` (gitignored).
2. Open `index.md` and confirm `Track`, `Song`, `Clip` and `ClipSlot` list
   members with signatures in the Doc column. Check whether `ClipSlot`
   has `create_audio_clip` and note the result in
   `docs/extended-features-plan.md` (it decides a Phase 1 detail).
3. Check the MCP server log: each module request should finish well inside
   the 60 s allowance.
