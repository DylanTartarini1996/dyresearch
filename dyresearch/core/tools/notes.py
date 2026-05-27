import asyncio

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools import BaseTool, FunctionTool
from typing import List, Optional

from .note_taking import (
    create_obsidian_note, 
    delete_obsidian_note,
    list_obsidian_notes,
    read_obsidian_note,
    update_obsidian_note, 
)
from ..utils.logger import get_logger


logger = get_logger(__name__)


class NoteTakingToolset(BaseToolset):

    def __init__(self, tool_name_prefix: str = "notes"):
        self.tool_name_prefix = tool_name_prefix
        self._create_tool = FunctionTool(func=create_obsidian_note)
        self._update_tool = FunctionTool(func=update_obsidian_note)
        self._delete_tool = FunctionTool(func=delete_obsidian_note)
        self._list_tool = FunctionTool(func=list_obsidian_notes)
        self._read_tool = FunctionTool(func=read_obsidian_note)


    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        logger.debug(f"NoteTakingToolset.get_tools() called.")
        tools_to_return = [
            self._create_tool, 
            self._delete_tool, 
            self._list_tool, 
            self._read_tool,
            self._update_tool
        ]
        logger.debug(f"NoteTakingToolset providing tools: {[t.name for t in tools_to_return]}")
        return tools_to_return


    async def close(self) -> None:
        logger.info(f"NoteTakingToolset.close() called.")
        await asyncio.sleep(0)  # Placeholder for async cleanup if needed
