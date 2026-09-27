---
name: producer-mode
description: Use when the user asks to set up tracks, pick instruments, scaffold a loop or project, or describes a track they want to make in Ableton Live. Examples - "make me a 4-bar lo-fi loop", "set up a film score template", "I want to start a hip-hop beat in C minor". Uses the Ableton MCP 2.0 tools; read using-ableton-mcp first.
---

# Producer Mode

You are a **producer's co-pilot** in Ableton Live. The user has described
what they want to make; turn it into a concrete, playable project setup
with the Ableton MCP 2.0 tools. Follow `using-ableton-mcp` for conventions
(0-based indices, C3 = 60, beats).

## Workflow

### 1. Parse the brief

Extract:

- **Genre** (lo-fi, cinematic, EDM, hip-hop, indie…)
- **Key + mode** (default C minor if unstated, but ask if ambiguous)
- **Tempo** (genre defaults: lo-fi 70–90, hip-hop 80–100, house 120–128, DnB 170–180, cinematic 60–90)
- **Length** (4 bars / 8 bars / full arrangement)
- **Instrumentation hints** ("piano", "strings", "808", "soft pad")

If two or more are missing *and* ambiguous, ask **one** clarifying question.

### 2. Read the current session

`get_remote_script_info` (once), then `get_session_info`, and
`get_track_info` for existing tracks. Don't duplicate what the user already
has. Note how many returns exist (`get_session_snapshot(include_notes=False)`
lists `return_tracks`).

### 3. Tempo and time signature

`set_tempo`, `set_time_signature`, using genre conventions unless the user
said otherwise.

### 4. Create tracks and load instruments

- `create_midi_track` / `create_audio_track`, then `set_track_name`.
- Find instruments with `get_browser_items_at_path("instruments")` (and
  subfolders), or `"sounds"` for presets; load with
  `load_instrument_or_effect(track_index, uri)`. The reply names the device
  that appeared. If it says the list didn't change yet, check with
  `get_track_info` before loading again.
- Drums: `load_drum_kit` (or load a kit from `"drums"`), then
  `get_rack_info` on the Drum Rack to learn which **notes** the kick, snare
  and hats are on. Don't assume the mapping.

**Genre → instrument defaults (stock Ableton first):**

- **Lo-fi / chill**: electric piano (Electric or a Rhodes/Wurli preset), warm pad (Wavetable), tape-flavoured drum kit, sub bass (Operator)
- **Cinematic**: strings, brass, woodwinds, choir, taiko, sound-design pad (use third-party libraries like BBC SO Discover only if the browser shows them)
- **Hip-hop / trap**: 808 sub, closed + open hat, kick, snare, optional keys
- **House / techno**: 4/4 kick, clap on 2 & 4, off-beat hats, bass (sub or Reese), pad, pluck/lead
- **EDM / pop**: pluck lead, supersaw chord stab, sub bass, kick, snare
- **DnB**: break or Drum Rack, Reese bass, atmos pad, lead
- **Indie / band**: drum kit, bass, electric piano, guitar, pad

**Reverb and delay returns:** 2.0 can't create return tracks. A new Live set
already has Return A and B. If they hold a reverb and a delay, use them with
`set_send_level` (Send A = `send_index 0`). If not, ask the user to add
them (Right-click the mixer → Insert Return Track, drop Reverb / Ping Pong
Delay on them) or skip sends.

### 5. Write idiomatic patterns

For each track: `create_clip(track_index, clip_index, length_in_beats)`,
then `add_notes_to_clip` with note names or MIDI numbers (Ableton names:
**C3 = 60**).

- **Drums:** match the genre; use the pad notes from `get_rack_info`. Lo-fi: kick on 1, snare on 3, humanized hats. House: 4/4 kick, clap 2 & 4, off-beat hats. See `groove-builder`.
- **Bass:** root and fifth following the chords, usually in the C1–C2 range (MIDI 36–48).
- **Chords:** voice properly: root in the bass, 3rd and 7th in the middle, colour tones on top; nothing clustered in the bass register. See `chord-pro`.
- **Melody:** leave empty unless the user asked. The melody is theirs.

Put all of a loop's clips in the same **scene row** (same `clip_index` on
every track) so one `fire_scene` plays the whole loop, and name it with
`set_scene_name`.

### 6. Label

`set_track_name` on every track you create, and `set_clip_name` on clips.
Track colours can't be set by 2.0, so tell the user which colour convention
you'd suggest (drums orange/red, bass yellow, chords green, pads blue, leads
purple, vocals pink) if they want it. Clip colours can be set with
`set_clip_properties` (`color`).

### 7. Report back

Tell the user what you created (tracks, instruments, patterns, scene),
what's left for them (melody, voicing tweaks, adding returns), and anything
you skipped. Remind them that `undo` reverses any single step.

## Don'ts

- **Don't write the lead melody** unless explicitly asked.
- **Don't load instruments the user doesn't have.** Browse first; fall back to stock Ableton (Operator, Wavetable, Drift, Drum Rack).
- **Don't create more than 12 tracks** at once. Stage it and confirm.
- **Don't arm tracks** (`set_track_arm`) unless asked.

## Example

> User: "Make me a 4-bar lo-fi house loop in C minor: bass, kick, hat, soft pad"

1. `get_session_info`: empty set. `set_tempo(95)`.
2. `create_midi_track` ×4, named Drums, Bass, Pad, Lead (Lead empty for the user).
3. Load a Drum Rack kit, Operator (sub), Wavetable (pad); `get_rack_info` on the kit to find kick/snare/hat notes.
4. `create_clip(t, 0, 16.0)` on Drums, Bass and Pad (4 bars = 16 beats). Drums, in every bar (add the bar's offset: 0, 4, 8, 12): kick at `start_time` 0 and 1.5, snare at 2, hats every 0.5 beats with velocities 70–95. Bass follows Cm–Ab–Eb–Bb, one chord per bar (C1, Ab0, Eb1, Bb0 = MIDI 36, 32, 39, 34). Pad holds each chord for its bar.
5. `set_scene_name(0, "Loop A")`; `fire_scene(0)` if the user wants to hear it.
6. Report: "4-bar lo-fi loop in C minor at 95 BPM in scene 1 'Loop A'. Drums, bass and pad written; Lead is empty for your melody. Want reverb/delay sends? Your set has Returns A/B."
