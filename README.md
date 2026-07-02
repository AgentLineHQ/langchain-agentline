# langchain-agentline

LangChain integration for [AgentLine](https://agentline.cloud) — give your AI agents real phone numbers to make calls, read SMS, set up webhooks, and provision numbers.

## Installation

```bash
pip install langchain-agentline
```

## Quick Start

```python
import os
from langchain_agentline import AgentLineToolkit

toolkit = AgentLineToolkit(api_key=os.environ["AGENTLINE_API_KEY"])
tools = toolkit.get_tools()

# Use with any LangChain agent
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

agent = create_react_agent(ChatOpenAI(), tools)
result = agent.invoke({
    "messages": [{"role": "user", "content": "Provision a phone number and call +15551234567"}]
})
```

## Available Tools (12 tools across 5 categories)

| Category | Tool | Description |
|---|---|---|
| **Calls** | `agentline_make_call` | Make outbound voice calls ($0.10/min) |
| | `agentline_get_calls` | List/filter calls by status |
| | `agentline_get_transcript` | Fetch call transcripts |
| | `agentline_hangup_call` | Hang up active calls |
| **SMS** | `agentline_get_messages` | Read inbound SMS messages |
| **Numbers** | `agentline_provision_number` | Buy a phone number ($2 one-time) |
| | `agentline_get_numbers` | List all phone numbers |
| **Webhooks** | `agentline_set_webhook` | Real-time event webhooks |
| | `agentline_list_webhooks` | List configured webhooks |
| | `agentline_delete_webhook` | Remove a webhook |
| **Billing** | `agentline_get_balance` | Check account balance |
| **Agents** | `agentline_list_agents` | List agents and their numbers |

## Setup

1. Sign up at [agentline.cloud](https://agentline.cloud)
2. Create an agent and copy your API key
3. Set your API key: `export AGENTLINE_API_KEY=sk_live_...`

## Requirements

- Python >= 3.10
- An AgentLine account with an active agent
