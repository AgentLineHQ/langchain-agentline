"""AgentLine LangChain tools.

Each tool wraps a subset of the AgentLine REST API (https://api.agentline.cloud/v1/).

Auth is via Bearer token passed as AGENTLINE_API_KEY env var or directly.

Limitations in the current AgentLine API (as of July 2026):
    - Outbound SMS/MMS sending is NOT enabled (POST /v1/messages exists but returns errors)
    - WhatsApp messaging is not supported (no API endpoints exist)
    - Calls are fully functional
    - Inbound SMS reading is fully functional
"""

from __future__ import annotations

import json
import os
from typing import Optional, Type

import requests
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

BASE_URL = "https://api.agentline.cloud/v1"


def _get_api_key(api_key: Optional[str] = None) -> str:
    """Resolve API key from arg, env var, or config file."""
    if api_key:
        return api_key
    key = os.environ.get("AGENTLINE_API_KEY")
    if key:
        return key
    # Try config file as last resort
    config_path = os.path.expanduser("~/.config/agentline/api_key")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return f.read().strip()
    raise ValueError(
        "AgentLine API key not found. Set AGENTLINE_API_KEY env var or pass api_key=..."
    )


def _make_request(
    method: str,
    path: str,
    api_key: Optional[str] = None,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
) -> dict:
    """Make an authenticated request to the AgentLine API."""
    headers = {
        "Authorization": f"Bearer {_get_api_key(api_key)}",
        "Content-Type": "application/json",
    }
    url = f"{BASE_URL}{path}"
    response = requests.request(
        method, url, headers=headers, json=json_body, params=params, timeout=30
    )
    response.raise_for_status()
    return response.json()


# ── Input schemas ──────────────────────────────────────────────────────


class MakeCallInput(BaseModel):
    """Input for making an outbound phone call."""

    agent_id: str = Field(
        description="The AgentLine agent ID to use for the call."
    )
    to_number: str = Field(
        description="Phone number to call in E.164 format (e.g. +15551234567)."
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional per-call override for the agent's system prompt.",
    )
    initial_greeting: Optional[str] = Field(
        default=None,
        description="Optional per-call override for the initial greeting the agent speaks.",
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="Optional voice preset: female-1, female-2, female-3, male-1, male-2, male-3.",
    )


class GetCallsInput(BaseModel):
    """Input for retrieving call history."""

    agent_id: Optional[str] = Field(
        default=None,
        description="Filter calls by agent ID. If omitted, returns all calls.",
    )
    status: Optional[str] = Field(
        default=None,
        description="Filter by call status (e.g. completed, in_progress, failed).",
    )
    limit: int = Field(
        default=10,
        description="Maximum number of calls to return (1-100).",
    )


class GetMessagesInput(BaseModel):
    """Input for reading inbound SMS messages."""

    agent_id: Optional[str] = Field(
        default=None,
        description="Filter messages by agent ID. If omitted, returns all messages.",
    )
    limit: int = Field(
        default=20,
        description="Maximum number of messages to return (1-100).",
    )


# ── Tools ──────────────────────────────────────────────────────────────


class AgentLineCallTool(BaseTool):
    """Make an outbound phone call using an AgentLine agent.

    Your AI agent can speak to real people on the phone. The agent follows
    its system prompt and can have natural conversations.

    Call costs $0.10/minute. Minimum balance required: $0.50 (~5 minutes).

    Returns the call ID and status so you can check back later for the transcript.
    """

    name: str = "agentline_make_call"
    description: str = (
        "Make an outbound phone call from an AgentLine AI agent. "
        "Provide agent_id and to_number (E.164 format like +15551234567). "
        "Optionally override the system_prompt, initial_greeting, or voice_id. "
        "Returns call details including call_id for later transcript retrieval."
    )
    args_schema: Type[BaseModel] = MakeCallInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(
        self,
        agent_id: str,
        to_number: str,
        system_prompt: Optional[str] = None,
        initial_greeting: Optional[str] = None,
        voice_id: Optional[str] = None,
        run_manager=None,
    ) -> str:
        body = {
            "agent_id": agent_id,
            "to_number": to_number,
        }
        if system_prompt:
            body["system_prompt"] = system_prompt
        if initial_greeting:
            body["initial_greeting"] = initial_greeting
        if voice_id:
            body["voice_id"] = voice_id

        result = _make_request("POST", "/calls", api_key=self.api_key, json_body=body)
        return json.dumps(result, indent=2, default=str)


class AgentLineGetCallsTool(BaseTool):
    """Retrieve call history, status, and transcripts from AgentLine.

    Use this to check on in-progress calls, review completed calls,
    and get transcripts of conversations your agents have had.
    """

    name: str = "agentline_get_calls"
    description: str = (
        "Get call history from AgentLine. Can filter by agent_id and status. "
        "Returns call IDs, statuses, from/to numbers, and timestamps. "
        "Use call IDs to fetch full transcripts."
    )
    args_schema: Type[BaseModel] = GetCallsInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
        run_manager=None,
    ) -> str:
        params = {"limit": min(limit, 100)}
        if agent_id:
            params["agent_id"] = agent_id
        if status:
            params["status"] = status

        result = _make_request("GET", "/calls", api_key=self.api_key, params=params)
        return json.dumps(result, indent=2, default=str)


class AgentLineGetMessagesTool(BaseTool):
    """Read inbound SMS messages received by your AgentLine phone numbers.

    When someone texts your agent's phone number, the message appears here.
    Outbound SMS sending is not currently supported by the AgentLine API.
    """

    name: str = "agentline_get_messages"
    description: str = (
        "Read inbound SMS messages received by AgentLine phone numbers. "
        "Filter by agent_id if you have multiple agents. "
        "Returns message body, from_number, to_number, and timestamps. "
        "NOTE: Outbound SMS sending is not yet supported by AgentLine."
    )
    args_schema: Type[BaseModel] = GetMessagesInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(
        self,
        agent_id: Optional[str] = None,
        limit: int = 20,
        run_manager=None,
    ) -> str:
        params = {"limit": min(limit, 100)}
        if agent_id:
            params["agent_id"] = agent_id

        result = _make_request(
            "GET", "/messages", api_key=self.api_key, params=params
        )
        return json.dumps(result, indent=2, default=str)


class AgentLineListAgentsTool(BaseTool):
    """List all configured AgentLine agents and their phone numbers.

    Useful for discovering which agents are available and their IDs
    before making calls or checking messages.
    """

    name: str = "agentline_list_agents"
    description: str = (
        "List all AgentLine agents in your account. "
        "Returns agent IDs, names, phone numbers, and system prompts. "
        "Use this to find agent_id values needed by other AgentLine tools."
    )
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(self, run_manager=None) -> str:
        result = _make_request("GET", "/agents", api_key=self.api_key)
        return json.dumps(result, indent=2, default=str)
