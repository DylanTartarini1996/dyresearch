import os
import re
import yaml

from langchain_text_splitters import MarkdownTextSplitter
from pathlib import Path
from typing import Any, Dict

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext

from ..tools.knowledge_base.vector_store import delete_source, ingest_source_chunks
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

    text_splitter = MarkdownTextSplitter(chunk_size=5000, chunk_overlap=200)
    content_chunks = text_splitter.split_text(content)

    # Use the existing ingestion logic
    result = await ingest_source_chunks(
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

    if tool.name in ["notes_create_obsidian_note", "notes_update_obsidian_note"]:    
        title = args.get("title")
        content = args.get("content")
        folder = args.get("folder", "General")
        if isinstance(tool_response, str) and tool_response.startswith("❌"):
            logger.warning(f"⚠️ Sync skipped: Tool reported failure for {title}")
            return
        
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
    

async def discover_and_apply_links_callback(
    tool: BaseTool, 
    args: Dict[str, Any], 
    tool_response: str,
    tool_context: ToolContext
    ):
    """ 
    Programmatic Hook: will scan the vault after a new note has been created and decide whether [[Wikilinks]] 
    should be created between the note and old notes.  
    
    This will be visible in the Obsidian Graphview.  
    """
    if tool.name not in ["notes_create_obsidian_note", "notes_update_obsidian_note"]:
        return
    
    if "vault_path" not in tool_context.state:
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "obsidian")
    else:
        vault_path = tool_context.state['vault_path']

    # Validation & Safety
    title = args.get("title")
    original_note_text = args.get("content")
    folder = args.get("folder", "General")


    if isinstance(tool_response, str) and tool_response.startswith("❌"):
        logger.warning(f"⚠️ Link discovery skipped: Tool reported failure for {title}")
        return

    # Construct full system path to the note
    file_extension = ".md" if not title.endswith(".md") else ""
    full_target_path = Path(vault_path) / folder / f"{title}{file_extension}"

    # 2. Build the Index (Targets)
    link_map = {}
    
    for root, _, files in os.walk(vault_path):
        for filename in files:
            if filename.endswith(".md"):
                file_p = Path(root) / filename
                clean_name = file_p.stem
                link_map[clean_name.lower()] = clean_name
                
                # Check for aliases in YAML without overwriting original_note_text
                try:
                    with open(file_p, 'r', encoding='utf-8') as f:
                        f_text = f.read()
                        if f_text.startswith('---'):
                            # Safely extract frontmatter
                            parts = f_text.split('---')
                            if len(parts) > 2:
                                frontmatter = yaml.safe_load(parts[1])
                                aliases = frontmatter.get('aliases', [])
                                if isinstance(aliases, list):
                                    for alias in aliases:
                                        link_map[alias.lower()] = clean_name
                except Exception:
                    continue

    # Prevent self-linking
    current_title_key = Path(title).stem.lower()
    link_map.pop(current_title_key, None)

    # Apply Links (Regex)
    # Sort by length descending to match "Machine Learning" before "Learning"
    sorted_targets = sorted(link_map.keys(), key=len, reverse=True)
    
    updated_content = original_note_text
    links_found = 0

    for target in sorted_targets:
        # Pattern ensures we don't link inside existing brackets or URLs
        pattern = rf'(?<!\[\[)\b({re.escape(target)})\b(?!\]\])'
        
        def link_replacer(match):
            nonlocal links_found
            links_found += 1
            original_match = match.group(1)
            actual_filename = link_map[target]
            
            if original_match.lower() == actual_filename.lower():
                return f"[[{actual_filename}]]"
            return f"[[{actual_filename}|{original_match}]]"

        updated_content = re.sub(pattern, link_replacer, updated_content, flags=re.IGNORECASE)

    # Silent Save
    if updated_content != original_note_text:
        try:
            full_target_path.write_text(updated_content, encoding="utf-8")
            logger.info(f"✅ Auto-linked {links_found} terms in '{title}'")
        except Exception as e:
            logger.error(f"❌ Failed to write auto-links to {full_target_path}: {e}")