---
name: sidechain-setup
description: Use when the user wants sidechain compression or ducking in Ableton Live - typically kick → bass, kick → pads, vocal → music bed. Examples - "sidechain my bass to the kick", "make the synths duck under the vocal", "add pumping to the chords". Loads and sets the compressor with the Ableton MCP 2.0 tools; the sidechain source is picked by the user. Read using-ableton-mcp first.
---

# Sidechain Setup

Set up sidechain compression. 2.0 can load and dial in the compressor, but
**can't choose the sidechain source**; that's one click for the user,
which you walk them through.

## Workflow

### 1. Source and target

- **Source** = the track that causes the duck (usually kick or vocal)
- **Target** = the track that gets ducked (bass, pads, music bed)

Confirm with names and indices from `get_session_info` / `get_track_info`:
*"Duck the Bass (track 2) under the Kick (track 1)?"*

### 2. Choose the technique

#### A. Compressor sidechain (standard for kick → bass)
Settings:
- Ratio 4:1 · Attack 5 ms · Release 80–120 ms (at 120 BPM a beat is 500 ms
  and a 16th is 125 ms; the release should finish well before the next kick)
- Threshold: until the user sees 4–6 dB gain reduction on each kick
- Makeup/output +1 to +2 dB

#### B. Glue Compressor sidechain
Same routing, more musical "analog" pump: house/EDM buses.

#### C. Volume pump without a trigger (creative)
For a 4/4 pump with no kick (breakdowns): Auto Filter or Auto Pan used as a
volume LFO, synced to 1/4, depth 6–12 dB. 2.0 can load and set it
(`load_instrument_or_effect`, then `set_device_parameter` by name).

#### D. Hand-drawn ducking
A volume automation envelope drawn against the source's hits. 2.0 can't
write automation, so describe the shape and let the user draw it.

### 3. Apply

1. **Load the compressor on the target:**
   `get_browser_items_at_path("audio_effects")` → Compressor (or Glue
   Compressor) → `load_instrument_or_effect(target_track, uri)`. The reply
   names the new device; find its `device_index` with `get_track_info`.
2. **Read its parameters:** `get_device_parameters`. Use the names it
   reports and set each value within its `min`/`max` with
   `set_device_parameter(..., parameter_name=…)`. Parameters are Live's
   internal values, not ms/dB labels. After setting, ask the user what the
   device shows and adjust.
3. **Hand over the routing step:**

> *"Compressor is on the Bass with 4:1, fast attack and ~100 ms release.
> One step for you: on the Compressor, open the sidechain section (the
> triangle at the top left), switch Sidechain on, and set Audio From to
> 'Kick'. Then play the kick and bass and tell me how much gain reduction
> you see. I'll set the threshold."*

### 4. Tune by ear

Ask the user to play kick + bass together, then adjust one parameter at a
time:

- Pumping too obvious → ratio 3:1 or release ~60 ms
- Not enough → ratio 6:1 or lower threshold
- Bass dips too long → shorter release
- Bass misses the next beat → release too long; shorten it

`set_device_enabled` off/on gives a quick A/B; `undo` reverts a change.

## Quick reference

| Use case | Ratio | Attack | Release | Gain reduction |
| --- | --- | --- | --- | --- |
| Kick → bass (rock/pop) | 4:1 | 5 ms | 100 ms | −4 dB |
| Kick → bass (EDM pump) | 8:1 | 1 ms | 200 ms | −10 dB |
| Kick → pad/chords | 3:1 | 10 ms | 150 ms | −3 dB |
| Vocal → music bed | 2:1 | 15 ms | 300 ms | −2 dB |
| Snare → reverb tail | 3:1 | 5 ms | 80 ms | −4 dB |

## Don'ts

- Don't sidechain everything. Kick → bass is universal; pad ducking is genre-specific.
- Don't go above 8:1 unless the user wants an obvious pump.
- Don't sidechain the master bus. (2.0 can't load devices on the master anyway.)
- Don't set the threshold blind. It depends on levels only the user can see.
