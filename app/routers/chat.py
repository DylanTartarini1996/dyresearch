import os

from datetime import datetime
from fastapi import APIRouter, HTTPException
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from typing import List

from app.models.request_chat import ChatRequest
from app.models.response_chat import ChatResponse
from app.models.session_info import SessionInfo
from dyresearch.agent import root_agent
from dyresearch.utils.logger import get_logger

APP_NAME = "DyResearch"

logger = get_logger(__name__)

chat_router = APIRouter(tags=["chats"])

db_url =os.getenv("SESSION_SERVICE_URI", "postgresql+asyncpg://adk_user:adk_password@localhost:5432/adk_history")
session_service = DatabaseSessionService(db_url)

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service
)

@chat_router.post("/chat")
async def chat(chat_request: ChatRequest) -> ChatResponse:

    try: 
        # Ensure Session Exists
        session = await runner.session_service.get_session(
            app_name=APP_NAME, 
            user_id=chat_request.user_id, 
            session_id=chat_request.session_id
        )
        if session is not None: 
            logger.info(f"Existing session found: {chat_request.session_id}")
        else:
            logger.info(f"Creating new session: {chat_request.session_id}")
            await runner.session_service.create_session(
                app_name=APP_NAME, 
                user_id=chat_request.user_id, 
                session_id=chat_request.session_id
            )

        final_response = []

        new_msg = types.Content(
            role="user", 
            parts=[types.Part(text=chat_request.message)]
        )

        async for event in runner.run_async(
            user_id=chat_request.user_id,
            session_id=chat_request.session_id,
            invocation_id=chat_request.invocation_id, #NOTE defaults to none
            new_message=new_msg
            ):

            author = getattr(event, "author", "")
            if author == "user":
                continue

            if hasattr(event, "content") and event.content:
                # Safely get the parts array
                parts = getattr(event.content, "parts", [])
                
                for part in parts:
                    text_chunk = None
                    
                    # THE FIX: Handle both Dictionary and Object formats
                    if isinstance(part, dict):
                        text_chunk = part.get("text")
                    elif hasattr(part, "text"):
                        text_chunk = part.text

                    if text_chunk:
                        final_response.append(text_chunk)
        
        full_text = "".join(final_response).strip()
        
        if not full_text:
            full_text = "*(The agent completed the task but returned no text.)*"

        return ChatResponse(message=full_text)
        
    except Exception as e:
        logger.error(f"❌ Server Error: {e}") # Log to your terminal
        raise HTTPException(status_code=500, detail=str(e))
    

@chat_router.get("/history/{user_id}", response_model=List[SessionInfo])
async def get_history(user_id: str):
    try:
        # 1. This returns a ListSessionsResponse object
        response = await runner.session_service.list_sessions(
            app_name=APP_NAME, 
            user_id=user_id
        )
        
        # 2. Extract the actual list of Session objects
        sessions_list = response.sessions if hasattr(response, "sessions") else []
        
        # 3. Sort by the 'last_update_time' (which is a float/timestamp)
        sorted_sessions = sorted(
            sessions_list, 
            key=lambda s: s.last_update_time, 
            reverse=True
        )
        
        # 4. Map to your SessionInfo response model
        return [
            SessionInfo(
                session_id=s.id, 
                # Convert float timestamp to datetime object for the Pydantic model
                last_updated=datetime.fromtimestamp(s.last_update_time) if s.last_update_time > 0 else datetime.now()
            ) 
            for s in sorted_sessions
        ]

    except Exception as e:
        logger.error(f"❌ Failed to fetch history: {e}")
        return []
    

@chat_router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    try:
        session = await runner.session_service.get_session(
            app_name=APP_NAME,
            session_id=session_id,
            user_id="dyresearch_plugin_user"
        )
        
        messages = []
        if session and hasattr(session, 'events'):
            for event in session.events:
                if hasattr(event, 'content') and event.content:
                    role = "👤 You" if event.author == "user" else "🤖 AI"
                    parts = getattr(event.content, "parts", [])
                    
                    # THE FIX: Only join parts that actually contain a string
                    text_parts = []
                    for p in parts:
                        val = getattr(p, 'text', None)
                        if isinstance(val, str):
                            text_parts.append(val)
                    
                    full_text = "".join(text_parts).strip()
                    if full_text:
                        messages.append({"role": role, "content": full_text})
        
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages for {session_id}: {e}")
        return []