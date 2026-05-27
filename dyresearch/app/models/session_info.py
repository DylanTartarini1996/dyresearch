from typing import Optional

from pydantic import BaseModel
from datetime import datetime

class SessionInfo(BaseModel):
    session_id: str
    last_updated: Optional[datetime] = None