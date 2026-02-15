import os 
import datetime

from google.adk.tools.tool_context import ToolContext

# from ...agents.librarian import librarian_agent
from ...utils.logger import get_logger

logger = get_logger(__name__)


def create_obsidian_note(
        title: str, 
        content: str, 
        tool_context: ToolContext,
        folder: str = "Study Notes", 
        tags: list[str] = None
    ) -> str:
    """
    Creates a beautifully formatted markdown note in the Obsidian Vault with YAML frontmatter.
    Args:
        title: The title of the concept (used for the filename).
        content: The core markdown content (headers, bullets, mermaid graphs).
        folder: The subfolder in the vault to save it to.
    """
    # 1. Sanitize the filename to prevent OS errors
    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    full_dir = os.path.join(tool_context.state.get("vault_path"), folder)
    os.makedirs(full_dir, exist_ok=True)
    
    file_path = os.path.join(full_dir, f"{clean_title}.md")
    
    # 2. Build Obsidian-native YAML Frontmatter
    tag_string = f"[{', '.join(tags)}]" if tags else "[]"
    today = datetime.date.today().isoformat()
    
    frontmatter = (
        "---\n"
        f"aliases: [{clean_title}]\n"
        f"tags: {tag_string}\n"
        f"date_created: {today}\n"
        "---\n\n"
    )
    
    # 3. Write to Vault
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter + content)
        logger.info(f"✅ Success: Note '{clean_title}' saved to Obsidian in '{folder}'.")
        return f"Success: Note '{clean_title}' saved to Obsidian in '{folder}'."
    except Exception as e:
        return f"Error saving note: {str(e)}"


def append_to_obsidian_note(
        title: str, 
        content_to_append: str, 
        tool_context: ToolContext, 
        folder: str = "Study Notes"
    ) -> str:
    """
    Adds new information to the bottom of an existing Obsidian note.
    """
    
    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    file_path = os.path.join(tool_context.state.get("vault_path"), folder, f"{clean_title}.md")
    
    timestamp = datetime.datetime.now().strftime("%H:%M")
    update_block = f"\n\n### Update ({timestamp})\n{content_to_append}"

    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(update_block)
        logger.info(f"✅ Success: Appended new info to '{clean_title}.md'.")
        return f"Success: Appended new info to '{clean_title}.md'."
    except FileNotFoundError:
        return f"Note '{clean_title}' does not exist yet. Please create it first."
    

# def check_for_existing_notes(concepts: list[str]) -> str:
#     """
#     Checks the Vector Store index for existing note titles that match these concepts.
#     Returns a list of titles to use for [[Backlinking]].
#     """
#     # This calls your Librarian's vector store index
#     matches = []
#     for concept in concepts:
#         # Use the Librarian's search logic here
#         existing = librarian_agent.tools['recall_book_concept'](query=concept) 
#         if "Source:" in existing:
#             # Extract the title from the metadata
#             title = existing.split("Source:")[1].split("]")[0].strip()
#             matches.append(title)
            
#     return f"Existing notes found for linking: {', '.join(matches)}"