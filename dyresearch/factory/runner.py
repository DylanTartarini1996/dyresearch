import os

from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService

from dyresearch.agent import root_agent


def get_session_service():
    default_db = "sqlite+aiosqlite:///./adk_history.db"
    db_url = os.getenv("SESSION_SERVICE_URI", default_db)
    
    return DatabaseSessionService(db_url)

def create_runner():
    return Runner(
        app_name="DyResearch",
        agent=root_agent,
        session_service=get_session_service()
    )

# Singleton instance for the app to use
runner = create_runner()