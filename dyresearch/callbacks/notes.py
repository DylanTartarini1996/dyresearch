from typing import Any, Dict

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext

from ..tools.knowledge_base.vector_store import delete_source, ingest_source
from ..utils.logger import get_logger


logger = get_logger(__name__)


async def internal_sync_obsidian_note(title: str, content: str, folder: str):
    """
    Syncs an Obsidian note to the library. 
    1. Deletes old chunks with the same title (to allow updates).
    2. Chunks the new content.
    3. Calls the existing ingest_source function.
    """
    # Clean up old version of this note to prevent duplicates
    await delete_source(title=title)

    chunk_size = 2000
    overlap = 200
    content_chunks = [
        content[i : i + chunk_size] 
        for i in range(0, len(content), chunk_size - overlap)
    ]

    # 3. Use your existing ingestion logic
    result = await ingest_source(
        content_chunks=content_chunks,
        subject=folder if folder else "Notes",
        title=title,
        source_type="obsidian_note",
        authors="note_taking_agent"
    )
    
    return result


async def sync_note_to_library_callback(
        tool: BaseTool, 
        args: Dict[str, Any], 
        tool_response: str,
        tool_context: ToolContext 
    ):
    """
    Programmatic hook: Automatically indexes notes after the 
    `note_taking_agent` finishes writing them, or automatically deletes a note's chunks 
    from vector store if the agent deleted said note. 
    """

    # Check if the tool executed was note creation or appending
    if tool.name in ["notes_create_obsidian_note", "notes_update_obsidian_note"]:    
        # Extract arguments from the trace structure you provided
        title = args.get("title")
        content = args.get("content")
        folder = args.get("folder", "General") # NOTE this should be mapped into metadata from KnowledgeChunk
        # Skip if the tool reported an error
        if isinstance(tool_response, str) and tool_response.startswith("❌"):
            logger.warning(f"⚠️ Sync skipped: Tool reported failure for {title}")
            return
        # Perform the background ingestion
        logger.info(f"🔄 [System Hook] Automatically indexing '{title}' into '{folder}'...")
        try:
            status = await internal_sync_obsidian_note(
                title=title, 
                content=content, 
                folder=folder
            )
            logger.info(f"✅ {status}")
        except Exception as e:
            logger.error(f"❌ Auto-ingestion failed for {title}: {e}")

    elif tool.name == "notes_delete_obsidian_note":
        if "Success" in str(tool_response):
            title = args.get("title")
            logger.info(f"🗑️ [System Hook] Purging '{title}' from Vector Store...")
            await delete_source(title=title)
        return