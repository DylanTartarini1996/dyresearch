from typing import Any, Dict

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext

from ..tools.knowledge_base.vector_store import delete_source, ingest_source_chunks, ingest_source_file
from ..utils.logger import get_logger


logger = get_logger(__name__)


async def upload_file_callback(
    tool: BaseTool, 
    args: Dict[str, Any], 
    tool_response: str,
    tool_context: ToolContext
    ):
    """ 
    Programmatic Hook: Automatically uploads a file obtained from the  
    `research_agent` inside the vector store. 
    """
    if tool.name == "research_download_document" and isinstance(tool_response, str) and tool_response.startswith("✅ File successfully downloaded to:"):
        logger.debug(f"Entering Upload File Callback")
        
        try: 
            url = args.get("url", None)
            filename = args.get("filename", None)
            file_path = tool_response.split("✅ File successfully downloaded to:", 1)[1]
            logger.info(f"⬆ Uploading {file_path} from callback..")

            ingestion_msg = await ingest_source_file(
                file_path=file_path, 
                title=filename, 
                source_type="web_download", 
                metadatas={"url": url}
            )
            
            logger.info(ingestion_msg)
        
        except Exception as e:
            logger.warning(str(e))

    
        