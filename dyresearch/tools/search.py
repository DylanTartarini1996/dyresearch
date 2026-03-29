import asyncio
from typing import List, Optional

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset

from .research.web_search import perform_web_search, download_document, scrape_website
from ..utils.logger import get_logger


logger = get_logger(__name__)    


class ResearchToolset(BaseToolset):

    def __init__(self, tool_name_prefix: str = "research"):
        self.tool_name_prefix = tool_name_prefix
        self._web_search_tool = FunctionTool(func=perform_web_search)
        self._web_scraping_tool = FunctionTool(func=scrape_website)
        self._download_tool = FunctionTool(func=download_document)


    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        logger.info(f"ResearchToolset.get_tools() called.")
        tools_to_return = [self._web_search_tool, self._web_scraping_tool, self._download_tool]
        logger.info(f"ResearchToolset providing tools: {[t.name for t in tools_to_return]}")
        return tools_to_return
    

    async def close(self) -> None:
        logger.info(f"ResearchToolset.close() called.")
        await asyncio.sleep(0)  # Placeholder for async cleanup if needed