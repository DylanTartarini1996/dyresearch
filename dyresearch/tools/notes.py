import asyncio

from typing import List, Optional
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools import BaseTool, FunctionTool

from .note_taking import create_obsidian_note, append_to_obsidian_note
from ..utils.logger import get_logger


logger = get_logger(__name__)


class NoteTakingToolset(BaseToolset):

    def __init__(self, tool_name_prefix: str = "notes"):
        self.tool_name_prefix = tool_name_prefix
        self._create_tool = FunctionTool(func=create_obsidian_note)
        self._append_tool = FunctionTool(func=append_to_obsidian_note)
        # self._check_existence_tool = FunctionTool(func=check_existing_notes, name=f"check_other_notes")

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        logger.info(f"NoteTakingToolset.get_tools() called.")
        tools_to_return = [self._create_tool, self._append_tool]
        logger.info(f"NoteTakingToolset providing tools: {[t.name for t in tools_to_return]}")
        return tools_to_return


    async def close(self) -> None:
        logger.info(f"NoteTakingToolset.close() called.")
        await asyncio.sleep(0)  # Placeholder for async cleanup if needed
