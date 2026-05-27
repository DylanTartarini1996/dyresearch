from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_id: str = "dyresearch_user"
    session_id: str = "default_session"
    invocation_id: Optional[str] = None