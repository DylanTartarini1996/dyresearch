import os

from google.adk.agents.callback_context import CallbackContext

from ..factory.database import initialize_database

async def initialize_study_state(callback_context: CallbackContext) -> None:
    """Injects environment variables into the state before the agent runs."""
    # Ensure variables are only set if they don't exist yet

    await initialize_database()

    if "vault_path" not in callback_context.state:
        callback_context.state["vault_path"] = os.getenv("OBSIDIAN_VAULT_PATH", "obsidian")
    
    # You can also inject other useful defaults here
    callback_context.state["user_name"] = os.getenv("USER_NAME", "Student")