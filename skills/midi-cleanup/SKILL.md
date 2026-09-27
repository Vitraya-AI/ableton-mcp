---
name: midi-cleanup
description: Use when the user asks to humanize a MIDI part, fix voice leading, quantize, clean up timing, fix stuck or duplicate notes, or polish a MIDI clip in Ableton Live. Examples - "humanize this hat", "voice these chords better", "the timing is too stiff", "fix the voice leading on the strings". Edits notes in place by note ID with the Ableton MCP 2.0 tools; read using-ableton-mcp first.
---

# MIDI Cleanup

Polish a MIDI clip the user wrote or recorded: make it feel human,
voice-led and rhythmically right, without rewriting their musical intent.

2.0 edits notes **in place by note ID**, so every cleanup is: read the
notes → compute the changes → send back only the changed fields. One
`modify_clip_notes` call is one undo step.

## Workflow

### 1. Identify the target clip

If ambiguous, ask: *"Which clip: the lead on track 3 or the chords on track 5?"*
Session clip: `track_index` + slot `clip_index`. Arrangement clip: add
`view="arrangement"` and use its index from `get_arrangement_info`.

Read it: `get_clip_notes`. Every note comes with `note_id`, `pitch`,
`start_time`, `duration`, `velocity`, `mute` and, on Live 11+,
`probability`, `velocity_deviation`, `release_velocity`. Note the count,
range and rhythmic density. Get the tempo from `get_session_info`; you'll
need it to turn milliseconds into beats (**beats = ms × BPM / 60000**).

### 2. Pick the cleanup

#### A. Humanize velocity
For drums, hats, percussion or any stiff rhythmic part.

- Range: ±10–15 for hats/percussion, ±8–12 for drums
- Preserve accents: notes above 100 stay loud, below 40 stay quiet
- Stay within 1–127
- Alternative that keeps the part identical on disk: set
  `velocity_deviation` (Live randomizes on each playback) instead of
  rewriting velocities. Offer this when the user wants "alive but
  consistent".

#### B. Humanize timing
For piano, guitar or string parts that sound stiff.

- ±8–20 ms (convert to beats at the song tempo), slightly more on off-beats
- Rolled chords: stagger attacks 5–15 ms (top note latest), only if wanted
- Leave the downbeat of bar 1 exactly on the grid; it's the anchor
- Don't move a note before 0 or past the clip end

#### C. Probability (Live 11+)
For "make the hats less repetitive": give ghost notes or off-beat hats
`probability` 0.5–0.8 instead of deleting them. Keep downbeats at 1.0.

#### D. Voice-leading fix
For chords in root-position block voicing.

- Keep the bass note in the bass voice
- Move upper voices by the smallest interval to the next chord (step or common tone)
- Max an octave between adjacent upper voices
- Avoid parallel fifths/octaves between outer voices
- **Instrument ranges, in Ableton note names (C3 = 60):**
  Violin 1 G2–G5 (MIDI 55–91), Violin 2 G2–D5 (55–86), Viola C2–A4
  (48–81), Cello C1–C4 (36–72), Double bass E0–A2 (28–57). Textbooks give
  these an octave higher (G3–G6…) because they use C4 = 60.

Apply with `modify_clip_notes`, changing only `pitch` on the moved voices.

#### E. Quantize (intelligently)
Never 100% by default. That kills feel.

- Default strength 75% toward the 16th grid (0.25 beats):
  new_start = start + strength × (nearest_grid − start)
- Swung genres (hip-hop, lo-fi): 60–70% toward a swung grid
- Tight EDM/house: 90–100% on percussion only, looser on chords/leads
- Keep grace notes and pickups (notes within ~30 ms ahead of a grid line)

#### F. Stuck / duplicate notes
- Duration under ~5 ms → remove (`remove_notes_from_clip` with a narrow
  window on that pitch and time)
- Same pitch overlapping → trim the first note's `duration` so they no
  longer overlap
- Notes held longer than 2 bars in a fast part → ask the user

### 3. Preview

Summarize before writing:

> *"32 hat notes: velocity spread ±12 around the current values, keeping
> the 4 accents at 110; off-beats nudged +6 ms (0.01 beats at 95 BPM).
> Apply?"*

### 4. Apply

One `modify_clip_notes` call with every changed note (`note_id` plus only
the fields that change). If it returns `note_id_not_found`, the clip changed
since you read it; read again and recompute.

### 5. Confirm

Say what changed, ask the user to listen, and offer "more/less" or `undo`
(one step reverts the whole cleanup).

## Don'ts

- **Don't change pitches** except for voice leading, and never the melody/lead voice.
- **Don't humanize beyond ±25 velocity or ±25 ms.** That just sounds sloppy.
- **Don't quantize at 100%** unless asked.
- **Don't voice-lead a melody.** It's for chords, pads and inner voices.
- **Don't touch velocity-127 hits.** They're intentional accents.
- **Don't clear and re-add notes** to make an edit; that loses note IDs and
  probability data. Use `modify_clip_notes`.

## Example

> User: "The hi-hat sounds too robotic, humanize it"

1. `get_clip_notes(track 2, clip 0)`: 32 16th notes, all velocity 100, perfectly on grid. Tempo 90 BPM.
2. Plan: velocities 88–112, off-beat 16ths +8 ms (8 × 90 / 60000 = 0.012 beats), ~4% swing on the "e" and "a" 16ths.
3. Preview, get approval.
4. `modify_clip_notes` with 32 entries: `{"note_id": …, "velocity": …, "start_time": …}`.
5. "Done. If it's still too tight, say 'more humanize' and I'll widen it to ±18. `undo` reverts it."
