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


class ProvisionNumberInput(BaseModel):
    """Input for provisioning a phone number."""

    agent_id: str = Field(
        description="Agent ID to assign the phone number to."
    )
    area_code: Optional[str] = Field(
        default=None,
        description="Preferred 3-digit US area code (e.g. 415 for San Francisco).",
    )
    number_type: str = Field(
        default="local",
        description="Number type: 'local' or 'tollfree'.",
    )


class SetWebhookInput(BaseModel):
    """Input for setting up a webhook."""

    agent_id: str = Field(
        description="Agent ID to receive webhook events for."
    )
    url: str = Field(
        description="The URL that will receive POST requests for call and SMS events."
    )
    secret: Optional[str] = Field(
        default=None,
        description="Optional secret for HMAC webhook signature verification.",
    )


class CallIdInput(BaseModel):
    """Input requiring a call ID."""

    call_id: str = Field(
        description="The call ID to operate on."
    )


class AgentIdInput(BaseModel):
    """Input requiring only an agent ID."""

    agent_id: str = Field(
        description="The AgentLine agent ID."
    )


# ── CALL TOOLS ─────────────────────────────────────────────────────────


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
    """Retrieve call history and status from AgentLine."""

    name: str = "agentline_get_calls"
    description: str = (
        "Get call history from AgentLine. Can filter by agent_id and status. "
        "Returns call IDs, statuses, from/to numbers, and timestamps. "
        "Use call IDs with agentline_get_transcript to fetch full transcripts."
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


class AgentLineGetTranscriptTool(BaseTool):
    """Fetch the full transcript of a completed call."""

    name: str = "agentline_get_transcript"
    description: str = (
        "Get the full transcript of a specific call by its call_id. "
        "Returns a list of turns with role (agent/caller), text, and timestamps. "
        "Use agentline_get_calls first to find the call_id you want."
    )
    args_schema: Type[BaseModel] = CallIdInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(self, call_id: str, run_manager=None) -> str:
        result = _make_request(
            "GET", f"/calls/{call_id}/transcript", api_key=self.api_key
        )
        return json.dumps(result, indent=2, default=str)


class AgentLineHangupCallTool(BaseTool):
    """Hang up an active phone call."""

    name: str = "agentline_hangup_call"
    description: str = (
        "Hang up an active/in-progress phone call by its call_id. "
        "Use agentline_get_calls to find active calls first."
    )
    args_schema: Type[BaseModel] = CallIdInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(self, call_id: str, run_manager=None) -> str:
        result = _make_request(
            "POST", f"/calls/{call_id}/hangup", api_key=self.api_key
        )
        return json.dumps(result, indent=2, default=str)


# ── SMS TOOLS ──────────────────────────────────────────────────────────


class AgentLineGetMessagesTool(BaseTool):
    """Read inbound SMS messages received by your AgentLine phone numbers."""

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


# ── PHONE NUMBER TOOLS ─────────────────────────────────────────────────


class AgentLineProvisionNumberTool(BaseTool):
    """Provision (buy) a new phone number for an agent.

    Cost: $2.00 one-time. US numbers only. The number is immediately
    assigned to the specified agent and ready for calls.
    """

    name: str = "agentline_provision_number"
    description: str = (
        "Provision a new US phone number for an AgentLine agent. "
        "Costs $2.00 one-time. Requires agent_id. "
        "Optionally specify area_code (3 digits) and number_type ('local' or 'tollfree'). "
        "Returns the phone number and number_id."
    )
    args_schema: Type[BaseModel] = ProvisionNumberInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(
        self,
        agent_id: str,
        area_code: Optional[str] = None,
        number_type: str = "local",
        run_manager=None,
    ) -> str:
        body = {
            "agent_id": agent_id,
            "country": "US",
            "number_type": number_type,
        }
        if area_code:
            body["area_code"] = area_code

        result = _make_request(
            "POST", "/numbers", api_key=self.api_key, json_body=body
        )
        return json.dumps(result, indent=2, default=str)


class AgentLineGetNumbersTool(BaseTool):
    """List all phone numbers in your account."""

    name: str = "agentline_get_numbers"
    description: str = (
        "List all phone numbers in your AgentLine account. "
        "Returns number IDs, phone numbers, assigned agents, and status. "
        "Use number IDs with agentline_reassign_number."
    )
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(self, run_manager=None) -> str:
        result = _make_request("GET", "/numbers", api_key=self.api_key)
        return json.dumps(result, indent=2, default=str)


# ── AGENT TOOLS ────────────────────────────────────────────────────────


class AgentLineListAgentsTool(BaseTool):
    """List all configured AgentLine agents and their phone numbers."""

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


# ── WEBHOOK TOOLS ──────────────────────────────────────────────────────


class AgentLineSetWebhookTool(BaseTool):
    """Set up a webhook to receive real-time call and SMS events.

    AgentLine will POST events (call.received, call.completed, sms.received)
    to your URL. Optionally set a secret for HMAC signature verification.
    """

    name: str = "agentline_set_webhook"
    description: str = (
        "Set a webhook URL for an AgentLine agent. "
        "AgentLine will POST call and SMS events to this URL in real-time. "
        "Requires agent_id and url. Optionally set a secret for signature verification. "
        "Use agentline_list_webhooks to see existing webhooks."
    )
    args_schema: Type[BaseModel] = SetWebhookInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(
        self,
        agent_id: str,
        url: str,
        secret: Optional[str] = None,
        run_manager=None,
    ) -> str:
        body = {"agent_id": agent_id, "url": url}
        if secret:
            body["secret"] = secret

        result = _make_request(
            "POST", "/webhooks", api_key=self.api_key, json_body=body
        )
        return json.dumps(result, indent=2, default=str)


class AgentLineListWebhooksTool(BaseTool):
    """List all configured webhooks."""

    name: str = "agentline_list_webhooks"
    description: str = (
        "List all webhooks configured for your AgentLine account. "
        "Returns agent IDs, webhook URLs, and whether secrets are configured."
    )
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(self, run_manager=None) -> str:
        result = _make_request("GET", "/webhooks", api_key=self.api_key)
        return json.dumps(result, indent=2, default=str)


class AgentLineDeleteWebhookTool(BaseTool):
    """Remove a webhook for a specific agent."""

    name: str = "agentline_delete_webhook"
    description: str = (
        "Delete the webhook for a specific agent. "
        "Requires agent_id. After deletion, events for this agent "
        "will no longer be sent to any URL."
    )
    args_schema: Type[BaseModel] = AgentIdInput
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(self, agent_id: str, run_manager=None) -> str:
        result = _make_request(
            "DELETE", "/webhooks", api_key=self.api_key, params={"agent_id": agent_id}
        )
        return json.dumps(result, indent=2, default=str)


# ── BILLING TOOLS ──────────────────────────────────────────────────────


class AgentLineGetBalanceTool(BaseTool):
    """Check your account balance.

    Useful before making calls to ensure you have enough credit.
    Calls cost $0.10/min. Minimum balance for calls: $0.50.
    """

    name: str = "agentline_get_balance"
    description: str = (
        "Check your AgentLine account balance. "
        "Calls cost $0.10/min. You need at least $0.50 to make calls. "
        "Use this before making calls to verify you have enough credit."
    )
    api_key: Optional[str] = Field(default=None, exclude=True)

    def _run(self, run_manager=None) -> str:
        result = _make_request("GET", "/billing/balance", api_key=self.api_key)
        return json.dumps(result, indent=2, default=str)
