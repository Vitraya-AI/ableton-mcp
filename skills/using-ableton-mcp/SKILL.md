---
name: using-ableton-mcp
description: Use whenever you are about to drive Ableton Live through the Ableton MCP 2.0 tools, and before any other Ableton skill acts. Covers the conventions every tool follows (0-based indices, Ableton note names where C3 = 60, beats vs bars, Session vs Arrangement clips, error codes, undo), how to find devices and set parameters, what Live 11 can and can't do, and the safe read-then-write workflow.
---

# Using Ableton MCP 2.0

The Ableton MCP 2.0 tools talk to a Remote Script running inside Live. This
skill is the ground truth for how they behave. The other Ableton skills
(`producer-mode`, `mixer-doctor`, `midi-cleanup`, …) assume you follow it.

## Start of every session

1. Call `get_remote_script_info`. Check `up_to_date: true` and note
   `live_version` and the `live_api` flags. They tell you what this Live can
   do. For example, `track_create_midi_clip: false` means Live 11, and
   `cue_point_set_name: false` means locators can't be renamed.
2. Call `get_session_info` (tempo, time signature, track count, scenes) and,
   for arrangement work, `get_arrangement_info`.
3. If a tool answers "Ableton Remote Script missing capability …", the Remote
   Script in Live is older than the server. Tell the user to reinstall it and
   restart Live (see `/ableton-debug`). Don't work around it.

## Conventions

| Topic | Rule |
|---|---|
| **Indices** | 0-based everywhere: the first track is `track_index=0`, the first clip slot is `clip_index=0`, Send A is `send_index=0`. |
| **Pitch** | MIDI numbers or note names in **Ableton's convention: C3 = 60** (middle C). C1 = 36 (kick on a Drum Rack), C-2 = 0, G8 = 127. Most theory books use C4 = 60, so **subtract one octave** from textbook note names. When in doubt, write the MIDI number. |
| **Time** | Positions and lengths are in **beats** (quarter notes). In 4/4, bar N starts at beat (N − 1) × 4. Arrangement tools also accept `start_bar` / `length_bars`, which follow Live's ruler and the song's time signature. |
| **Milliseconds** | beats = ms × BPM / 60000. At 120 BPM, 10 ms ≈ 0.02 beats. A 16th note is 0.25 beats. |
| **Velocity** | 1–127. Keep humanized values inside that range. |
| **Volume and sends** | Normalized 0.0–1.0: **0.85 = 0 dB**, 1.0 = +6 dB, 0.0 = −∞. The curve isn't linear in dB; move in small steps and read the result back. |
| **Pan** | −1.0 (left) to 1.0 (right). |
| **Device parameters** | Each parameter has its own `min`/`max` (from `get_device_parameters`). Values outside the range are rejected (`parameter_value_out_of_range`), never clamped. Switch-type parameters list their positions in `value_items`; set the index of the position you want. Parameters show Live's internal value, not the Hz/dB label, so for frequency-style controls, set the value, then tell the user what to check in the UI. |
| **Session vs Arrangement** | Clip tools default to Session clip slots. Pass `view="arrangement"` to `get_clip_notes`, `add_notes_to_clip`, `modify_clip_notes`, `remove_notes_from_clip`, `clear_notes_from_clip`, `delete_clip` and `set_clip_properties` to act on Arrangement clips; then `clip_index` is the clip's position in that track's list from `get_arrangement_info` (ordered by start time). |

## Read before write

- Always read state first (`get_track_info`, `get_clip_notes`,
  `get_device_parameters`, `get_rack_info`) and never assume a track, clip
  or device exists at an index. The user's set is not yours.
- `get_session_snapshot(include_notes=False)` returns the whole set in one
  call: every track's mixer, sends, devices and parameters, **plus the return
  tracks and the master chain**. Use it for audits.
- After Live restarts (for example after a Remote Script update), indices and
  note IDs may have changed. Read again before editing.

## Editing notes

- `add_notes_to_clip` **appends**; it never replaces existing notes.
- To change existing notes (humanize, quantize, transpose, voice-lead):
  `get_clip_notes` → change the fields you need → `modify_clip_notes` with
  each note's `note_id`. One call is one undo step.
- To remove: `remove_notes_from_clip` with a time/pitch window, or
  `clear_notes_from_clip` for everything.
- Notes support `probability` (0–1), `velocity_deviation` and
  `release_velocity` on Live 11+.

## Devices and racks

- **Find a device:** `get_browser_items_at_path("audio_effects")`,
  `"instruments"`, `"midi_effects"` or `"drums"` lists items with a `uri`;
  go deeper with `"audio_effects/<folder>"`. `get_browser_tree` is capped at
  depth 2 (deeper walks time out).
- **Load it:** `load_instrument_or_effect(track_index, uri)` appends it to
  the track's chain; the reply names the new device. Drum kits:
  `load_drum_kit`.
- **Inside racks:** `get_rack_info` lists chains, the devices in each chain,
  macros, and a Drum Rack's filled pads (each pad's `note` and name). Reach a
  device in a chain with `chain_index` + `chain_device_index`, one level deep.
- **Parameters by name:** `set_device_parameter(..., parameter_name="Ratio")`
  saves looking up indices. Names are case-insensitive but exact; a wrong name
  returns the list of valid ones.
- **Macro-mapped parameters** show `is_enabled: false`. The macro overrides
  them, so change the macro on the rack instead.
- **Bypass for A/B:** `set_device_enabled(..., enabled=false)`, then `true`.
- Device tools address **regular tracks only**. Master and return devices can
  be read (snapshot) but not changed; master volume and pan can
  (`set_master_volume`, `set_master_panning`).

## Errors

Every failure ends with `(code: …)`. Act on the code:

| Code | Meaning / what to do |
|---|---|
| `track_index_out_of_range`, `clip_index_out_of_range`, `device_index_out_of_range`, `chain_index_out_of_range`, `scene_index_out_of_range`, `send_index_out_of_range` | Re-read the set; indices changed or were wrong. |
| `clip_slot_empty`, `clip_slot_occupied` | Pick another slot or create a clip first. |
| `clip_overlap` | An Arrangement clip is already there. Choose another position, or pass `allow_overlap=True` only if the user wants layering. |
| `no_free_clip_slot` | Live 11 needs one empty Session slot on that track to build an Arrangement MIDI clip. Ask the user to free one or add a scene (`create_scene`). |
| `parameter_value_out_of_range`, `value_out_of_range` | Use the reported `min`/`max`. |
| `parameter_not_found` | Use one of the names in the message. |
| `not_a_rack`, `not_midi_track`, `not_audio_track`, `not_midi_clip`, `not_audio_clip`, `track_not_armable` | Wrong target type. |
| `note_id_not_found` | The clip changed since you read it. Call `get_clip_notes` again and use the fresh IDs. |
| `cue_not_found` | No locator with that name or time. `get_arrangement_info` lists them (on Live 11 they're named "1", "2", …). |
| `invalid_audio_file` | The path is missing, relative or not audio. Ask for an absolute path. |
| `not_supported` | This Live version or device can't do it. Tell the user; don't retry. |
| `timeout` | Live didn't respond in time. Read state to see what happened before retrying. |

## Undo is your safety net

- Every editing command is **one undo step**, including multi-step ones such
  as `create_arrangement_midi_clip`. Moving the playhead or jumping to
  locators adds none.
- After a change the user dislikes, call `undo` once. Offer this explicitly
  after anything destructive.

## What 2.0 can't do (tell the user; give the manual step)

| Not available | Manual step for the user |
|---|---|
| Create or delete **return tracks** | Right-click the mixer → Insert Return Track (a new Live set has Returns A and B). Then use `set_send_level`. |
| **Track colors** | Right-click the track → pick a color. (Clip colors *can* be set: `set_clip_properties` with `color`.) |
| Change devices on **master or return** tracks | Ask the user to drop the device on the master/return; you can then read it via `get_session_snapshot`. |
| **Sidechain routing** | In the Compressor, open the sidechain section and pick the source track. |
| **Automation** envelopes | Draw in Live's automation lane. |
| **Level meters / LUFS / spectrum** | Ask the user to read the meters or a metering device and tell you the numbers. |
| **Save presets**, **render/export**, **group tracks** | Cmd/Ctrl+S on the device; File → Export; Cmd/Ctrl+G. |
| **Rename locators on Live 11** | `create_locator` places it but Live keeps its number; `cue_point` can jump to it by that number. |
| **Plugin presets** | `navigate_device_preset` only works for plugins that expose a program list. |

## Operating principles

1. **Read before write.** Inspect state before creating or changing anything.
2. **Confirm destructive operations** (deleting tracks/clips/devices,
   clearing notes, overwriting) before doing them, and mention `undo`.
3. **One change at a time** for anything the user needs to hear (mix moves,
   humanization strength). Batch only mechanical scaffolding.
4. **Report what Live actually did.** Tool replies read values back from
   Live; quote those, not what you asked for.
5. **Co-pilot, not generator.** The user owns melody, emotion and structure.
