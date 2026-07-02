# langchain-agentline

LangChain integration for [AgentLine](https://agentline.cloud) — give your AI agents real phone numbers to make calls and read SMS messages.

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
    "messages": [{"role": "user", "content": "Call +15551234567 and tell them the meeting is at 3pm"}]
})
```

## Available Tools

| Tool | Description |
|---|---|
| `agentline_make_call` | Make an outbound phone call from an AgentLine agent |
| `agentline_get_calls` | List recent calls and get transcripts |
| `agentline_get_messages` | Read inbound SMS messages |
| `agentline_list_agents` | List your configured agents and their phone numbers |

## Setup

1. Sign up at [agentline.cloud](https://agentline.cloud)
2. Create an agent and provision a phone number
3. Set your API key: `export AGENTLINE_API_KEY=sk_live_...`

## Requirements

- Python >= 3.10
- An AgentLine account with an active agent
