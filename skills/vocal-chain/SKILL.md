---
name: vocal-chain
description: Use when the user has recorded vocals and wants a processing chain in Ableton Live. Examples - "set up my vocal chain", "process this vocal", "make the vocal sit in the mix", "give me a pop vocal chain", "make this rap vocal aggressive". Loads and sets stock devices in order with the Ableton MCP 2.0 tools; read using-ableton-mcp first.
---

# Vocal Chain

Build a vocal processing chain on the vocal track with stock Ableton
devices. The user can swap in third-party plugins later.

## Workflow

### 1. Identify the style

| Style | Goal |
| --- | --- |
| Pop lead | Bright, present, controlled |
| Rap (modern) | Aggressive, up front, heavily compressed |
| Indie / lo-fi | Warm, a little distant, character kept |
| R&B | Smooth, lush |
| Cinematic / spoken word | Intimate, breathy, minimal |
| Backing vocals | Behind the lead: duller, narrower |

### 2. Inspect the track

`get_track_info` on the vocal track: existing devices (don't remove the
user's), audio vs MIDI. 2.0 can't read levels, so ask: *"Roughly where do
the vocal's peaks sit? Around −6 to −3 dB is ideal."* If they're clipping or
very quiet (below −20 dB), say so: processing won't fix a bad recording.

### 3. The chain

Standard order:
1. Gate / noise reduction (only if needed)
2. Subtractive EQ
3. De-esser
4. Compressor 1 (fast, peaks)
5. Compressor 2 (slow, levelling)
6. Additive EQ
7. Saturation (optional)
8. Pitch correction (only if asked)
9. Reverb on a **send**
10. Delay on a **send**

#### Pop lead (stock)

| Slot | Device | Settings |
| --- | --- | --- |
| 1 | EQ Eight | HPF 80 Hz; −3 dB at 250 Hz; −2 dB around 4 kHz if harsh |
| 2 | Multiband Dynamics | De-ess the top band (5–9 kHz), ~4:1 |
| 3 | Compressor | 4:1, attack 5 ms, release 60 ms, 4–6 dB GR on peaks |
| 4 | Glue Compressor | 2:1, slow attack, auto release, 1–2 dB GR |
| 5 | EQ Eight | +2 dB 100 Hz (warmth), +2 dB 5 kHz (presence), +2 dB 12 kHz (air) |
| 6 | Saturator (optional) | Drive 2–3 dB, Soft Clip |
| Send | Reverb return | 15–20%, pre-delay 30–50 ms |
| Send | Delay return | Dotted 1/8, 15–20%, feedback ~25% |

#### Rap (modern, aggressive)

| Slot | Device | Settings |
| --- | --- | --- |
| 1 | EQ Eight | HPF 100 Hz, narrow cuts on resonances |
| 2 | Multiband Dynamics | De-ess 5–9 kHz, ~6:1 |
| 3 | Compressor | 6:1, attack 3 ms, release 40 ms, 6–8 dB GR |
| 4 | Compressor | 3:1, attack 30 ms, auto release, 2–3 dB GR |
| 5 | EQ Eight | +3 dB 5 kHz, +2 dB 200 Hz |
| 6 | Saturator | Drive 4–6 dB |
| Send | Short plate reverb | 8–12% |
| Send | Slap delay | Single 1/16 repeat, ~10% |

#### Indie / lo-fi

| Slot | Device | Settings |
| --- | --- | --- |
| 1 | EQ Eight | HPF 70 Hz, gentle |
| 2 | Compressor | 3:1, attack 30 ms, release 80 ms, 3–4 dB GR |
| 3 | Saturator | Drive 3–5 dB, warm curve |
| 4 | EQ Eight | −1 dB at 8 kHz |
| 5 | Vinyl Distortion or Cabinet | Subtle |
| Send | Spring-style reverb | 25–30% |

### 4. Apply, in order, with confirmation

Show the chain first. On approval:

1. For each slot, top to bottom: find the device under
   `get_browser_items_at_path("audio_effects")` and
   `load_instrument_or_effect(vocal_track, uri)`. Live inserts a loaded
   device after the track's selected device (normally the end of the chain),
   so load in slot order and check the order with `get_track_info` after
   each one. If one lands in the wrong place, `undo` and ask the user to
   click the last device in the chain before retrying.
2. Set each with `get_device_parameters` → `set_device_parameter` **by
   name**, within `min`/`max`; filter types via `value_items`. Values are
   Live's internal units: after frequency/threshold moves, ask the user what
   the device shows.
3. Sends: `set_send_level(vocal_track, send_index, value)`. Send A = 0.
   2.0 can't create return tracks; if the set lacks a reverb/delay return,
   ask the user to add one.
4. Thresholds and gain reduction depend on levels only the user can see:
   ask for the GR reading and adjust.

### 5. Listen and tune

- Too dark → +1–2 dB at 10–12 kHz
- Too bright/harsh → more de-essing or a cut at 4–5 kHz
- Pumping → lower ratio or raise threshold on compressor 1
- Still sibilant → de-ess threshold lower or band tighter

A/B any stage with `set_device_enabled`; `undo` reverts the last change.

## Don'ts

- Don't add pitch correction without asking; many vocals are meant to be raw.
- Don't take 8+ dB of compression in one stage; split it across two.
- Don't put reverb in-line; always on a send.
- Don't load third-party plugins by default.
- Don't remove devices the user already has; add after them.
