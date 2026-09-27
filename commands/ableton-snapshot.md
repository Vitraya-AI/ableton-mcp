---
name: ableton-snapshot
description: Save a human-readable Markdown snapshot of the current Ableton Live set - tempo, tracks, devices, key parameters, clips, arrangement, returns and master - using Ableton MCP 2.0. Use as a checkpoint before risky changes or to document a session.
---

# /ableton-snapshot

Read the whole set and write it to a Markdown file. Useful as:

- A checkpoint before risky changes (alongside `undo`, which only goes back one step at a time)
- A hand-over document for collaborators
- Versioning: "snapshot before the bridge rewrite"

## What it captures

One `get_session_snapshot(include_notes=False, include_params=True)` call
returns almost everything; add `get_arrangement_info` for bar numbers.

- **Session**: tempo, time signature, song length, loop, locators
- **Tracks**: name, MIDI/audio, volume (0.85 = 0 dB), pan, mute/solo/arm, sends
- **Devices**: each track's chain with the few parameters that matter (not every knob), including devices inside racks
- **Session clips**: name, length, note count
- **Arrangement clips**: name, start/end bar
- **Returns and master**: their device chains and faders
- **Scenes**: names

Track colours and meter levels aren't available to 2.0; leave them out.

## Output

Default: `./snapshots/<YYYY-MM-DD-HHMM>-<set-or-first-track-name>.md` in
the user's project folder (ask where if unclear). Never overwrite; always
timestamp.

```markdown
# Snapshot: my-track v3
**Date:** 2026-09-27 14:32 · **Tempo:** 95 BPM · **Time sig:** 4/4 · **Length:** 44 bars

## Tracks (8)

### 0. Drums (MIDI)
- Volume 0.80 · Pan 0.00 · Sends A 0.20, B 0.00
- Devices: Drum Rack (808 Core Kit, 16 pads) › Compressor (Ratio 3:1) › EQ Eight
- Session clips: slot 0 "Loop A" (4 bars, 64 notes)
- Arrangement: bars 5–20, 29–36

### 1. Bass (MIDI)
- …

## Returns
- A: Reverb (Decay Time …)

## Master
- Volume 0.85 · Glue Compressor (off) › Limiter (off)
```

## Workflow

1. `get_session_snapshot(include_notes=False)` and `get_arrangement_info`.
2. Summarize to Markdown: key parameters only (ratio, threshold, filter frequency, dry/wet, device on/off), note counts not note lists.
3. Write the file with your file tools. It lives on the user's disk, not in Live.
4. Confirm: *"Snapshot saved to ./snapshots/2026-09-27-1432-my-track.md"*

## Don'ts

- Don't dump every parameter; focus on what matters.
- Don't include note arrays; counts are enough.
- Don't overwrite existing snapshots.
