from pydantic import BaseModel

class RenameSessionRequest(BaseModel):
    new_session_id: str
    user_id: str