<div align="center">

# 🎛️ Ableton MCP 2.0
## with Skills!

**Connect Your Agent to Ableton Live**

Prompt-assisted music production across Session and Arrangement view: write and edit notes, mix, build arrangements, and work inside racks, driven by AI.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Ableton Live 11+](https://img.shields.io/badge/Ableton%20Live-11%2B-orange)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Remote Script 1.11.1](https://img.shields.io/badge/Remote%20Script-1.11.1-555)

[**What's new**](#-whats-new-in-20) · [**Tool reference**](#-tool-reference) · [**Agent skills**](#-agent-skills) · [**Roadmap**](#-roadmap) · [**Issues**](https://github.com/Vitraya-AI/ableton-mcp/issues)

</div>

---

Ableton MCP 2.0 builds on [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) (the original Ableton MCP) and brings in the most useful ideas from [uisato/ableton-mcp-extended](https://github.com/uisato/ableton-mcp-extended), rebuilt for Live 11 and tested against a real Live 11.3.43 set. It grows the original's 31 music tools to 60: note editing by note ID, mixing, scenes, undo, arrangement building, and device and rack control. Every error comes back with a machine-readable code, and every edit is one undo step in Live.

## ⚡ Quickstart

Four steps: install `uv`, point your MCP client at the server, install the Ableton Remote Script, then select it in Live.

**1. Install uv**

```bash
# macOS
brew install uv
```

Otherwise, install from [uv's official website](https://docs.astral.sh/uv/getting-started/installation/).

> **Warning:** Do not proceed before installing uv.

**2. Add the MCP server to your client**

<details open>
<summary><b>Claude Desktop</b> (Settings → Developer → Edit Config)</summary>

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/Vitraya-AI/ableton-mcp",
                "ableton-mcp"
            ]
        }
    }
}
```
</details>

<details>
<summary><b>Cursor</b> (Settings → MCP)</summary>

Paste this as a command:

```
uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp
```
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add AbletonMCP -- uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp
```
</details>

> **Note:** `uvx ableton-mcp` on its own installs the **original** package from PyPI, not 2.0. Keep the `--from git+…` part.

> **Warning:** Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both.

**3. Install the Ableton Remote Script**

```bash
uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp-install-script
uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp-install-script --list-targets   # preview target folders first
```

**4. Connect**

1. Launch Ableton Live (or restart it if it was open)
2. Go to **Settings/Preferences → Link, Tempo & MIDI**
3. In the **Control Surface** dropdown, select **AbletonMCP**
4. Set **Input** and **Output** to **None**

That's it. Ask Claude to build something. 🎶

---

## 📑 Table of Contents

- [Quickstart](#-quickstart)
- [What's new in 2.0](#-whats-new-in-20)
- [Tool reference](#-tool-reference)
- [Agent skills](#-agent-skills)
- [Components](#-components)
- [Installation](#-installation)
- [Usage](#-usage)
- [Troubleshooting](#-troubleshooting)
- [Technical details](#-technical-details)
- [Limitations](#-limitations)
- [Telemetry and data](#-telemetry-and-data)
- [Development](#-development)
- [Roadmap](#-roadmap)
- [Credits](#-credits)

---

## ✨ What's new in 2.0

### 🎹 Notes, edited in place
- Read every note in a clip with its Live 11 **note ID**, then change pitch, timing, velocity, probability or mute on just those notes (`modify_clip_notes`). No more clearing and rewriting a whole clip to change one note.
- Remove notes in a time and pitch window (`remove_notes_from_clip`), for example only the kick in bar 2.
- **Note names** anywhere a pitch is accepted: `"C3"`, `"Eb2"`, `"F#4"`, using Ableton's convention (C3 = MIDI 60).
- `add_notes_to_clip` supports **probability**, velocity deviation and release velocity, and returns the new notes' IDs.

### 🎚️ Mixing
Track volume, pan, mute, solo, arm and send levels, plus master volume and pan. Values are checked against Live's own ranges, and group tracks, which can't be armed, give a clear `track_not_armable` error.

### 🎬 Scenes, clips and undo
Create, fire, rename and delete scenes; duplicate clips; delete tracks; set the time signature. **Undo and redo** are tools, and every editing command is exactly one undo step in Live, even ones that take several steps internally. Jumps and transport commands add none.

### 🗺️ Arrangement view
- `get_arrangement_info`: the whole timeline in one call, with song length, loop, time signature, locators, and every track's clips with **bar numbers that match Live's ruler**.
- `create_arrangement_midi_clip` places a MIDI clip with notes at any bar. On Live 12 it uses Live's native call; on Live 11 it builds the clip in a spare Session slot, copies it to the Arrangement and removes the temporary clip, all in one undo step.
- `create_arrangement_audio_clip` places an audio file on the timeline.
- `cue_point` jumps to a locator (by name or time), steps to the next or previous one, or deletes one. `set_arrangement_loop` sets the loop brace.
- The note tools and `delete_clip` take `view="arrangement"`, so they work on Arrangement clips as well as Session clips.
- `set_clip_properties` sets several properties in one call: name, mute, color, loop and markers, and for audio clips gain, pitch and warp.
- Positions can be given in beats **or bars**.

### 🎛️ Devices and racks
- `get_rack_info` shows a rack's chains, the devices in each chain, its macros, and a Drum Rack's filled pads mapped to their chains.
- Reach **any device inside a rack chain**, not just the first, with `chain_index` and `chain_device_index` on the device tools.
- Set parameters **by name** (`parameter_name="Filter Freq"`) as well as by index. Switch-type parameters list their named positions.
- Turn devices on and off (`set_device_enabled`), delete them (`delete_device`), and step through plugin presets (`navigate_device_preset`).
- Loading an instrument waits for Live and reports what actually appeared ("New devices: Drift").

### 🛡️ Reliability
- **Structured errors.** Every failure ends with a code such as `(code: clip_overlap)` or `(code: parameter_value_out_of_range)`, so the AI can react to it instead of guessing.
- **Waits for Live.** Live applies playhead and loop changes on its next update, so commands that move the playhead and then act (placing locators, for example) wait for Live before continuing. The results report what Live actually did.
- **Honest results.** If Live 11 can't do something, such as rename a locator from a script, the reply says so instead of pretending it worked.
- **Version and capability handshake.** The server knows which Remote Script version and Live build it's talking to (`get_remote_script_info`) and refuses commands an older script would misinterpret.
- **Fixed from upstream:** a rejected command no longer drops the connection; each command keeps its own timeout (a bug had forced them all to 15 s); `max_depth` on the browser tree is capped where it would exceed the timeout; values out of range are rejected instead of silently clamped.
- **Smaller tool list.** Dataset-only tools and the telemetry `user_prompt` parameter are hidden from the model, which saves about 3.5k tokens of context per session (see [Telemetry and data](#-telemetry-and-data)).

---

## 🧰 Tool reference

60 tools. Indices are 0-based (the first track is track 0).

| Area | Tools |
|---|---|
| **Session info** | `get_session_info`, `get_track_info`, `get_session_snapshot`, `get_remote_script_info` |
| **Tracks** | `create_midi_track`, `create_audio_track`, `set_track_name`, `delete_track` |
| **Mixer** | `set_track_volume`, `set_track_panning`, `set_track_mute`, `set_track_solo`, `set_track_arm`, `set_send_level`, `set_master_volume`, `set_master_panning` |
| **Session clips** | `create_clip`, `create_audio_clip`, `set_clip_name`, `duplicate_clip`, `delete_clip`, `fire_clip`, `stop_clip`, `set_clip_properties` |
| **Notes** | `get_clip_notes`, `add_notes_to_clip`, `modify_clip_notes`, `remove_notes_from_clip`, `clear_notes_from_clip` |
| **Arrangement** | `get_arrangement_info`, `get_arrangement_clips`, `create_arrangement_midi_clip`, `create_arrangement_audio_clip`, `duplicate_to_arrangement`, `set_arrangement_clip_name`, `set_arrangement_loop`, `set_arrangement_time`, `create_locator`, `cue_point`, `switch_to_arrangement_view` |
| **Scenes** | `create_scene`, `fire_scene`, `set_scene_name`, `delete_scene` |
| **Transport and song** | `start_playback`, `stop_playback`, `set_tempo`, `set_time_signature`, `undo`, `redo` |
| **Devices and racks** | `get_device_parameters`, `set_device_parameter`, `set_device_enabled`, `delete_device`, `get_rack_info`, `navigate_device_preset` |
| **Browser** | `get_browser_tree`, `get_browser_items_at_path`, `load_instrument_or_effect`, `load_drum_kit` |

---

## 🎓 Agent skills

The tools give an AI access to Live; the [skills](skills/README.md) teach it
to use them like a co-producer. There are 13 skills and 4 slash commands,
adapted from [glincker/ableton-skills](https://github.com/glincker/ableton-skills)
and rewritten against 2.0's real tools:

- **`using-ableton-mcp`**, the foundation: indices, Ableton note names (C3 = 60), beats vs bars, Session vs Arrangement, error codes, undo, and what Live 11 can't do
- **Making music:** `producer-mode`, `groove-builder`, `chord-pro`, `midi-cleanup`, `arrangement-coach`, `sound-designer`, `tempo-coach`, `reference-match`
- **Mixing:** `mixer-doctor`, `sidechain-setup`, `vocal-chain`, `mastering-prep`
- **Commands:** `/ableton-init`, `/ableton-snapshot`, `/ableton-export`, `/ableton-debug`

Install them into Claude Code (from a clone):

```bash
mkdir -p ~/.claude/skills ~/.claude/commands
for d in skills/*/; do [ "$(basename "$d")" = templates ] || cp -R "${d%/}" ~/.claude/skills/; done
cp commands/*.md ~/.claude/commands/
```

For Cursor, Codex and Gemini CLI, and the per-project `CLAUDE.md` template, see [skills/README.md](skills/README.md). A test checks that every tool the skills name exists in this server.

---

## 🧩 Components

1. **Ableton Remote Script** (`AbletonMCP_Remote_Script/__init__.py`): a Python control surface script that runs inside Live, listens on a local socket and executes commands on Live's main thread. A byte-identical copy ships in `MCP_Server/bundled_ableton_remote_script/` for the installer.
2. **MCP server** (`MCP_Server/server.py`): implements the Model Context Protocol and talks to the Remote Script.

---

## 📦 Installation

### Prerequisites

- **Ableton Live 11 or newer.** Developed and verified on **Live 11.3.43**. Live 12 should work and unlocks native arrangement MIDI clips and locator renaming, but it hasn't been tested end to end yet. Live 10 is not supported, because its Remote Scripts run on Python 2.
- **Python 3.10 or newer** (uv provides it if you don't have it)
- **uv** package manager

If you're on Mac, install uv with:

```
brew install uv
```

Otherwise, install from [uv's official website](https://docs.astral.sh/uv/getting-started/installation/).

### Claude for Desktop Integration

Go to **Claude → Settings → Developer → Edit Config → `claude_desktop_config.json`** and add:

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "uvx",
            "args": ["--from", "git+https://github.com/Vitraya-AI/ableton-mcp", "ableton-mcp"]
        }
    }
}
```

<details>
<summary><b>Running from a local clone</b> (for development, or to pin a branch)</summary>

```bash
git clone https://github.com/Vitraya-AI/ableton-mcp.git
```

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "/opt/homebrew/bin/uv",
            "args": ["--directory", "/path/to/ableton-mcp", "run", "ableton-mcp"]
        }
    }
}
```

Use the full path to `uv` (`which uv`): Claude Desktop doesn't inherit your shell's PATH. Whatever branch is checked out in that folder is what runs the next time Claude starts.
</details>

### Cursor Integration

Go to **Cursor Settings → MCP** and paste this as a command:

```
uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp
```

> **Warning:** Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both.

### Claude Code Integration

In the terminal, run:

```
claude mcp add AbletonMCP -- uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp
```

### Installing the Ableton Remote Script

Install the Remote Script with:

```bash
uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp-install-script
uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp-install-script --list-targets   # preview target folders first
```

> From a local clone, the same command is `uv --directory /path/to/ableton-mcp run ableton-mcp-install-script`.

This copies the matching Remote Script into your Ableton **User Library**'s `Remote Scripts` folder, the location Live scans for third-party control surface scripts. The installer reads the User Library location from Live's `Library.cfg`, falling back to the default (`~/Music/Ableton/User Library` on macOS, `Documents\Ableton\User Library` on Windows). If a different version of the script is already there, the existing file is backed up to `__init__.py.bak` before being replaced.

If your User Library lives somewhere non-standard and isn't detected, point the installer at it directly:

```bash
uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp-install-script --target "/path/to/User Library/Remote Scripts"
```

> The legacy `Preferences/User Remote Scripts` folder (used for instant-mapping configs, not Python control surfaces) is no longer targeted by default; pass `--legacy` if you need it.

Then **restart Ableton** so Live loads it. 🔁 Re-run the installer **and restart Live** after every update. Live only reads Remote Scripts at startup, so the server warns when the loaded script version doesn't match what it expects. Live also reopens your last saved set when it restarts, so save first.

> **Note:** The server does **not** install the script on startup. Writing into Ableton's preferences directory is an explicit action, not a side effect of launching a server.

**First-time Ableton setup:**

1. Run the install command above
2. Launch Ableton Live
3. Go to **Settings/Preferences → Link, Tempo & MIDI**
4. In the **Control Surface** dropdown, select **AbletonMCP**
5. Set **Input** and **Output** to **None**

<details>
<summary><b>Manual fallback locations (User Library → Remote Scripts)</b></summary>

- **macOS:** `~/Music/Ableton/User Library/Remote Scripts/AbletonMCP/`
- **Windows:** `C:\Users\[Username]\Documents\Ableton\User Library\Remote Scripts\AbletonMCP\`

Copy `AbletonMCP_Remote_Script/__init__.py` there. If you've moved your User Library, use its actual location (shown in Live under **Preferences → Library → Location of User Library**), and create the `Remote Scripts` folder inside it if it doesn't exist yet.
</details>

Ask Claude to run `get_remote_script_info` to confirm the setup. It reports the Remote Script version (`up_to_date: true` when it matches the server), your Live version, and which version-dependent Live features are available (`live_api`).

---

## 🎧 Usage

### Starting the Connection

1. Make sure the AbletonMCP control surface is selected in Live
2. Make sure the MCP server is configured in your client
3. The connection is made automatically on your first request

Once both are running, you'll see the Ableton MCP tools in your client (the hammer icon in Claude Desktop).

### Example Commands

| Prompt |
|---|
| *"Create an 80s synthwave track"* ([demo](https://youtu.be/VH9g66e42XA)) |
| *"Create a full arrangement with an intro, buildup, drop, breakdown, and outro"* |
| *"Put an 8-bar bass line in the arrangement starting at bar 17"* |
| *"Remove the kick from bar 2 and make the snares softer"* |
| *"Shift every hi-hat in the chorus clip up an octave and give them 70% probability"* |
| *"Turn the bass down a little and pan the hats slightly right"* |
| *"Loop bars 9 to 16 and jump to the Verse locator"* |
| *"Lower the cutoff on the filter inside the Instrument Rack on track 1"* |
| *"Bypass the reverb on the vocal chain, then undo that"* |
| *"Load an 808 drum rack on a new track and tell me which pads are filled"* |
| *"Set the tempo to 120 BPM and the time signature to 6/8"* |

---

## 🩺 Troubleshooting

| Problem | Fix |
|---|---|
| **Connection issues** | Make sure AbletonMCP is selected as a Control Surface in Live, and the MCP server is configured in your client |
| **"Remote Script missing capability …" or `up_to_date: false`** | Live is running an older Remote Script. Re-run the install command, then restart Live |
| **New features missing after updating** | Restart Live after installing; it only loads Remote Scripts at startup |
| **Your set changed after a restart** | Live reopens the last *saved* set, so save before reinstalling the Remote Script |
| **Timeout errors** | Break big requests into smaller steps. `get_browser_tree` is capped at depth 2; use `get_browser_items_at_path` to go deeper |
| **Checking what happened** | Claude Desktop logs the server to `~/Library/Logs/Claude/mcp-server-AbletonMCP.log`. The Remote Script writes to Live's `Log.txt`, including every playhead move and locator change |
| **Have you tried turning it off and on again?** | Restart both your client and Ableton Live |

---

## ⚙️ Technical details

### Communication Protocol

JSON over a local TCP socket (port 9877). The Remote Script listens on **127.0.0.1 only**, so nothing else on your network can drive Live. To run the server and Live on different machines, set `ABLETON_MCP_HOST` for the Remote Script and `ABLETON_HOST` / `ABLETON_PORT` for the server, and only on a trusted network.

- **Commands** are JSON objects with a `type` and optional `params`
- **Responses** are JSON objects with a `status` and either a `result`, or a `message` and an error `code`

### How commands run

- Commands that change Live run on Live's main thread. Each edit is **one undo step**, so a single `undo` reverses the whole command, even when it takes several internal steps. Moving the playhead or jumping between locators adds no undo steps.
- Commands that move the playhead or loop **wait for Live** to apply the change before acting or reading back, and give up with a `timeout` code if Live never does.
- The handshake reports the Remote Script version, its capabilities, the Live version, and flags such as `track_create_midi_clip` or `cue_point_set_name`. Tools use these to choose the right code path for your Live version, or to refuse cleanly.

---

## ⚠️ Limitations

- **Live 11 can't rename locators from a script.** `create_locator` places the locator but it keeps Live's name ("1", "2", …); the reply says so, and `cue_point` can jump to it by that name. Live 12 allows renaming.
- **Arrangement MIDI clips on Live 11** are built in a temporary Session clip, so the track needs one empty Session slot.
- **Rack addressing goes one level deep**: a device inside a chain is reachable, but not the devices inside a rack nested within that chain.
- **Preset stepping** (`navigate_device_preset`) works only with plugins that expose their program list to Live. Some, like Serum 2, show a single preset.
- **Third-party plugin loading and automation curves** aren't available yet (see the [Roadmap](#-roadmap)).
- Always save your work before extensive experimentation.

---

## 🔒 Telemetry and data

The original Ableton MCP includes two kinds of data collection: **anonymous usage telemetry** (on by default: install ID, which tools ran, success and timing) and opt-in **dataset recording**, which uploads prompts, MIDI, track and clip names and device settings to an open music-production training dataset. [TERMS.md](TERMS.md) describes the original project's hosted service.

### What 2.0 changed

- 🚫 **Nothing is sent.** Both kinds of collection upload to the original maintainer's Supabase project, using credentials from `MCP_Server/config.py`. That file isn't part of this repository, and without it telemetry and dataset recording are switched off entirely. The code is kept, unchanged, so this project stays easy to merge with the original.
- 🙈 **No consent prompt.** The original asks every user to opt in: through a client dialog where the client supports one, and otherwise by adding a question to tool results that tells the AI what to ask you. 2.0 shows neither. Asking for consent belongs in your client's interface, not in text that instructs the model.
- ✂️ **Less context.** The six dataset-only tools (`set_dataset_consent`, `submit_intent`, `rate_last_action`, `reject_last_action`, `prefer_candidate`, `record_audition`) and the `user_prompt` parameter on every tool are hidden from the model. That trims the tool list by about 30%.

This is all done in one small module, `MCP_Server/dataset_visibility.py`, so the original tool code is untouched.

### Environment variables (still honored)

| Variable | Effect |
|---|---|
| `ABLETON_MCP_DISABLE_TELEMETRY=true` | Turns off telemetry and dataset recording (also `DISABLE_TELEMETRY`, `MCP_DISABLE_TELEMETRY`) |
| `ABLETON_MCP_DISABLE_DATASET=true` | Turns off dataset recording only, overriding any stored consent |
| `ABLETON_MCP_ENABLE_DATASET=true` | Opts in to dataset recording and shows the dataset tools again (only has an effect with your own `config.py`) |
| `ABLETON_MCP_SHOW_DATASET_TOOLS=true` | Shows the hidden dataset tools without opting in |

For Claude Desktop, put them in the server's `env`:

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "uvx",
            "args": ["--from", "git+https://github.com/Vitraya-AI/ableton-mcp", "ableton-mcp"],
            "env": {
                "ABLETON_MCP_DISABLE_TELEMETRY": "true"
            }
        }
    }
}
```

---

## 🛠️ Development

```bash
git clone https://github.com/Vitraya-AI/ableton-mcp.git && cd ableton-mcp
uv run --with pytest python -m pytest -q        # full test suite, no Ableton needed
```

- **Tests** replace Live with fake objects that apply changes one update late, as Live does. New tests are checked to fail against the code from before the feature they cover.
- **Live checklist:** [`docs/manual-smoke-tests.md`](docs/manual-smoke-tests.md) lists the checks to run in a real Live set after changing the Remote Script.
- **Live API reference for your own build:** with Live running, `uv run ableton-mcp-dump-live-api` writes every class, member and call signature of your Live's Python API to `docs/live-api/<version>/` (about 8 seconds; gitignored).
- **Remote Script rules:** Python 3.7 syntax (Live 11's interpreter); keep `AbletonMCP_Remote_Script/__init__.py` and the bundled copy identical; bump `SCRIPT_VERSION` and `EXPECTED_REMOTE_SCRIPT_VERSION` together. Any command that writes Live state and then depends on it must wait for Live between steps. The full checklist is in [`docs/extended-features-plan.md`](docs/extended-features-plan.md).

---

## 🗺️ Roadmap

### ✅ Done
- [x] Note editing by note ID: read, modify, remove by window; probability and velocity deviation
- [x] Note names in Ableton's convention (C3 = 60)
- [x] Mixer: volume, pan, mute, solo, arm, sends, master
- [x] Scenes, clip duplication, track deletion, time signature
- [x] Undo and redo, with every edit as a single undo step
- [x] Structured error codes on every failure
- [x] Fix: rejected commands no longer drop the connection
- [x] Fix: each command keeps its own timeout
- [x] Browser tree depth option, capped at the timeout
- [x] Live version and API-availability handshake
- [x] Live API dump for your own Live build
- [x] Bar/beat positions that follow Live's ruler and time signature
- [x] Arrangement overview, locators and cue navigation, loop
- [x] Arrangement MIDI and audio clip creation (Live 11 and 12)
- [x] Note and clip-property editing on Arrangement clips
- [x] Commands wait for Live before acting on playhead or loop changes
- [x] Rack inspection, chain devices, drum pads mapped to chains
- [x] Device parameters by name; device on/off and deletion; plugin presets
- [x] Loading an instrument reports the device that appeared
- [x] Telemetry and dataset hidden and inactive; consent prompt removed from tool output
- [x] Verified end to end in Ableton Live 11.3.43
- [x] Agent skills and slash commands tailored to 2.0

### 🔜 Still to do
- [ ] 🔌 Third-party plugins: list and load VST/AU plugins in one request, with friendly parameter names for popular synths
- [ ] 📈 Automation curves: write envelope points on Session clips (Live 11 has no clip-envelope access for Arrangement clips, so that needs another route)
- [ ] 🔁 Reconnect and retry read commands automatically after Live restarts
- [ ] 📦 Batch command: run several steps in one round trip
- [ ] 🎚️ Verify preset stepping with a plugin that exposes its program list
- [ ] 🆕 Test end to end on Live 12 (native arrangement MIDI clips, locator renaming)
- [ ] 🪆 Address devices in racks nested more than one level deep
- [ ] 🚀 Publish 2.0 as a package so plain `uvx` installs it
- [ ] 📊 Read track and master level meters (the mix and mastering skills ask the user for now)
- [ ] 🔀 Create return tracks, and load devices on returns and the master
- [ ] 🏷️ Show parameter values as Live displays them (Hz, dB, ms), not just raw values
- [ ] 🎨 Set track colours
- [ ] 🧵 Choose a compressor's sidechain source

---

## 🙏 Credits

- **[Siddharth Ahuja](https://x.com/sidahuj)** created the original [Ableton MCP](https://github.com/ahujasid/ableton-mcp), which this project builds on, including its setup and installer. Its community is on [Discord](https://discord.gg/JK4hNKGprW).
- **[uisato/ableton-mcp-extended](https://github.com/uisato/ableton-mcp-extended)** inspired the arrangement and device features.
- Live 11 API research used the runtime captures at [midiremotescripts.structure-void.com](https://midiremotescripts.structure-void.com/).

## 🤝 Contributing

Contributions are welcome! Please open an issue or a Pull Request on [Vitraya-AI/ableton-mcp](https://github.com/Vitraya-AI/ableton-mcp).

## 📄 Disclaimer

This is a third-party integration and not made by Ableton.

---

<div align="center">

**If Ableton MCP 2.0 is useful to you, consider starring the repo ⭐**

</div>
