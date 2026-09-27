---
name: tempo-coach
description: Use when the user is unsure about tempo, time signature or rhythmic feel in Ableton Live. Examples - "what tempo should this be?", "should I switch to 3/4?", "is 95 BPM right for lo-fi?", "how do I make this feel less stiff rhythmically?". Mostly conversational; applies changes with set_tempo / set_time_signature from the Ableton MCP 2.0 tools; read using-ableton-mcp first.
---

# Tempo Coach

Help the user choose tempo, time signature and rhythmic feel. Mostly
conversation; few writes.

## Workflow

### 1. Understand the context

Read the current state with `get_session_info` (tempo, time signature).
Then pull from: genre, a reference track's tempo, mood (slow = reflective,
fast = energetic), and use case (sync to picture, DJ set, film cue).

### 2. Genre conventions

| Genre | Typical tempo | Notes |
| --- | --- | --- |
| Ambient | 50–70 | Often beatless; tempo sets the harmonic pulse |
| Cinematic underscore | 60–90 | Often rubato; click for sync, not feel |
| Lo-fi hip-hop | 70–90 | Half-time feel makes it feel slower |
| Boom-bap | 85–95 | ~90 is the classic pocket |
| Modern hip-hop | 75–115 | Trap is often half-time at 140–160 |
| Indie / folk | 80–120 | Rubato common |
| Pop | 95–130 | "100 BPM ballad", "118 dance-pop" |
| Rock | 100–160 | Power ballads 60–80 |
| House | 120–128 | 124 is the sweet spot |
| Tech house | 124–128 | |
| Techno | 125–135 | |
| Trance | 132–140 | |
| EDM / big room | 128 | Locked |
| Hardstyle | 150–160 | |
| Drum & bass | 165–180 | 174 is the default |
| Jungle | 160–175 | |
| Footwork | 160 | |

### 3. Time signature

| When | Time signature |
| --- | --- |
| Most popular music | 4/4 |
| Waltz / three-feel | 3/4 |
| Compound (jig, gospel triplet feel) | 6/8, 12/8 |
| Odd meters | 5/4, 7/8, 11/8 |
| Cinematic flexibility | 4/4 and 3/4 by section |

Unsure → **4/4** unless they want a three-feel. `set_time_signature` takes
numerator 1–99 and denominator 1, 2, 4, 8 or 16. It's song-wide; 2.0 can't
place time-signature changes mid-song, so the user adds those markers in the
Arrangement by hand.

### 4. Half-time vs full-time

- **Trap at 140**: tempo 140, snare on beat 3 of each bar (half-time)
- **DnB at 174**: full-time, snare on 2 and 4

"The drums feel slow but I want it fast" → full-time pattern, or faster hats
at the same tempo. The reverse → half-time the drums. Suggest the swap;
don't assume. `groove-builder` writes either.

### 5. Feel problems to flag

Ask the user to play the loop and listen for:

- **Dragging** (behind the click): tighten micro-timing / less late humanize
- **Rushing** (ahead of it): the opposite
- **Tempo doesn't fit the vibe**: a romantic progression at 140 → try 90 with a half-time feel

Timing fixes go through `midi-cleanup` (notes edited in place by ID).
Swing: push every second 16th later by swing% × 0.25 beats (8–15% for
hip-hop, 0% for EDM).

### 6. Recording with a click

- Subdivide 1/4 for slow tempos, 1/8 for fast
- 1–2 bars of count-in
- These are Live's metronome settings; the user sets them (2.0 has no
  metronome control).

### 7. Apply (with approval)

`set_tempo(bpm)` and `set_time_signature(numerator, denominator)`. Both
replies report what Live now has; quote them. `undo` reverts either.

## Don'ts

- **Don't change tempo without explicit approval.** Warped audio and
  arrangement positions shift with it.
- Don't suggest extremes (40 or 220 BPM) without checking that's intended.
- Don't assume 4/4 if the loop is in a three-feel.

## Common scenarios

**"My beat feels stiff"** → humanize (`midi-cleanup`) or add swing
(8–15% on 16ths for hip-hop; none for EDM).

**"Too slow, but I don't want to speed up"** → half-time drums flipped to
full-time at the same tempo.

**"Can I change time signature mid-song?"** → Yes, at section boundaries
(intro 4/4 → bridge 3/4 → chorus 4/4). The user places the time-signature
markers in the Arrangement; 2.0 only sets the song's main signature.
