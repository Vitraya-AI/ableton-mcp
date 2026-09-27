# 🎓 Agent skills for Ableton MCP 2.0

Skills and slash commands that teach an AI agent (Claude Code, Claude
Desktop projects, Cursor, Codex, Gemini CLI) to use Ableton MCP 2.0 like a
co-producer: set up projects, write grooves and voiced chords, humanize and
voice-lead MIDI, build arrangements, design sounds, and diagnose mixes.

They're adapted from [glincker/ableton-skills](https://github.com/glincker/ableton-skills)
(MIT) and rewritten against 2.0's actual tools: every tool a skill names
exists in this server (a test enforces it), note names follow Ableton's
convention (C3 = 60), and anything 2.0 can't do comes with the manual step
for the user instead of a call to a tool that doesn't exist.

## Start here

| Skill | What it does |
|---|---|
| [`using-ableton-mcp`](using-ableton-mcp/SKILL.md) | **Foundation.** How the tools behave: indices, pitch and time conventions, Session vs Arrangement, devices and racks, error codes, undo, and what Live 11 / 2.0 can't do. Every other skill assumes it. |

## Workflow skills

| Skill | What it does |
|---|---|
| [`producer-mode`](producer-mode/SKILL.md) | Turns a brief into tracks, instruments, patterns and a playable scene |
| [`groove-builder`](groove-builder/SKILL.md) | Genre drum patterns on the kit's real pad notes, humanized |
| [`chord-pro`](chord-pro/SKILL.md) | Progressions with proper voicing and voice leading |
| [`midi-cleanup`](midi-cleanup/SKILL.md) | Humanize, quantize, probability, voice-leading fixes, all edited in place by note ID |
| [`arrangement-coach`](arrangement-coach/SKILL.md) | Session loops → a full Arrangement with sections, locators and fills |
| [`sound-designer`](sound-designer/SKILL.md) | Patches on Operator, Wavetable, Analog and Drift, parameters set by name |
| [`mixer-doctor`](mixer-doctor/SKILL.md) | Diagnoses muddy, harsh or buried mixes and applies moves one at a time |
| [`sidechain-setup`](sidechain-setup/SKILL.md) | Compressor ducking (kick → bass, vocal → bed) |
| [`vocal-chain`](vocal-chain/SKILL.md) | Pop, rap and indie vocal chains from stock devices |
| [`mastering-prep`](mastering-prep/SKILL.md) | Pre-master audit of the whole set, including the master chain |
| [`reference-match`](reference-match/SKILL.md) | "Make it sound like X" → the three most distinctive moves |
| [`tempo-coach`](tempo-coach/SKILL.md) | Tempo, time signature, half-time vs full-time, swing |

## Slash commands

| Command | Purpose |
|---|---|
| [`/ableton-init`](../commands/ableton-init.md) | Labeled track layout, tempo and a starter scene; guides the return/master setup |
| [`/ableton-snapshot`](../commands/ableton-snapshot.md) | Markdown snapshot of the set as a checkpoint |
| [`/ableton-export`](../commands/ableton-export.md) | Pre-export checklist |
| [`/ableton-debug`](../commands/ableton-debug.md) | Diagnose connection, version and behaviour problems |

## Install

The MCP server has to be set up first (see the main [README](../README.md#-quickstart)).

**Claude Code** (from a clone of this repository):

```bash
mkdir -p ~/.claude/skills ~/.claude/commands
for d in skills/*/; do                      # one folder per skill
  [ "$(basename "$d")" = templates ] || cp -R "${d%/}" ~/.claude/skills/
done
cp commands/*.md ~/.claude/commands/
```

Restart Claude Code. The skills load automatically when a task matches;
`/ableton-init` and the other commands appear in the slash menu.

**Per project:** copy [`templates/CLAUDE.md`](templates/CLAUDE.md) into your
Ableton project folder so every session starts with the co-producer context.

**Cursor:** copy the skill folders into `.cursor/rules/`. **Codex / Gemini
CLI:** reference `templates/CLAUDE.md` from your `AGENTS.md` / `GEMINI.md`.

## What the skills work around

These aren't in 2.0 yet (see the [roadmap](../README.md#-roadmap)), so the
skills hand the step to the user: creating return tracks, track colours,
devices on the master and returns, sidechain routing, automation, level
meters and loudness, saving presets, rendering, grouping, and locator
names on Live 11.

## Credits

Based on [ableton-skills](https://github.com/glincker/ableton-skills) by
Glincker, MIT License. See [LICENSE](LICENSE) for the original notice. The
musical guidance (genre tables, voicing rules, mix moves) comes from there;
the tool workflows, pitch conventions and 2.0-specific behaviour were
rewritten for this project.
