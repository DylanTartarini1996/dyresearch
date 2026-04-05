import os

from fastapi import APIRouter, HTTPException
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService

from app.models.request_chat import ChatRequest
from app.models.response_chat import ChatResponse
from dyresearch.agent import root_agent
from dyresearch.utils.logger import get_logger

APP_NAME = "DyResearch"

logger = get_logger(__name__)

chat_router = APIRouter(prefix="/chat",tags=["chats"])

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
            # The ADK event is an object. We check if it has a 'content' attribute.
            if hasattr(event, "content") and event.content is not None:
                parts = getattr(event.content, "parts", [])
                
                for part in parts:
                    # Filter for text. If it's a 'function_call' (a tool trace) 
                    # we quietly ignore it and let it run in the background.
                    if hasattr(part, "text") and part.text:
                        final_response.append(part.text)
                        
        # Join all accumulated text chunks and return
        full_text = "".join(final_response).strip()
        
        if not full_text:
            full_text = "*(The agent completed the task but returned no text.)*"

        return ChatResponse(message=full_text)
        
    except Exception as e:
        logger.error(f"❌ Server Error: {e}") # Log to your terminal
        raise HTTPException(status_code=500, detail=str(e))
