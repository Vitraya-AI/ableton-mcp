"""Keep the dataset feature out of the model's context unless it is in use.

Upstream ships dataset recording as part of every session: six tools that only
serve the dataset, a ``user_prompt`` parameter on every tool, and a consent
question appended to tool results. Together that is roughly a third of the
tool list the client loads into context, spent on a feature that records
nothing unless the user has opted in.

``apply()`` runs once at startup. Unless dataset recording is already granted
(or ``ABLETON_MCP_SHOW_DATASET_TOOLS`` is set), it:

* unregisters the dataset-only tools,
* drops ``user_prompt`` from each tool's advertised schema and docstring (the
  functions still accept it, defaulting to ""), and
* stops the consent question, which would otherwise ask the model to call
  ``set_dataset_consent`` after it has been hidden.

It works on the registered tools rather than their definitions, so upstream's
tool code stays untouched and merges cleanly. Opting in still works through
``ABLETON_MCP_ENABLE_DATASET=1``, which makes everything visible again.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger("AbletonMCPServer")

DATASET_TOOLS = (
    "set_dataset_consent",
    "submit_intent",
    "rate_last_action",
    "reject_last_action",
    "prefer_candidate",
    "record_audition",
)

_USER_PROMPT_DOC = re.compile(r"^[ \t]*- user_prompt:.*\n?", re.MULTILINE)


def _show_requested() -> bool:
    value = os.environ.get("ABLETON_MCP_SHOW_DATASET_TOOLS", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def should_hide() -> bool:
    """Hide unless the user opted in or asked to see the dataset tools."""
    if _show_requested():
        return False
    from .dataset.consent import GRANTED, consent_state

    return consent_state() != GRANTED


def _strip_user_prompt(tool) -> None:
    schema = tool.parameters or {}
    schema.get("properties", {}).pop("user_prompt", None)
    required = schema.get("required")
    if required and "user_prompt" in required:
        schema["required"] = [name for name in required if name != "user_prompt"]
    if tool.description:
        tool.description = _USER_PROMPT_DOC.sub("", tool.description)


def apply(mcp) -> bool:
    """Hide the dataset surface on ``mcp`` when appropriate. True if hidden."""
    if not should_hide():
        return False

    manager = mcp._tool_manager
    for name in DATASET_TOOLS:
        if manager.get_tool(name) is not None:
            manager.remove_tool(name)

    for tool in manager.list_tools():
        _strip_user_prompt(tool)

    from .dataset import consent

    consent.suppress_prompt()

    logger.info(
        "Dataset tools hidden (not opted in). Set ABLETON_MCP_SHOW_DATASET_TOOLS=1 "
        "or ABLETON_MCP_ENABLE_DATASET=1 to show them."
    )
    return True
