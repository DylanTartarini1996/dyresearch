from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.schemas.v1 import StorageEvent, StorageSession
from google.adk.sessions.session import Session
from rapidfuzz import fuzz
from sqlalchemy import update, text, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

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
        
       # Update the 'events' table directly via SQL
        async with get_db_context(db_config) as db_session:
            
            update_stmt = (
                update(StorageEvent)
                .where(
                    StorageEvent.session_id == old_session_id,  # Referencing the Model columns
                    StorageEvent.user_id == user_id,
                    StorageEvent.app_name == app_name
                )
                .values(
                    session_id=new_session_id
                )
            )

            await db_session.execute(update_stmt)
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
    

def get_db_engine_type(db_session: AsyncSession) -> str:
    """Determines if the connected engine is PostgreSQL or otherwise."""
    return str(db_session.bind.dialect.name).lower()


async def _fuzzy_search_postgres(db_session, search_term: str) -> List:
    """Implementation optimized for PostgreSQL using native pg_trgm."""
    # Replaced StorageSession.id with the actual DB column name, assuming 'id'
    stmt = select(StorageSession).where(
        text("similarity(id, :search_term) > :threshold")
    ).order_by(
        text("similarity(id, :search_term) DESC")
    ).limit(5)

    result = await db_session.execute(
        stmt, 
        {"search_term": search_term, "threshold": 0.3} 
    )
    return result.scalars().all()


async def _fuzzy_search_sqlite(db_session, search_term: str) -> List:
    """Fallback implementation for SQLite using RapidFuzz."""
    logger.warning("⚠️ Using slow, in-memory Python fuzzy matching for SQLite. ---")
    
    stmt = select(StorageSession).limit(1000) 
    result = await db_session.execute(stmt)
    all_sessions = result.scalars().all()

    matches = []
    for session in all_sessions:
        # Rapidfuzz ratio returns 0-100
        score = fuzz.ratio(session.id, search_term)
        if score > 30:  # Rough equivalent to the 0.3 pg_trgm threshold
            matches.append((score, session))
            
    matches.sort(key=lambda x: x[0], reverse=True)
    return [session for score, session in matches[:5]] # Matched limit to Postgres


async def fuzzy_search_session(db_session: AsyncSession, search_term: str) -> List[StorageSession]:
    """
    Universal wrapper function to handle fuzzy searching based on the DB engine.
    """
    db_type = get_db_engine_type(db_session)
    if 'postgres' in db_type:
        return await _fuzzy_search_postgres(db_session, search_term)
    elif 'sqlite' in db_type:
        return await _fuzzy_search_sqlite(db_session, search_term)
    else:
        raise NotImplementedError(
            f"Fuzzy matching is not implemented for database dialect: {db_type}"
        )    

async def search_session_by_name(
    db_session_service: DatabaseSessionService, 
    search_id: str, 
    app_name: str, 
    user_id: str, 
    fuzzy_match: bool = False
    ) -> List[Session]:
    """ 
    Returns a session with a given id. 
    If `fuzzy_match` is set to `True`, will search for similar ids
    """
    if not fuzzy_match:
        session = await db_session_service.get_session(
            app_name=app_name, 
            user_id=user_id, 
            session_id=search_id
        )

        return [session] if session else []

    async with get_db_context(db_config) as db_session:
        storage_sessions = await fuzzy_search_session(db_session, search_id)

        sessions = []
        for s in storage_sessions:
            sessions.append(s.to_session())

        return sessions
