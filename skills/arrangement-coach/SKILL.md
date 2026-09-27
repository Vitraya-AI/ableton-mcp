---
name: arrangement-coach
description: Use when the user has a Session-view loop and wants a full Arrangement, wants sections built (intro/verse/drop/break/outro), or wants to extend a short idea into a full-length track in Ableton Live. Examples - "turn this loop into a full song", "build me a 2-minute arrangement from this", "promote session to arrangement". Uses the Ableton MCP 2.0 arrangement tools; read using-ableton-mcp first.
---

# Arrangement Coach

Promote Session-view loops into a structured Arrangement. The user owns the
musical content; you make the structural decisions and place the clips.

## How 2.0 builds an arrangement

- **Sections are made by placing or leaving out clips**, track by track.
  Track mute applies to the whole song, and 2.0 can't write automation, so
  "drums out in the intro" means *don't place the drum clip there*.
- `duplicate_to_arrangement(track_index, clip_index, destination_time)`
  copies a Session clip to the timeline at a beat position, **one copy per
  call, one clip length long**. A 4-bar loop filling a 16-bar section needs
  4 calls (at +0, +16, +32, +48 beats).
- `create_arrangement_midi_clip(track_index, start_bar=…, length_bars=…,
  notes=[…])` writes new material straight onto the timeline, such as fills
  or variations. On Live 11 it needs one empty Session slot on that track.
- Positions are beats; bar N in 4/4 = (N − 1) × 4. The arrangement tools
  also accept bars directly.

## Workflow

### 1. Read what they have

- `get_session_info`: tempo, time signature, scenes
- `get_track_info` per track: which Session slots hold clips, and their lengths
- `get_arrangement_info`: is the Arrangement empty? If not, ask before
  adding (`clip_overlap` protects existing clips, but ask anyway)

### 2. Choose a structure (ask once)

| Template | Length | Sections (bars) |
| --- | --- | --- |
| **Pop** | ~3 min | Intro 8 → V1 16 → Pre 8 → Chorus 16 → V2 16 → Pre 8 → Chorus 16 → Bridge 8 → Chorus 16 → Outro 8 |
| **EDM** | ~4 min | Intro 16 → Build 16 → Drop 32 → Break 32 → Build 16 → Drop 32 → Outro 16 |
| **Lo-fi** | 2–3 min | Intro 4 → Loop A ×4 → Variation ×2 → Loop A ×2 → Tail 4 |
| **Cinematic** | varies | Statement → Development → Climax → Resolution |
| **Hip-hop** | 2–3 min | Intro 4 → V1 16 → Hook 8 → V2 16 → Hook 8 → Bridge/V3 16 → Hook 8 → Outro 4 |

Bars → seconds: bars × beats_per_bar × 60 / BPM.

### 3. Mark the sections

`create_locator(name, time)` at each section start. **On Live 11 the name
can't be applied**: the locator keeps Live's number and the reply says so.
Keep a list for the user ("1 = Intro, 2 = Verse 1, …"). `cue_point` can
jump by those numbers. On Live 12 the names apply.

### 4. Place the clips

For each section and track that plays in it, call
`duplicate_to_arrangement` once per loop length. Typical densities:

- **Intro:** keys + pad (no drums, no bass)
- **Verse:** drums + bass + keys
- **Chorus / drop:** everything
- **Break / bridge:** strip back to pad + one element
- **Outro:** mirror the intro, then just the pad

Check progress with `get_arrangement_info`. It lists every clip with its
start/end bar.

### 5. Transitions

What 2.0 can do:

- **Drum fills** at section boundaries: `create_arrangement_midi_clip` on the
  drum track for the last bar (for example, a snare roll of 16ths rising in
  velocity), using the pad notes from `get_rack_info`.
- **Variations:** place a different Session clip, or write a new clip.
- **Mute a single placed clip** for a gap: `set_clip_properties(…,
  view="arrangement", properties={"muted": true})`.

What the user does by hand (tell them where): risers/sweeps from samples,
**filter and volume automation** (high-pass into a build, low-pass into a
break), and reverb/delay throws on the last hit.

### 6. Confirm before placing

> *"EDM structure, 2:48 at 128 BPM: intro 16, build 16, drop 32, break 32,
> build 16, drop 32, outro 16. Locators at each section (Live 11 will number
> them 1–7). Drum fills in the last bar of each build. Filter sweeps into the
> builds are yours to draw. Go ahead?"*

### 7. Review

`switch_to_arrangement_view`, `set_arrangement_loop` around a section the
user wants to audition, and `cue_point` to jump between sections. Remind the
user each placement is its own undo step (`undo` removes the last one).

## Don'ts

- Don't rewrite the user's musical content. Arrange existing clips; new
  material is only fills/variations they agreed to.
- Don't add sections they didn't ask for.
- Don't place over existing Arrangement clips without asking
  (`allow_overlap` stays false by default).
- Don't quantize or edit clip contents here. That's `midi-cleanup`.

## Example

> User: "I have a 4-bar lo-fi loop, give me a full 2-minute track"

1. Read: 4 tracks (drums, bass, keys, pad), 4-bar clips in slot 0, 90 BPM. The lo-fi template is 40 bars ≈ 1:47 (40 × 4 × 60 / 90 s); offer one more Loop A for a full two minutes.
2. Locators at bars 1, 5, 21, 29, 37 (beats 0, 16, 80, 112, 144).
3. Intro (bars 1–4): keys + pad at beat 0. Loop A (bars 5–20): all four tracks at beats 16, 32, 48, 64. Variation (bars 21–28): no drums; bass, keys, pad at beats 80 and 96. Loop A (bars 29–36): all four at 112 and 128. Tail (bars 37–40): pad at 144.
4. Fill into the return of Loop A: `create_arrangement_midi_clip` on drums at `start_bar=28`, `length_bars=1`, snare 16ths (bar 28 is free because the variation has no drums).
5. Report the section map and the locator numbers; suggest a low-pass sweep on the variation.
