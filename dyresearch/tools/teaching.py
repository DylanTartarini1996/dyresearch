import asyncio
from typing import List, Optional

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset

from .knowledge_base.vector_store import search_knowledge_base
from .note_taking.obsidian_tools import (
    get_obsidian_relations, 
    search_obsidian_vault, 
    read_obsidian_note
)
from ..utils.logger import get_logger


logger = get_logger(__name__)    


class TeachingToolset(BaseToolset):

    def __init__(self, tool_name_prefix: str = "teaching"):
        self.tool_name_prefix = tool_name_prefix
        self._search_vault_tool = FunctionTool(func=search_obsidian_vault)
        self._read_note_tool = FunctionTool(func=read_obsidian_note)
        self._search_kb_tool = FunctionTool(func=search_knowledge_base)
        self._get_relations_tool = FunctionTool(func=get_obsidian_relations)


    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        logger.debug(f"TeachingToolset.get_tools() called.")
        tools_to_return = [
            self._search_vault_tool,
            self._read_note_tool,
            self._search_kb_tool, 
            self._get_relations_tool
        ]

        logger.debug(f"TeachingToolset providing tools: {[t.name for t in tools_to_return]}")
        return tools_to_return
    

    async def close(self) -> None:
        logger.info(f"TeachingToolset.close() called.")
        await asyncio.sleep(0)  # Placeholder for async cleanup if needed