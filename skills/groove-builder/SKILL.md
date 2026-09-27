---
name: groove-builder
description: Use when the user wants drum patterns by genre in Ableton Live - kick, snare, hi-hat, percussion. Examples - "give me a trap beat", "house drum pattern", "DnB drums at 174", "lo-fi drums with swing", "boom-bap pattern". Reads the Drum Rack's real pad notes and writes humanized MIDI with the Ableton MCP 2.0 tools; read using-ableton-mcp first.
---

# Groove Builder

Write idiomatic drum patterns by genre, with genre-appropriate
humanization, onto the user's drum track.

## Workflow

### 1. Genre and tempo

Required: genre. Tempo: the user's, or the genre default (`set_tempo` only
with their OK; changing tempo moves everything).

| Genre | Default tempo | Feel |
| --- | --- | --- |
| Lo-fi hip-hop | 70–90 | swung |
| Boom-bap | 85–95 | swung |
| Trap | 130–150 | half-time |
| House | 120–128 | straight |
| Tech house | 124–128 | straight |
| Techno | 125–135 | straight |
| DnB / Jungle | 165–180 | straight |
| UK garage | 130–138 | shuffled |
| Drill (UK) | 140–145 | half-time |
| Reggaeton | 95–100 | dembow |

### 2. Find the kit's real notes

`get_track_info` on the drum track to find the Drum Rack, then
**`get_rack_info`** on it. It lists every filled pad with its `note` and
name ("Kick", "Snare", "Hihat Closed"…). Use those notes; kits differ.

If there's no kit: offer to load one (`load_drum_kit`, or a kit from
`get_browser_items_at_path("drums")`). Most stock kits follow the GM layout
in Ableton names: kick C1 (36), snare D1 (38), clap D#1 (39), closed hat
F#1 (42), open hat A#1 (46). Still confirm with `get_rack_info`.

### 3. Write the pattern

The grids below are one bar of 16 steps. Step *n* (0–15) starts at
`start_time = bar_offset + n × 0.25` beats; use `duration` 0.25 (drums
ignore length on most kits). For several bars, repeat with bar offsets 0,
4, 8…

Clip: `create_clip(track_index, clip_index, bars × 4)` for Session, or
`create_arrangement_midi_clip` to put it straight on the timeline. Then
`add_notes_to_clip`.

#### Lo-fi hip-hop
```
Kick:  X . . . . . X . . . . . . . . .
Snare: . . . . X . . . . . . . X . . .
Hat:   X . X . X . X . X . X . X . X .   (8ths)
```
Kick 100–110 · snare 90–100, a touch late (+5 ms) · hats 65–85

#### Boom-bap
```
Kick:  X . . X . . X . . . X . . . . .
Snare: . . . . X . . . . . . . X . . .
Hat:   X X X X X X X X X X X X X X X X   (16ths)
```
Hats 50–80, humanize ±20

#### Trap (half-time)
```
Kick:  X . . . . . . X . . . . . . . .
Snare: . . . . . . . . X . . . . . . .   (beat 3 of the bar)
Hat:   X X . X X X . X X . X X X . X X   (rolling, with stutters)
```
Hat rolls: swap some 16ths for 32nd bursts (0.125-beat steps). Open hat
now and then on an off-beat. 808 held under it (separate track).

#### House
```
Kick:  X . . . X . . . X . . . X . . .   (4 on the floor)
Clap:  . . . . X . . . . . . . X . . .
Hat:   . . X . . . X . . . X . . . X .   (off-beat 8ths)
```
Kick 110 on the grid · clap 95 · hats tight

#### DnB
```
Kick:  X . . . . . . . . . X . . . . .
Snare: . . . . X . . . . . . . X . . .
Hat:   X X X X X X X X X X X X X X X X   (16ths)
```
Ghost snares at velocity 30–50 (2–3 per bar at most)

### 4. Humanize

Right after writing, read back with `get_clip_notes` and apply with
`modify_clip_notes` by `note_id` (see `midi-cleanup`). Timing in beats =
ms × BPM / 60000.

| Genre | Velocity | Timing | Swing |
| --- | --- | --- | --- |
| Lo-fi | ±20 | ±15 ms | 12% |
| Boom-bap | ±15 | ±10 ms | 6–8% |
| House / techno | ±5 | ±2 ms | 0% |
| Trap | loose hats, tight kick/snare | ±5 ms hats | 0–4% |
| DnB | loose hats, tight kick/snare | ±5 ms hats | 0% |

Swing: push every second 16th (steps 1, 3, 5…) later by swing% × 0.25
beats. For variety that doesn't change the notes, give ghost notes and
extra hats `probability` 0.6–0.8.

### 5. Fill (optional)

Two-bar pattern: bar 2 repeats bar 1 but its last one or two beats become a
fill (snare roll rising in velocity, tom run, hat stutter).

### 6. Confirm

Summarize before writing: *"Lo-fi at 90 BPM: kick on 1 and the & of 2,
snare on 2 and 4, 8th hats with 12% swing, ±15 velocity. Write it to a new
clip in slot 1 of Drums?"* Then offer to `fire_clip` it.

## Don'ts

- Don't write 100% on the grid except minimal techno or hard EDM.
- Don't overdo ghost notes (more than 4 per bar clutters).
- Don't override the user's tempo with a genre default.
- Don't write more than 8 bars at once; let them hear a section first.
- Don't assume pad notes; read them with `get_rack_info`.
