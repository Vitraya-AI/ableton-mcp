---
name: ableton-debug
description: Diagnose connection or behavior problems between the AI client and Ableton Live with Ableton MCP 2.0. Use when tools don't respond, AbletonMCP doesn't appear in Live's preferences, tools report a missing capability, or commands time out.
---

# /ableton-debug

Walk a structured diagnosis when something is broken between the client and
Ableton Live.

## 1. Check the connection and versions

Call `get_remote_script_info`:

| Result | Meaning | Fix |
|---|---|---|
| JSON with `up_to_date: true` | Server and Remote Script match | Connection is fine; go to step 3 |
| `up_to_date: false`, or a tool says "Ableton Remote Script missing capability …" | Live is running an older Remote Script | Reinstall and **restart Live** (step 2) |
| `script_version: "legacy"` | A pre-handshake Remote Script (the original project's) | Reinstall (step 2) |
| "Could not connect to Ableton" / connection refused | Live not running, or AbletonMCP not selected as a control surface | Step 2, checks 1–2 |
| Timeout | Live is busy or frozen (big browser walk, heavy set) | Wait, then retry once; if it persists, restart Live |

## 2. Verify the setup, in order

Ask the user to confirm each; fix the first ❌ before moving on.

1. ✅ Ableton Live **11 or newer** is open with a set loaded (Live 10 is not supported).
2. ✅ Settings → Link, Tempo & MIDI → a **Control Surface** slot shows **AbletonMCP**, Input/Output **None**.
3. ✅ The Remote Script is installed in the **User Library**:
   `~/Music/Ableton/User Library/Remote Scripts/AbletonMCP/` (macOS) or
   `Documents\Ableton\User Library\Remote Scripts\AbletonMCP\` (Windows).
   Reinstall with:
   `uvx --from git+https://github.com/Vitraya-AI/ableton-mcp ableton-mcp-install-script`
   (or `uv --directory <clone> run ableton-mcp-install-script`), then
   **restart Live**. It only loads Remote Scripts at startup.
4. ✅ The MCP client shows the AbletonMCP server as connected (not "error").
5. ✅ Only **one** client runs the server (not Claude Desktop and Cursor at once).

## 3. Common symptoms

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| AbletonMCP missing from the Control Surface list | Script not in `User Library/Remote Scripts/AbletonMCP/` | Reinstall (step 2.3); `--list-targets` shows where it installs |
| New tools missing or refused after an update | Live still runs the old script | Restart Live after installing |
| The set looks different after a restart | Live reopened the last **saved** set | Save before reinstalling |
| First command after restarting Live fails, the next works | The server's socket was closed by the restart | Retry once |
| `get_browser_tree` times out | Deep browser walks exceed the 10 s read timeout | Depth is capped at 2; use `get_browser_items_at_path` |
| An edit "didn't happen" | Wrong index, or the set changed | Re-read with `get_session_info` / `get_arrangement_info`; indices are 0-based |
| Locator names don't apply | Live 11 can't rename locators from a script | Expected; see `get_remote_script_info` → `live_api.cue_point_set_name` |
| Server on another machine / WSL can't connect | The Remote Script listens on 127.0.0.1 only | Set `ABLETON_MCP_HOST` for Live and `ABLETON_HOST`/`ABLETON_PORT` for the server, on a trusted network only |

Every tool error ends with `(code: …)`; the table in `using-ableton-mcp`
explains each.

## 4. Logs

- **MCP server** (Claude Desktop): `~/Library/Logs/Claude/mcp-server-AbletonMCP.log`.
  Look for "Connected to Ableton", "Remote Script handshake", and lines with
  `ERROR`. Each command's duration is visible from its "Sending command" and
  "Received" timestamps.
- **Remote Script** (inside Live): Live's `Log.txt`, e.g.
  `~/Library/Preferences/Ableton/Live 11.3.43/Log.txt` on macOS. It records
  commands, device loads, playhead moves and locator changes.

Ask the user for the most recent error lines.

## 5. Last resort

1. Save the set, quit Live.
2. Reinstall the Remote Script (step 2.3).
3. Restart the MCP client (it restarts the server).
4. Start Live; re-select AbletonMCP as the control surface if needed.
5. `get_remote_script_info` again.

## Don'ts

- Don't suggest deleting Live's preference files. It's rarely needed and loses the user's settings; only mention it with a backup, as a last resort.
- Don't `pip install` random packages; the server runs from uv.
- Don't run `rm -rf` on anything.
- Don't blame the user; find the actual cause.
