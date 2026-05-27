import json

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from google.genai import types

from .. import APP_NAME
from ..models.request_chat import ChatRequest
from ..models.request_rename_session import RenameSessionRequest
from ..models.response_chat import ChatResponse
from ..models.session_info import SessionInfo
from ...core.factory.runner import runner
from ...core.sessions.memory import rename_adk_session, search_session_by_name
from ...core.utils.logger import get_logger


logger = get_logger(__name__)

chat_router = APIRouter(tags=["chats"])

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
    

@chat_router.post("/chat/stream")
async def chat_stream(chat_request: ChatRequest):

    async def event_generator():
        try: 
            # Ensure Session Exists (Same as before)
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

            new_msg = types.Content(
                role="user", 
                parts=[types.Part(text=chat_request.message)]
            )

            # Iterate through the async stream
            async for event in runner.run_async(
                user_id=chat_request.user_id,
                session_id=chat_request.session_id,
                invocation_id=chat_request.invocation_id,
                new_message=new_msg
            ):
                author = getattr(event, "author", "")
                if author == "user":
                    continue

                # --- Check for Agent Transfers ---
                actions = getattr(event, "actions", {})
                if actions:
                    transfer_agent = actions.get("transfer_to_agent") if isinstance(actions, dict) else getattr(actions, "transfer_to_agent", None)
                    if transfer_agent:
                        payload = {"type": "system", "content": f"🔄 Transferring to {transfer_agent}..."}
                        yield f"data: {json.dumps(payload)}\n\n"

                # --- Check Content Parts ---
                content = getattr(event, "content", None)
                if content:
                    parts = getattr(content, "parts", [])
                    
                    for part in parts:
                        text_chunk = None
                        is_thought = False
                        
                        # Handle Dictionary format
                        if isinstance(part, dict):
                            # Catch Function Calls
                            if "function_call" in part:
                                tool_name = part["function_call"].get("name", "unknown_tool")
                                payload = {"type": "system", "content": f"🛠️ Using tool: {tool_name}..."}
                                yield f"data: {json.dumps(payload)}\n\n"
                                
                            text_chunk = part.get("text")
                            is_thought = part.get("thought", False) 
                        
                        # Handle Object format
                        else:
                            # Catch Function Calls
                            function_call = getattr(part, "function_call", None)
                            if function_call:
                                tool_name = getattr(function_call, "name", "unknown_tool")
                                payload = {"type": "system", "content": f"🛠️ Using tool: {tool_name}..."}
                                yield f"data: {json.dumps(payload)}\n\n"

                            text_chunk = getattr(part, "text", None)
                            is_thought = getattr(part, "thought", False)

                        # YIELD Text or Thoughts
                        if text_chunk:
                            payload = {
                                "type": "thinking" if is_thought else "answer",
                                "content": text_chunk
                            }
                            yield f"data: {json.dumps(payload)}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Server Error during stream: {e}")
            # Yield the error to the frontend so the UI doesn't hang indefinitely
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    # 4. Return the StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@chat_router.get("/history/{user_id}")
async def get_history(user_id: str, limit: int = 10, offset: int = 0):
    try:
        response = await runner.session_service.list_sessions(
            app_name=APP_NAME, 
            user_id=user_id
        )
        sessions_list = response.sessions if hasattr(response, "sessions") else []

        sorted_sessions = sorted(
            sessions_list, 
            key=lambda s: s.last_update_time,
            reverse=True
        )

        total_sessions = len(sorted_sessions)
    
        paged_sessions = sorted_sessions[offset : offset + limit]

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
    

@chat_router.get("/sessions/search")
async def search_sessions(
    user_id: str,
    q: str = Query(..., description="The session name or ID to search for"),
    fuzzy: bool = Query(False, description="Enable fuzzy matching")
):
    """Searches for sessions by name, with optional fuzzy matching."""
    try:
        results = await search_session_by_name(
            db_session_service=runner.session_service,
            search_id=q,
            app_name=APP_NAME,
            user_id=user_id,
            fuzzy_match=fuzzy
        )
        
        session_data = []
        for s in results:
            if s:
                last_updated = datetime.fromtimestamp(s.last_update_time) if hasattr(s, "last_update_time") and s.last_update_time > 0 else datetime.now()
                session_data.append(SessionInfo(
                    session_id=s.id, 
                    last_updated=last_updated
                ))
                
        return {
            "status": "success",
            "total": len(session_data),
            "sessions": session_data
        }

    except NotImplementedError as e:
        logger.warning(f"Fuzzy search not implemented for this dialect: {e}")
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Failed to search sessions: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during search.")
    

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
    

@chat_router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, user_id: str):
    try:
        await runner.session_service.delete_session(
            app_name=APP_NAME,
            session_id=session_id,
            user_id=user_id
        )
        return {"status": "success", "message": f"Session {session_id} deleted."}
    except Exception as e:
        logger.error(f"❌ Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail="Delete failed")
