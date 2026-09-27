---
name: ableton-init
description: Bootstrap a fresh Ableton Live set with a labeled track layout, tempo, time signature and a starter scene using Ableton MCP 2.0, and walk the user through the return tracks and master chain it can't create itself. Use at the start of a new project.
---

# /ableton-init

Set up a clean, production-ready session. Run once per new project, before
recording or composing.

## What 2.0 sets up, and what the user adds

| Part | Who | How |
|---|---|---|
| Tempo, time signature | 2.0 | `set_tempo`, `set_time_signature` |
| Labeled tracks | 2.0 | `create_midi_track` / `create_audio_track`, `set_track_name` |
| First scene, named | 2.0 | `set_scene_name(0, "Idea")` |
| Section locators (optional) | 2.0 | `create_locator` (Live 11 keeps numeric names) |
| Return tracks | **User** | 2.0 can't create returns; a new Live set usually has Returns A and B |
| Devices on returns and master | **User** | 2.0 can't load devices there |
| Track colours | **User** | 2.0 can't set track colours |

## The layout

### Tracks (8, unarmed, no instruments loaded)

| # | Type | Name | Suggested colour | Purpose |
| --- | --- | --- | --- | --- |
| 0 | MIDI | Drums | Orange | Drum Rack / kit |
| 1 | MIDI | Bass | Yellow | Sub / 808 / bass |
| 2 | MIDI | Chords | Green | Pad, keys, harmony |
| 3 | MIDI | Lead | Purple | Melody |
| 4 | Audio | Vocals | Pink | Recording |
| 5 | Audio | Sample | Blue | Loops, foley |
| 6 | MIDI | Aux 1 | Light blue | Spare |
| 7 | MIDI | Aux 2 | Light blue | Spare |

### Returns (user adds; suggest these)

| Return | Device | Starting send |
| --- | --- | --- |
| A: Verb | Reverb (hall, ~2.5 s decay) | per track, starting at 0 |
| B: Delay | Ping Pong Delay (dotted 1/8, ~35% feedback) | per track, starting at 0 |
| C: Parallel | Glue Compressor (4:1, fast attack, auto release) | per track, starting at 0 |

### Master chain (user adds; suggest this)

EQ Eight (high-pass ~30 Hz) → Glue Compressor (2:1, slow attack, off until
mixdown) → Limiter (−1 dB ceiling, off until export).

## Workflow

1. `get_session_info`. If the set isn't empty, ask: *"The set has N tracks
   already. Add the layout anyway, or stop?"*
2. `set_tempo` and `set_time_signature` (default 120 BPM, 4/4, or the
   invocation's values).
3. Create the 8 tracks in order and name them. 2.0 creates tracks with
   `index=-1` (at the end); read back names with `get_track_info`.
4. `set_scene_name(0, "Idea")`.
5. Sends: leave them at 0. Don't auto-send to reverb.
6. Report, including the user's part:
   *"Set initialized at 120 BPM, 4/4: 8 labeled tracks and a scene called
   'Idea'. Your part: add Returns A–C with Reverb, Ping Pong Delay and Glue
   Compressor (right-click the mixer → Insert Return Track), optionally the
   master chain above, and colour the tracks as suggested. Save it as a
   template (File → Save Live Set as Default Set) if you want this every
   time."*

## Variations

- `/ableton-init 95 4/4`: set tempo and time signature
- `/ableton-init lofi`: 85 BPM, and suggest a softer reverb with no master limiter
- `/ableton-init cinematic`: 16 tracks grouped by section (strings, brass, woodwinds, percussion, choir, FX); the user groups them (Cmd/Ctrl+G), since 2.0 can't
- `/ableton-init minimal`: only tempo, time signature and the return/master suggestions

## Don'ts

- Don't arm any track.
- Don't load instruments; that's the user's per-project choice.
- Don't set sends above 0 by default.
- Don't suggest third-party plugins; stock Ableton only.
