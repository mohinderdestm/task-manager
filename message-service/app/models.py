from pydantic import BaseModel
from datetime import datetime
from typing import List,Optional

class Message(BaseModel):
    sender: str
    receiver: str
    content: str
    timestamp: datetime = datetime.utcnow()

class Group(BaseModel):
    group_id: str
    members: List[str]
    timestamp: datetime | None = None

    
