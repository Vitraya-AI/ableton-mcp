---
name: mastering-prep
description: Use when the user is finishing a track in Ableton Live and wants to check it's ready for mastering or self-mastering. Audits headroom, peaks, master processing, mono compatibility, frequency balance and loudness. Examples - "is this ready to master?", "audit my mix before export", "check my levels". Reads the whole set with the Ableton MCP 2.0 tools and asks the user for meter readings; read using-ableton-mcp first.
---

# Mastering Prep

A pre-master audit: confirm the mix is clean for an external mastering
engineer or for self-mastering. This skill **audits**. It doesn't apply a
mastering chain.

## What 2.0 can and can't see

- **Can read:** every track, return and the master chain with device
  parameters (`get_session_snapshot(include_notes=False)`), faders, pans,
  mute/solo, sends, which devices are on or off.
- **Can't read:** level meters, peaks, LUFS, phase correlation or a
  spectrum. For those, ask the user to read Live's meters or a metering
  device (Spectrum, Utility, a loudness meter) and tell you the numbers.
  Never invent readings.
- **Can change:** track faders/pans/sends, master volume and pan, and
  devices on regular tracks. **Can't change** devices on the master or
  returns; the user does that by hand.

## Workflow

### 1. Read the session

`get_session_snapshot(include_notes=False)`. From it, note:

- The master chain (`master_track.devices`): limiter? compressor? their settings
- Devices that are switched off (candidates for removal)
- Tracks with extreme fader positions (near 1.0 = +6 dB)
- Returns and what's on them

### 2. Ask for the readings you can't take

In one message: master peak, integrated LUFS (if they have a meter), whether
any track meter hits red, and whether they've checked mono.

### 3. Audit

Mark each item ✅ pass, ❌ fail or ⚠️ warning, with the reading:

| Check | Target | How |
| --- | --- | --- |
| **Master peak** | −3 to −6 dB; never above −1 dB | User's meter reading |
| **No master limiter for external mastering** | Off | Snapshot: limiter on the master and switched on? |
| **Master compressor** | Under 2 dB gain reduction | Snapshot settings + user's GR reading |
| **Integrated loudness** | −16 to −20 LUFS for a pre-master | User's meter |
| **Mono compatibility** | Nothing disappears in mono | User flips Utility to mono on the master |
| **Phase** | Correlation above 0 | User's correlation meter |
| **Frequency balance** | No region >6 dB above its neighbours | User's Spectrum reading |
| **Sub below ~30 Hz** | Filtered or controlled | Look for a high-pass on bass/master in the snapshot; ask |
| **Above ~18 kHz** | Controlled if there's no musical content | Same |
| **DC offset** | None | Utility's DC filter on the master |
| **Track clipping** | No red meters | User's reading |
| **Inactive devices** | Removed or intentionally off | Snapshot: devices switched off |

### 4. Report

Failures first, then warnings, then passes:

> *❌ Master peaks at −0.8 dB: needs at least 3 dB more headroom*
> *❌ Limiter active on the master: bypass it for the mastering engineer*
> *⚠️ −10.2 LUFS: too loud for a pre-master*
> *✅ No inactive devices*

### 5. Propose fixes (apply one at a time, on approval)

- **Master too hot** → `set_master_volume` down a step (0.85 = 0 dB; read the
  new value back), or better, trim the loudest tracks with `set_track_volume`.
- **Master limiter/compressor for export** → the user bypasses it (2.0 can't
  change master devices).
- **Mono problem** → find the widened track (snapshot shows wideners,
  Utility width, chorus) and propose reducing it; for a device on a regular
  track, `set_device_parameter` or `set_device_enabled` to A/B.
- **DC offset** → the user adds Utility with DC on the master.
- **Unused devices** → propose `delete_device` on regular tracks, with
  confirmation (`undo` restores).

Let the user listen between fixes.

### 6. Export checklist (if they're exporting now)

Rendering is in Live's Export dialog (2.0 can't render):

- ✅ 24-bit, at the project's sample rate (44.1 or 48 kHz)
- ✅ Dither on for 16-bit, off for 24-bit
- ✅ Normalize off
- ✅ Convert to mono off (unless a mono deliverable is requested)
- ✅ File name with track name, BPM, key and version, e.g. `track-95bpm-Cm-v3.wav`

## Don'ts

- **Don't apply a mastering chain.** This skill audits.
- **Don't recommend paid mastering tools** without asking budget and intent.
- **Don't suggest normalizing.** It's peak-based and breaks headroom.
- **Don't fix more than one issue before the user listens.**
- **Don't state levels you didn't get from the user.**
