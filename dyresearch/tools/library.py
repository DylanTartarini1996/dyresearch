import asyncio
from typing import List, Optional

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset

from .knowledge_base.vector_store import ingest_source, list_available_sources, delete_source, delete_by_subject
from ..utils.logger import get_logger


logger = get_logger(__name__)


class LibrarianToolset(BaseToolset):

    def __init__(self, tool_name_prefix: str = "library"):
        self.tool_name_prefix = tool_name_prefix
        self._ingestion_tool = FunctionTool(func=ingest_source)
        self._list_sources_tool = FunctionTool(func=list_available_sources)
        self._delete_tool = FunctionTool(func=delete_source)
        self._delete_by_subject_tool = FunctionTool(func=delete_by_subject)
        

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        logger.info(f"LibrarianToolset.get_tools() called.")
        tools_to_return = [self._ingestion_tool, self._list_sources_tool, self._delete_tool, self._delete_by_subject_tool]
        logger.info(f"LibrarianToolset providing tools: {[t.name for t in tools_to_return]}")
        return tools_to_return
    

    async def close(self) -> None:
        logger.info(f"LibrarianToolset.close() called.")
        await asyncio.sleep(0)  # Placeholder for async cleanup if needed
