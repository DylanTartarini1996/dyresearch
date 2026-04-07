import os 
import datetime

from google.adk.tools.tool_context import ToolContext

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

    -----
    Args:
    -----
    `title`: `str`
        The title of the concept (used for the filename).
    `content`: `str`
        The core markdown content (headers, bullets, mermaid graphs).
    `folder`: `str`
        The subfolder in the vault to save it to.
    """
    # Sanitize the filename to prevent OS errors
    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    full_dir = os.path.join(tool_context.state.get("vault_path"), folder)
    os.makedirs(full_dir, exist_ok=True)
    
    file_path = os.path.join(full_dir, f"{clean_title}.md")
    
    # Build Obsidian-native YAML Frontmatter
    tag_string = f"[{', '.join(tags)}]" if tags else "[]"
    today = datetime.date.today().isoformat()
    
    frontmatter = (
        "---\n"
        f"aliases: [{clean_title}]\n"
        "created_by: dyresearch"
        f"tags: {tag_string}\n"
        f"date_created: {today}\n"
        "---\n\n"
    )
    
    # Write to Vault
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter + content)
        logger.info(f"✅ Success: Note '{clean_title}' saved to Obsidian in '{folder}'.")
        return f"Success: Note '{clean_title}' saved to Obsidian in '{folder}'."
    except Exception as e:
        return f"Error saving note: {str(e)}"
    

def update_obsidian_note(
    title: str, 
    content: str, 
    tool_context: ToolContext, 
    folder: str = "Study Notes",
    mode: str = "append"
    ) -> str:
    """
    Updates an existing Obsidian note. 

    -----
    Args:
    -----
    `title`: `str` 
        The title of the note to update.
    `content`: `str` 
        The new information or the entire new body of the note.
    `mode`: `str` 
        'append' (adds to bottom with timestamp) or 'overwrite' (replaces everything after frontmatter).
    """
    vault_path = tool_context.state.get("vault_path")
    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    file_path = os.path.join(vault_path, folder, f"{clean_title}.md")

    if not os.path.exists(file_path):
        return f"Error: Note '{clean_title}' does not exist in '{folder}'. Use create_obsidian_note first."

    try:
        if mode == "append":
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            update_block = f"\n\n### Update ({timestamp})\n{content}"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(update_block)
            logger.info(f"✅ Success: Appended info to '{clean_title}.md'.")
            return f"Success: Appended new information to '{clean_title}'."

        elif mode == "overwrite":
            # 1. Read existing file to preserve the YAML frontmatter
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 2. Extract frontmatter (everything between the first two '---')
            frontmatter = ""
            if lines and lines[0].strip() == "---":
                end_index = -1
                for i in range(1, len(lines)):
                    if lines[i].strip() == "---":
                        end_index = i
                        break
                if end_index != -1:
                    frontmatter = "".join(lines[:end_index + 1])
            
            # 3. Write frontmatter + the brand new content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(frontmatter + "\n\n" + content)
            
            logger.info(f"✅ Success: Overwrote '{clean_title}.md' while preserving frontmatter.")
            return f"Success: Note '{clean_title}' has been fully updated and reorganized."

    except Exception as e:
        return f"Error updating note: {str(e)}"

def list_obsidian_notes(
    tool_context: ToolContext, 
    folder: str = ""
    ) -> str:
    """
    Lists all Markdown (.md) notes currently in the Obsidian vault.  

    -----
    Args:
    -----
    `folder`: `str` 
        Optional subfolder to search within (e.g., 'AI Research').
    """
    vault_root = tool_context.state.get("vault_path")
    if not vault_root:
        return "Error: 'vault_path' not found in tool context state."

    search_path = os.path.join(vault_root, folder) if folder else vault_root
    
    if not os.path.exists(search_path):
        return f"Error: The path '{search_path}' does not exist."
        
    md_files = []
    # Using os.walk to handle nested folders properly
    for root, dirs, files in os.walk(search_path):
        for file in files:
            if file.endswith(".md"):
                # Get the path relative to the vault root for the agent to use
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, vault_root)
                md_files.append(rel_path)
    
    if not md_files:
        return f"No notes found in '{folder if folder else 'the vault'}'."
        
    formatted_list = [f"- {path}" for path in sorted(md_files)]
    return f"### 📄 Vault Inventory:\n" + "\n".join(formatted_list)


def read_obsidian_note(
    file_path: str, 
    tool_context: ToolContext
    ) -> str:
    """
    Reads the full content of an Obsidian note.  

    -----
    Args:
    -----
    `file_path`: `str` 
        The relative path to the file (e.g., 'Study Notes/Physics.md').
    """
    vault_root = tool_context.state.get("vault_path")
    if not vault_root:
        return "Error: 'vault_path' not found in tool context state."

    full_path = os.path.join(vault_root, file_path)
    
    if not os.path.exists(full_path):
        return f"Error: File '{file_path}' not found. Use list_obsidian_notes to verify the path."
        
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"✅ Success: Read content from '{file_path}'.")
        return f"### 📖 Content of {file_path}:\n\n{content}"
    except Exception as e:
        return f"Error reading note: {str(e)}"
    

def delete_obsidian_note(
    title: str, 
    tool_context: ToolContext, 
    folder: str = "Study Notes"
    ) -> str:
    """
    Permanently deletes a note from the Obsidian vault.  

    -----
    Args:
    -----
    `title`: `str` 
        The title of the note to delete.
    `folder`: `str` 
        The subfolder where the note is located.
    """
    vault_path = tool_context.state.get("vault_path")
    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    file_path = os.path.join(vault_path, folder, f"{clean_title}.md")

    if not os.path.exists(file_path):
        return f"Error: Note '{clean_title}' not found in '{folder}'. Nothing to delete."

    try:
        os.remove(file_path)
        logger.info(f"🗑️ Success: Deleted '{clean_title}.md' from Obsidian.")
        return f"Success: Note '{clean_title}' has been permanently removed from the vault."
    except Exception as e:
        return f"Error deleting note: {str(e)}"