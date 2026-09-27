---
name: ableton-export
description: Pre-export checklist before rendering audio from Ableton Live with Ableton MCP 2.0. Validates headroom, master processing, mono compatibility and export settings. Use right before bouncing to a file.
---

# /ableton-export

Run a pre-export audit and surface anything that would compromise the
bounced file. For a full pre-master audit use the `mastering-prep` skill;
this is the quick version.

## What it checks

| Check | Pass | Source |
| --- | --- | --- |
| Master peak | Below −1 dB | Ask the user (2.0 can't read meters) |
| Headroom before any limiter | At least 3 dB | Ask the user |
| Track clipping | No red track meters | Ask the user |
| Master chain | Limiter on only if this is a final master | `get_session_snapshot(include_notes=False)` → `master_track.devices` |
| Inactive devices | Removed or deliberately off | Snapshot: devices switched off |
| Muted / soloed tracks | Intended | Snapshot: `mute` / `solo` per track |
| Loop brace | Matches what should be exported | `get_arrangement_info` → `loop` |
| Mono compatibility | Nothing disappears in mono | Ask the user to flip Utility to mono on the master |
| Sub below ~30 Hz | Filtered or controlled | Snapshot (high-passes) + ask |
| Export settings | See below | The user's Export dialog |

**Export dialog** (File → Export Audio/Video):
24-bit at the project's sample rate (44.1 or 48 kHz) for archival or
mastering; 16-bit with dither only for final distribution; Normalize off;
Convert to Mono off unless requested; render the loop/selection you
checked above.

## Workflow

1. Read the set: `get_session_snapshot(include_notes=False)` and `get_arrangement_info`.
2. Ask the user, in one message, for the readings 2.0 can't take (master peak, headroom, red meters, mono check).
3. Mark each check ✅ or ❌ and print a summary table.
4. For ❌, propose specific fixes (for example `set_master_volume` down a step, or un-soloing a forgotten solo with `set_track_solo`). Apply one at a time on approval.
5. All ✅: *"Ready to export. Recommended: 24-bit, 48 kHz, normalize off."*

## Don'ts

- Don't export for the user. 2.0 can't render, and the user picks the file name and location.
- Don't apply a mastering chain; this is a check.
- Don't report levels the user didn't give you.
