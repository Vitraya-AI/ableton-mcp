"""Hiding the dataset feature from the model unless it is in use."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from MCP_Server import dataset_visibility
from MCP_Server.dataset import consent

REPO_ROOT = Path(__file__).resolve().parents[1]


def _toy_server():
    mcp = FastMCP("toy")

    @mcp.tool()
    def set_dataset_consent(consent: bool, user_said: str = "") -> str:
        """Record consent."""
        return ""

    @mcp.tool()
    def undo(user_prompt: str = "") -> str:
        """
        Undo the last change.

        Parameters:
        - user_prompt: The original user prompt that led to this tool call (for telemetry)
        """
        return "Undid the last change"

    return mcp


@pytest.fixture
def not_opted_in(monkeypatch):
    monkeypatch.delenv("ABLETON_MCP_SHOW_DATASET_TOOLS", raising=False)
    monkeypatch.setattr(consent, "consent_state", lambda: consent.UNKNOWN)
    monkeypatch.setattr(consent, "_prompt_suppressed", False)


def _tools(mcp):
    return {t.name: t for t in asyncio.run(mcp.list_tools())}


def test_hides_dataset_tools_and_user_prompt(not_opted_in):
    mcp = _toy_server()
    assert dataset_visibility.apply(mcp) is True

    tools = _tools(mcp)
    assert "set_dataset_consent" not in tools
    undo = tools["undo"]
    assert "user_prompt" not in undo.inputSchema["properties"]
    assert "user_prompt" not in undo.description
    assert "Undo the last change." in undo.description


def test_hidden_parameter_is_still_accepted(not_opted_in):
    """Clients never send it now, but an explicit value must not break."""
    mcp = _toy_server()
    dataset_visibility.apply(mcp)
    result = asyncio.run(mcp.call_tool("undo", {"user_prompt": "x"}))
    assert "Undid the last change" in json.dumps(result, default=str)


def test_hiding_suppresses_the_consent_question(not_opted_in):
    dataset_visibility.apply(_toy_server())
    assert consent._prompt_suppressed is True
    assert consent.may_ask_now() is False
    assert consent.maybe_consent_notice() == ""


def test_opted_in_users_keep_everything(monkeypatch):
    monkeypatch.setattr(consent, "consent_state", lambda: consent.GRANTED)
    mcp = _toy_server()
    assert dataset_visibility.apply(mcp) is False
    assert "set_dataset_consent" in _tools(mcp)


def test_env_var_shows_the_tools(monkeypatch, not_opted_in):
    monkeypatch.setenv("ABLETON_MCP_SHOW_DATASET_TOOLS", "1")
    mcp = _toy_server()
    assert dataset_visibility.apply(mcp) is False
    assert "set_dataset_consent" in _tools(mcp)


def test_real_server_tool_list_is_clean(tmp_path):
    """Apply to the real server in a fresh process with no stored consent."""
    script = (
        "import asyncio, json\n"
        "import MCP_Server.server as s\n"
        "from MCP_Server import dataset_visibility\n"
        "dataset_visibility.apply(s.mcp)\n"
        "tools = asyncio.run(s.mcp.list_tools())\n"
        "print(json.dumps([t.model_dump(exclude_none=True) for t in tools]))\n"
    )
    env = dict(os.environ, ABLETON_MCP_STATE_DIR=str(tmp_path),
               ABLETON_MCP_DISABLE_TELEMETRY="1")
    env.pop("ABLETON_MCP_SHOW_DATASET_TOOLS", None)
    env.pop("ABLETON_MCP_ENABLE_DATASET", None)
    out = subprocess.run([sys.executable, "-c", script], cwd=REPO_ROOT, env=env,
                         capture_output=True, text=True, check=True).stdout
    tools = json.loads(out.strip().splitlines()[-1])

    names = {t["name"] for t in tools}
    assert not names & set(dataset_visibility.DATASET_TOOLS)
    assert {"undo", "get_session_snapshot", "set_track_volume"} <= names
    for tool in tools:
        assert "user_prompt" not in tool["inputSchema"].get("properties", {}), tool["name"]
        assert "user_prompt" not in tool.get("description", ""), tool["name"]
