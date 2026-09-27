---
name: sound-designer
description: Use when the user wants to design or modify a synth patch in Ableton Live - lead, bass, pad, pluck, keys, FX - on stock synths (Operator, Wavetable, Analog, Drift). Examples - "make me a wide supersaw lead", "design a sub bass", "give me a lush pad like Olafur Arnalds". Sets parameters by name with the Ableton MCP 2.0 tools; read using-ableton-mcp first.
---

# Sound Designer

Build synth patches from a description on stock Ableton synths: Operator
(FM), Wavetable (wavetable + FM), Analog (subtractive), Drift (modern
subtractive). The user can swap in a third-party synth later.

## How to set a patch with 2.0

1. Load the synth: `get_browser_items_at_path("instruments")` →
   `load_instrument_or_effect(track_index, uri)`. If the track already has an
   instrument, ask before adding another. Don't overwrite their favourites.
2. **Read before you set:** `get_device_parameters` lists every parameter's
   name, value, `min`/`max`, and for switches (waveform, filter type, voice
   mode) the `value_items` positions.
3. Set by name: `set_device_parameter(track_index, device_index, value=…,
   parameter_name="Filter Freq")`. Use the names the device reports; they
   differ between synths and Live versions. For a switch, the value is the
   **index** of the position in `value_items`.
4. Values are Live's internal units within `min`/`max`, not the ms/Hz/%
   labels in the UI. For time and frequency controls, pick a starting value,
   then ask the user what the device displays and nudge it.
5. Inside an Instrument Rack, address the synth with `chain_index` and
   `chain_device_index` (find them with `get_rack_info`).

## Workflow

### 1. Pick the synth

| Sound | Synth | Why |
| --- | --- | --- |
| Sub bass, 808 | **Operator** (sine) or Drift | Pure, controllable low end |
| Reese / wide bass | **Wavetable** | Detuned saws + filter movement |
| Pluck / staccato | **Operator** | Fast envelopes, FM bite |
| Supersaw | **Wavetable** (saw, unison 7+) | Native unison + detune |
| Lush pad | **Wavetable** (LP filter, slow envelopes) | Movement + filter LFO |
| Warm / felt | **Drift** + saturation | Soft character |
| Vintage analog lead | **Analog** | Classic subtractive voice |
| Bell / mallet | **Operator** (FM ratios) | Inharmonic partials |

### 2. Starting points

#### Sub bass (Operator)
Single sine carrier (algorithm with only A audible) · amp env: attack 0,
decay 0, sustain full, release short · mono with ~50 ms glide.

#### Supersaw (Wavetable)
Osc 1 saw table · unison 7 voices, detune ~25–35% · filter 1 LP24, cutoff
high (~80%), resonance ~15%, envelope amount ~30% · filter env A 0 / D
400 ms / S 50% / R 200 ms · amp env A 5 ms / D 200 ms / S 80% / R 300 ms.

#### Lush pad (Wavetable)
Osc 1 choir/vocal table · osc 2 saw, detuned −7 cents · LP24, cutoff ~60%,
resonance ~10% · filter LFO triangle ~0.1 Hz, amount ~25% · amp env A
800 ms / D 1.5 s / S 70% / R 2 s.

#### Pluck (Operator)
Modulator B → carrier A, B ratio 2 · filter LP ~70%, env amount ~40% ·
filter env A 0 / D 80 ms / S 0 / R 100 ms · amp env A 0 / D 200 ms / S 0 /
R 100 ms.

### 3. Character with effects

Add in this order (each via `load_instrument_or_effect`, then set by name;
check the chain order with `get_track_info` after each load, since Live
inserts after the track's selected device):

- **Saturator** (drive 3–6 dB) for warmth
- **Chorus-Ensemble** for width on pads/leads
- **Auto Filter** with LFO for movement
- **EQ Eight** last: cut harsh resonances
- **Reverb/delay on sends**, not in-line: `set_send_level` to the user's
  reverb/delay returns (pads 20–30%, leads 10–15%, plucks 15–20% delay). 2.0
  can't create returns; if there are none, ask the user to add them.

### 4. Verify

Read back with `get_device_parameters` and summarize:
> *"Wavetable supersaw: 7-voice unison at ~30% detune, LP24 with light
> envelope movement, Chorus-Ensemble after it, 25% to your reverb return.
> Play a chord and tell me what to change."*

Offer an A/B with `set_device_enabled` on the effects, and `undo` for any
single change.

### 5. Save

2.0 can't save presets. Tell the user: *"If you like it, save it from the
device title bar (Cmd/Ctrl+S) so it lands in your User Library."*

## Don'ts

- Don't default to third-party synths (Serum, Massive, Diva).
- Don't max resonance; above ~70% on Wavetable's filter risks self-oscillation.
- Don't replace the user's instrument or preset without asking; inspect first.
- Don't stack more than ~6 effects; clarity over saturation.
- Don't guess parameter names; read them first.
