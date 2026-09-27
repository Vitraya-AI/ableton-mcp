---
name: reference-match
description: Use when the user references an artist or track whose vibe or sound they want in Ableton Live. Examples - "make this sound like Ólafur Arnalds", "I want a Tame Impala vibe", "match the mix of Kendrick's Money Trees". Translates the reference into concrete production moves and applies the top three with the Ableton MCP 2.0 tools; read using-ableton-mcp first.
---

# Reference Match

Turn a reference artist or track into concrete production choices. We do
**not** download or analyse copyrighted audio; we use known sonic
signatures and the user's ears.

## Workflow

### 1. Pin down the reference

If not given: *"Which track or artist, and which part: arrangement, mix,
sound design or overall vibe?"*

### 2. Recall the signature

| Reference | Signature |
| --- | --- |
| **Ólafur Arnalds** | Felt piano, strings, tape saturation, 60–80 BPM, minor keys, sparse, long reverb tails, close-mic intimacy |
| **Tame Impala (Currents era)** | LinnDrum-style drums, chorused guitars/synths, filtered vocals, sidechained bass, 60–90 BPM, saturated drums |
| **Bonobo** | Live + electronic percussion, jazz harmony, vinyl texture, 90–110 BPM, wide stereo, sample chops |
| **Burial** | Vinyl/cassette texture, rain and atmosphere, pitched vocal fragments, sub bass, 2-step garage rhythm, minor 7 chords |
| **Kendrick (DAMN era)** | 808 sub, trap hats, jazz samples, layered vocals, heavy compression |
| **Billie Eilish (early)** | Close whispered vocal, sparse 808, snaps, sub-heavy, breaths left in, heavy automation |
| **Skrillex** | Formant-modulated bass, stutter edits, bright leads, very wide, pumping sidechain |
| **Hans Zimmer** | Layered low brass + synth, choir, pulsing ostinatos, slow swells, very long reverb |
| **Lo-fi hip-hop** | Rhodes/Wurli, jazz chords, vinyl crackle, tape saturation, 70–90 BPM, swung 16ths |

### 3. Translate into moves, and map each to 2.0

| Aspect | Moves | How |
| --- | --- | --- |
| **Tempo / feel** | Genre tempo, swing, half-time | `set_tempo` (with approval); swing/humanize via `midi-cleanup` |
| **Harmony** | Characteristic chords | `chord-pro` → `add_notes_to_clip` / `modify_clip_notes` |
| **Drums** | Kit character, pattern | `groove-builder`; kits from `get_browser_items_at_path("drums")` |
| **Sound design** | Era-appropriate synths | `sound-designer` (Operator/Wavetable/Analog/Drift, set by name) |
| **Effects** | Tape/vinyl saturation, chorus, reverb type | `load_instrument_or_effect` (Saturator, Vinyl Distortion, Chorus-Ensemble, Reverb) then `set_device_parameter` |
| **Space** | Reverb/delay amounts | `set_send_level` to the user's returns |
| **Arrangement** | Density, section lengths | `arrangement-coach` |
| **Mix / loudness** | Width, low end, LUFS target | `mixer-doctor`; readings come from the user |

Loudness targets: lo-fi/Bonobo −10 to −8 LUFS, modern pop −8 to −6,
cinematic −16 to −14. Reverb types: hall (cinematic), plate (vocals),
spring (surf/lo-fi), room (tight modern pop).

What 2.0 can't do here: automation (swells, filter rides), which the user
draws, and reading loudness.

### 4. Propose the top 3, then listen

Pick the **three most distinctive** elements and propose only those:

> *"Top three Ólafur moves: (1) felt piano, a Grand Piano preset with
> Saturator in tape mode; (2) a slow-swelling string pad, long attack, 40%
> to your reverb return; (3) 70 BPM, minor key, gentle velocity-driven
> timing. Apply these, then listen?"*

Apply one at a time on approval.

### 5. Iterate

After listening, refine what's still off. References are approximate;
iterate with the user.

## Don'ts

- Don't claim an exact clone. We approximate the recipe.
- Don't download or process copyrighted audio.
- Don't recommend sample packs unless the user has them.
- Don't apply more than 3 reference moves before the user listens.

## Unfamiliar reference

Ask what they like about it ("the drums? the vocal effect? the
arrangement?") and translate that description into moves. You don't need to
know the artist.
