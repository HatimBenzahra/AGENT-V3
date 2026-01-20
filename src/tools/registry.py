from typing import Dict, List

from src.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found")
        return self._tools[name]

    def get_all_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_tools_schema(self) -> List[Dict]:
        return [tool.to_dict() for tool in self._tools.values()]
