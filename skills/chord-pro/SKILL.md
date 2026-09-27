---
name: chord-pro
description: Use when the user wants to generate, voice, or modify chord progressions in Ableton Live. Examples - "give me a sad chord progression in C minor", "voice these chords for piano", "what's a good progression for cinematic music?", "extend this progression with more color tones". Writes with the Ableton MCP 2.0 note tools using Ableton note names (C3 = 60); read using-ableton-mcp first.
---

# Chord Pro

Generate or refine chord progressions with proper voicing, grounded in
music theory.

> **Octave convention.** Ableton names middle C **C3** (MIDI 60); most
> theory texts call it C4. Everything below uses **Ableton names** with MIDI
> numbers in brackets. When translating from a textbook, subtract one octave.

## Workflow

### 1. Ask if needed

Required: **key + mode**, **mood/genre**, **target instrument**. Optional:
length (default 4 chords), rhythm. If two are missing, ask in one sentence:
*"What key and what mood?"*

### 2. Choose a progression

| Mood / genre | Reliable progressions (in C / Cm) |
| --- | --- |
| Sad / cinematic | Cm – Ab – Eb – Bb (i–VI–III–VII), or Cm – Gm/Bb – Ab – Eb |
| Hopeful / pop | C – G – Am – F (I–V–vi–IV), or C – Am – F – G |
| Tension | Cm – F – Cm – G7 (i–iv–i–V), or Cm – Bb – Ab – G |
| Neo-soul / R&B | Cmaj7 – Em7 – Am7 – Dm7, or modal interchange |
| Lo-fi / chill | Cmaj7 – Fmaj7 – Bb7 – Eb7, or ii–V–I with extensions |
| Cinematic build | Cm – Ab – Fm – G (Aeolian + V) |
| EDM uplifting | Am – F – C – G (vi–IV–I–V) |
| Modal / Dorian | Cm – F – Gm – Cm (i–IV–v–i) |

### 3. Voice for the instrument

**Piano**
- Left hand: root + 5th (or octave) below middle C (below C3 = 60)
- Right hand: 3rd + 7th (or 3rd + 5th + 9th) around and above C3
- No close-position triad in the bass register

**String ensemble** (ranges in Ableton names)
- Cello: root, around C1–C2 (36–48)
- Viola: 5th or 3rd
- Violin 2: 3rd or 7th
- Violin 1: top colour tone (9, 11, 13)
- Ranges: Violin 1 G2–G5 (55–91), Violin 2 G2–D5 (55–86), Viola C2–A4 (48–81), Cello C1–C4 (36–72)

**Guitar**: idiomatic shapes, not piano voicings translated: open chords
for folk/indie, drop-2 for jazz, power chords (root + 5th) for rock.

**Pad / synth**: spread over two octaves; close voicing is fine in the
upper register; keep the root out of the bass synth's octave.

### 4. Add colour (optional)

- 9ths on major chords (Cmaj9)
- 11ths on suspended chords
- 7ths throughout for jazz/neo-soul
- Altered tones (b9, #11) on V chords for tension

### 5. Voice-lead between chords

Move each voice the smallest interval to the next chord; keep common tones;
avoid parallel fifths/octaves between the outer voices.

### 6. Write it

- New clip: `create_clip(track_index, clip_index, length)` with length =
  chords × beats per chord (4 per bar in 4/4). Or straight onto the timeline
  with `create_arrangement_midi_clip(start_bar=…, length_bars=…, notes=…)`.
- `add_notes_to_clip` with one note per voice: `pitch` (Ableton name or MIDI
  number), `start_time` (beat the chord starts), `duration` (usually the
  chord's length), `velocity` (~90).
- Revoicing an existing progression: `get_clip_notes`, then
  `modify_clip_notes` changing `pitch` by `note_id`. That keeps the user's
  timing and velocities.

## Don'ts

- Don't stack close-position triads without thinking about voice leading.
- Don't ignore instrument ranges. Violin 1 can't go below G2 (55).
- Don't put every voice in the same octave (mid-range mud).
- Don't use 7-note voicings unless the patch is rich enough to carry them.
- Don't use textbook octave numbers as-is; convert to Ableton's (C3 = 60).

## Example

> User: "Sad progression in F minor for piano"

- Progression: Fm – Db – Ab – Eb (i–VI–III–VII), 1 bar each, velocity 90.
- Bar 1 (beat 0), Fm: LH F1 C2 (41, 48) · RH Ab2 C3 Eb3 (56, 60, 63)
- Bar 2 (beat 4), Db: LH Db1 Ab1 (37, 44) · RH F2 Ab2 Db3 (53, 56, 61), Ab held
- Bar 3 (beat 8), Ab: LH Ab1 Eb2 (44, 51) · RH C3 Eb3 G3 (60, 63, 67), top voice rises
- Bar 4 (beat 12), Eb: LH Eb1 Bb1 (39, 46) · RH G2 Bb2 Eb3 (55, 58, 63), pulls back to Fm

`create_clip(t, 0, 16.0)`, then one `add_notes_to_clip` with all 20 notes
(`duration` 4.0 each).
