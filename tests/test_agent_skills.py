"""The agent skills and slash commands must only name tools this server has.

The skills came from a project written against other Ableton MCP servers;
11 of the tools they named didn't exist here (set_clip_notes, add_device,
load_browser_item, ...). An agent following such a skill calls a tool that
isn't there. These tests keep the skills in step with the tool list.
"""

import asyncio
import re
from pathlib import Path

import pytest

import MCP_Server.server as server
from MCP_Server import dataset_visibility

REPO = Path(__file__).resolve().parents[1]
SKILLS = sorted(p for p in (REPO / "skills").glob("*/SKILL.md"))
COMMANDS = sorted((REPO / "commands").glob("*.md"))
DOCS = SKILLS + COMMANDS + [REPO / "skills" / "templates" / "CLAUDE.md"]

# A backticked identifier that starts like a tool call is treated as one.
TOOL_LIKE = re.compile(
    r"`((?:get|set|create|add|delete|load|remove|modify|clear|fire|stop|start|"
    r"duplicate|navigate|switch|save|jump|undo|redo|cue)_?[a-z_]*)`")


def _visible_tools():
    """Tools an agent actually sees (dataset tools are hidden by default)."""
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    return names - set(dataset_visibility.DATASET_TOOLS)


# Note fields the skills talk about; they're data, not tools.
NOTE_FIELDS = {"start_time"}


def _non_tool_words():
    """Identifiers that look like tool calls but aren't: every tool's
    parameter names, note fields, and the error codes the Remote Script
    raises. Derived from the code so the list can't go stale."""
    words = set(NOTE_FIELDS)
    for tool in asyncio.run(server.mcp.list_tools()):
        words |= set(tool.inputSchema.get("properties", {}))
    script = (REPO / "AbletonMCP_Remote_Script" / "__init__.py").read_text(encoding="utf-8")
    words |= set(re.findall(r'"([a-z]+(?:_[a-z]+)+)"\)', script))
    return words


def _frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert match, "%s has no frontmatter" % path
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def test_there_are_skills_and_commands():
    assert len(SKILLS) == 13
    assert len(COMMANDS) == 4


@pytest.mark.parametrize("path", DOCS, ids=lambda p: str(p.relative_to(REPO)))
def test_only_real_tools_are_named(path):
    tools = _visible_tools()
    named = set(TOOL_LIKE.findall(path.read_text(encoding="utf-8"))) - _non_tool_words()
    unknown = sorted(n for n in named if n not in tools)
    assert not unknown, "%s names tools this server doesn't have: %s" % (
        path.relative_to(REPO), unknown)


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter_matches_its_folder(path):
    fields = _frontmatter(path)
    assert fields.get("name") == path.parent.name
    assert len(fields.get("description", "")) > 40


@pytest.mark.parametrize("path", COMMANDS, ids=lambda p: p.stem)
def test_command_frontmatter_matches_its_file(path):
    fields = _frontmatter(path)
    assert fields.get("name") == path.stem
    assert fields.get("description")


def test_the_tool_pattern_catches_the_upstream_mistakes():
    """Guard the guard: the names that were wrong upstream must be flagged."""
    tools = _visible_tools()
    for bad in ("set_clip_notes", "add_device", "load_browser_item",
                "get_notes_from_clip", "create_return_track", "set_track_color",
                "save_device_preset", "create_arrangement_clip"):
        assert TOOL_LIKE.fullmatch("`%s`" % bad)
        assert bad not in tools
        assert bad not in _non_tool_words()


def test_skills_use_abletons_octave_convention():
    """Textbook names put middle C at C4; Ableton (and the server) at C3.
    The string ranges were copied an octave high upstream."""
    text = (REPO / "skills" / "midi-cleanup" / "SKILL.md").read_text(encoding="utf-8")
    assert "G2–G5 (MIDI 55–91)" in text
    assert server._parse_pitch("G2") == 55 and server._parse_pitch("G5") == 91


def test_upstream_license_notice_is_kept():
    text = (REPO / "skills" / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text and "Glincker" in text
