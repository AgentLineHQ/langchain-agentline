"""AgentLine Toolkit for LangChain.

Groups all AgentLine tools into a single toolkit that can be
configured with an API key and optionally filtered to a subset of tools.
"""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_agentline.tools import (
    AgentLineCallTool,
    AgentLineGetCallsTool,
    AgentLineGetMessagesTool,
    AgentLineListAgentsTool,
)

ALL_TOOLS: dict[str, type[BaseTool]] = {
    "agentline_make_call": AgentLineCallTool,
    "agentline_get_calls": AgentLineGetCallsTool,
    "agentline_get_messages": AgentLineGetMessagesTool,
    "agentline_list_agents": AgentLineListAgentsTool,
}


class AgentLineToolkit(BaseModel):
    """Collection of AgentLine tools for making calls and reading SMS.

    Set up with your API key and use `get_tools()` to get a list of
    LangChain tools ready for use with any agent.

    Example:

        toolkit = AgentLineToolkit(api_key="sk_live_...")
        tools = toolkit.get_tools()

        # Or select specific tools
        tools = toolkit.get_tools(selected_tools=[
            "agentline_make_call",
            "agentline_get_calls",
        ])
    """

    api_key: Optional[str] = Field(
        default=None,
        description="AgentLine API key. If not set, reads from AGENTLINE_API_KEY env var or ~/.config/agentline/api_key.",
    )

    selected_tools: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional list of tool names to include. If None, all tools are loaded. "
            "Available: agentline_make_call, agentline_get_calls, "
            "agentline_get_messages, agentline_list_agents."
        ),
    )

    def get_tools(self) -> List[BaseTool]:
        """Return the configured AgentLine tools as a list."""
        if self.selected_tools is None:
            tool_names = list(ALL_TOOLS.keys())
        else:
            tool_names = self.selected_tools

        tools = []
        for name in tool_names:
            if name in ALL_TOOLS:
                tools.append(ALL_TOOLS[name](api_key=self.api_key))
        return tools
