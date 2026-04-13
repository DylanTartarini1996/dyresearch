import os

from datetime import datetime
from fastapi import APIRouter, HTTPException
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService

from app.models.request_chat import ChatRequest
from app.models.request_rename_session import RenameSessionRequest
from app.models.response_chat import ChatResponse
from app.models.session_info import SessionInfo
from dyresearch.agent import root_agent
from dyresearch.sessions.memory import rename_adk_session
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
                    is_thought = False
                    
                    # Handle both Dictionary and Object formats
                    if isinstance(part, dict):
                        text_chunk = part.get("text")
                        # Check if this part is flagged as a thought
                        is_thought = part.get("thought", False) 
                    elif hasattr(part, "text"):
                        text_chunk = part.text
                        # LiteLLM/ADK usually sets this attribute on the Part object
                        is_thought = getattr(part, "thought", False)

                    # ONLY append if it's not a thought
                    if text_chunk and not is_thought:
                        final_response.append(text_chunk)
        
        full_text = "".join(final_response).strip()
        
        if not full_text:
            full_text = "*(The agent completed the task but returned no text.)*"

        return ChatResponse(message=full_text)
        
    except Exception as e:
        logger.error(f"❌ Server Error: {e}") # Log to your terminal
        raise HTTPException(status_code=500, detail=str(e))
    

@chat_router.get("/history/{user_id}")
async def get_history(user_id: str, limit: int = 10, offset: int = 0):
    try:
        # This returns a ListSessionsResponse object
        response = await runner.session_service.list_sessions(
            app_name=APP_NAME, 
            user_id=user_id
        )
        
        # Extract the actual list of Session objects
        sessions_list = response.sessions if hasattr(response, "sessions") else []
        
        # Sort by the 'last_update_time' (which is a float/timestamp)
        sorted_sessions = sorted(
            sessions_list, 
            key=lambda s: s.last_update_time,
            reverse=True
        )

        total_sessions = len(sorted_sessions)
        # Brutal pagination here
        paged_sessions = sorted_sessions[offset : offset + limit]

        # Map to your SessionInfo response model
        session_data = [
            SessionInfo(
                session_id=s.id, 
                last_updated=datetime.fromtimestamp(s.last_update_time) if s.last_update_time > 0 else datetime.now()
            ) 
            for s in paged_sessions
        ]

        return {
            "total": total_sessions,
            "limit": limit,
            "offset": offset,
            "sessions": session_data
        }

    except Exception as e:
        logger.error(f"❌ Failed to fetch history: {e}")
        return {"total": 0, "sessions": []}
    

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
                    
                    text_parts = []

                    for p in parts:
                        is_thought = False
                        if isinstance(p, dict):
                            val = getattr(p, 'text', None)
                            is_thought = getattr(p, "thought", False)
                        elif hasattr(p, "text"):
                            val = p.text
                            # LiteLLM/ADK usually sets this attribute on the Part object
                            is_thought = getattr(p, "thought", False)
                        if isinstance(val, str) and not is_thought:
                            text_parts.append(val)
                    
                    full_text = "".join(text_parts).strip()
                    if full_text:
                        messages.append({"role": role, "content": full_text})
        
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages for {session_id}: {e}")
        return []
    

@chat_router.post("/sessions/{old_session_id}/rename")
async def rename_session(old_session_id: str, request: RenameSessionRequest):
        try: 
            await rename_adk_session(
                db_session_service=runner.session_service,
                app_name=APP_NAME, 
                old_session_id=old_session_id,
                user_id=request.user_id,
                new_session_id=request.new_session_id
            )
            return {"status": "success", "new_session_id": request.new_session_id}

        except Exception as e: 
            raise HTTPException(status_code=500, detail="Could not rename session")