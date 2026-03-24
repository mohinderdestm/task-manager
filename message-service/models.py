from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    SYSTEM = "system"
    FILE = "file"


class ConversationType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"

# Models for MongoDB documents
class MessageDocument(BaseModel):
    conversation_id: str
    sender_id: str
    sender_name: str = ""        
    receiver_id: Optional[str] = None
    receiver_name: Optional[str] = None   
    content: str
    message_type: MessageType = MessageType.TEXT
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ConversationDocument(BaseModel):
    conversation_type: ConversationType
    name: Optional[str] = None
    created_by: str
    members: List[str]= []
    member_names: List[str] = []
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Models for API requests/responses
class CreateDirectConversation(BaseModel):
    target_user_id: str
    target_user_name: str


class CreateGroupConversation(BaseModel):
    name: str
    member_ids: List[str]
    member_names: List[str]

class AddMemberRequest(BaseModel):
    user_id: str
    user_name: str

class SendMessageRequest(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT

class MarkReadRequest(BaseModel):
    conversation_id: str


# Models for WebSocket communication
class WSIncoming(BaseModel):
    type : str
    conversation_id: str
    content: Optional[str] = None

class WSOutgoing(BaseModel):
    type: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    content: Optional[str] = None
    created_at: Optional[datetime] = None
    extra: Optional[dict] = None