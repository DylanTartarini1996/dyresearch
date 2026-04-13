from google.adk.sessions.database_session_service import DatabaseSessionService
from sqlalchemy import select, delete, func, text

from ..factory.database import db_config, get_db_context
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def rename_adk_session(
    db_session_service: DatabaseSessionService, 
    app_name: str, 
    old_session_id: str, 
    user_id: str, 
    new_session_id: str
    ):
    """ Renames a session (and matches the connected events) in Google ADK """
    try:
        # Verify the old session exists (prevents ghost-renaming)
        old_session = await db_session_service.get_session(
            app_name=app_name,
            session_id=old_session_id,
            user_id=user_id
        )
        
        # Create the new session row in the 'sessions' table
        new_session = await db_session_service.create_session(
            app_name=app_name,
            session_id=new_session_id,
            user_id=user_id
        )
        
        
        # 3Update the 'events' table directly via SQL
        # We must do this BEFORE deleting the old session to avoid data loss.
        async with get_db_context(db_config) as db_session:
            update_query = text("""
                UPDATE events 
                SET session_id = :new_session_id 
                WHERE session_id = :old_session_id 
                  AND user_id = :user_id 
                  AND app_name = :app_name
            """)
            
            await db_session.execute(update_query, {
                "new_session_id": new_session_id,
                "old_session_id": old_session_id,
                "user_id": user_id,
                "app_name": app_name
            })
            
            # Commit the update so the foreign keys are successfully transferred
            await db_session.commit()

            logger.info(f"New Session {new_session_id} created")
        
        # Safely delete the old session (its events are already migrated)
        await db_session_service.delete_session(
            app_name=app_name,
            session_id=old_session_id,
            user_id=user_id
        )

        logger.info(f"✅ Session Rename completed!")

    except Exception as e:
        logger.error(f"❌ Failed to rename session and migrate events: {e}")
        raise e