from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from typing import Optional
import json
import logging

from database import messages_collection, conversations_collection
from models import (
    CreateDirectConversation, CreateGroupConversation,
    AddMemberRequest, SendMessageRequest,
    MessageDocument, ConversationDocument,
    MessageType, ConversationType, WSIncoming
)
from dependencies import get_current_user, get_user_from_token_param
from messaging.ws_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)

# helper functions for converting MongoDB documents and fetching conversations
def _ser(doc: dict) -> dict:
    
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# Fetch conversation and check membership 
async def _get_conversation_or_404(conv_id: str) -> dict:
    try:
        conv = await conversations_collection.find_one({"_id": ObjectId(conv_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid conversation id")
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# Direct messages 1-1
@router.post("/conversations/direct", status_code=201)
async def create_direct_conversation(
    body: CreateDirectConversation,
    user: dict = Depends(get_current_user)
):
    
    me = user["user_id"]

    # Prevent duplicate direct conversations
    existing = await conversations_collection.find_one({
        "conversation_type": ConversationType.DIRECT,
        "members": {"$all": [me, body.target_user_id]}
    })
    if existing:
        return {"conversation": _ser(existing), "created": False}

    doc = ConversationDocument(
        conversation_type=ConversationType.DIRECT,
        created_by=me,
        members=[me, body.target_user_id],
        member_names=[user.get("name", me), body.target_user_name],
    )
    result = await conversations_collection.insert_one(doc.dict())
    created = await conversations_collection.find_one({"_id": result.inserted_id})
    return {"conversation": _ser(created), "created": True}

# Group conversations
@router.post("/conversations/group", status_code=201)
async def create_group_conversation(
    body: CreateGroupConversation,
    user: dict = Depends(get_current_user)
):
    
    me = user["user_id"]

    all_members = list(dict.fromkeys([me] + body.member_ids))   # dedupe, keep order
    all_names   = list(dict.fromkeys([user.get("name", me)] + body.member_names))

    doc = ConversationDocument(
        conversation_type=ConversationType.GROUP,
        name=body.name,
        created_by=me,
        members=all_members,
        member_names=all_names,
    )
    result = await conversations_collection.insert_one(doc.dict())
    created = await conversations_collection.find_one({"_id": result.inserted_id})

    payload = {
        "type": "group_created",
        "conversation_id": str(result.inserted_id),
        "name": body.name,
        "created_by": me,
    }
    await manager.broadcast_to_members(all_members, payload, exclude_user_id=me)

    return {"conversation": _ser(created)}

# Conversation management – REST
@router.get("/conversations")
async def list_my_conversations(user: dict = Depends(get_current_user)):
    
    me = user["user_id"]
    cursor = conversations_collection.find({"members": me}).sort("last_message_at", -1)
    convs  = await cursor.to_list(length=100)
    return {"conversations": [_ser(c) for c in convs]}

# Conversation details and membership management
@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    conv = await _get_conversation_or_404(conv_id)
    if user["user_id"] not in conv["members"]:
        raise HTTPException(status_code=403, detail="Not a member")
    return {"conversation": _ser(conv)}

# Adding/removing members (only for group conversations, and only by creator or self-removal)
@router.post("/conversations/{conv_id}/members")
async def add_member(
    conv_id: str,
    body: AddMemberRequest,
    user: dict = Depends(get_current_user)
):
    conv = await _get_conversation_or_404(conv_id)

    if conv["conversation_type"] != ConversationType.GROUP:
        raise HTTPException(status_code=400, detail="Cannot add members to a direct conversation")
    if user["user_id"] not in conv["members"]:
        raise HTTPException(status_code=403, detail="Not a member")
    if body.user_id in conv["members"]:
        raise HTTPException(status_code=409, detail="User already in conversation")

    await conversations_collection.update_one(
        {"_id": ObjectId(conv_id)},
        {"$push": {"members": body.user_id, "member_names": body.user_name}}
    )

    # Notify the new member and current members
    payload = {"type": "member_added", "conversation_id": conv_id,
               "user_id": body.user_id, "user_name": body.user_name}
    await manager.broadcast_to_members(conv["members"] + [body.user_id], payload)

    return {"message": f"{body.user_name} added to group"}

# self-removal or removal by creator
@router.delete("/conversations/{conv_id}/members/{user_id}")
async def remove_member(
    conv_id: str,
    user_id: str,
    user: dict = Depends(get_current_user)
):
    conv = await _get_conversation_or_404(conv_id)
    me = user["user_id"]

    if conv["conversation_type"] != ConversationType.GROUP:
        raise HTTPException(status_code=400, detail="Cannot remove from direct conversation")
    if me not in conv["members"]:
        raise HTTPException(status_code=403, detail="Not a member")
    if me != conv["created_by"] and me != user_id:
        raise HTTPException(status_code=403, detail="Only creator can remove others")

    # Find and remove member + name together by index
    idx = conv["members"].index(user_id)
    conv["members"].pop(idx)
    if idx < len(conv["member_names"]):
        conv["member_names"].pop(idx)

    await conversations_collection.update_one(
        {"_id": ObjectId(conv_id)},
        {"$set": {"members": conv["members"], "member_names": conv["member_names"]}}
    )
    return {"message": "Member removed"}


# Messages via REST and WebSocket
@router.get("/conversations/{conv_id}/messages")
async def get_message_history(
    conv_id: str,
    limit: int = 50,
    before_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    conv = await _get_conversation_or_404(conv_id)
    if user["user_id"] not in conv["members"]:
        raise HTTPException(status_code=403, detail="Not a member")

    query: dict = {"conversation_id": conv_id}
    if before_id:
        try:
            query["_id"] = {"$lt": ObjectId(before_id)}
        except Exception:
            pass

    cursor = messages_collection.find(query).sort("created_at", -1).limit(limit)
    msgs   = await cursor.to_list(length=limit)
    msgs.reverse()  # oldest-first for UI
    return {"messages": [_ser(m) for m in msgs]}


@router.post("/conversations/{conv_id}/messages", status_code=201)
async def send_message_http(
    conv_id: str,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user)
):
    
    conv = await _get_conversation_or_404(conv_id)
    me   = user["user_id"]
    if me not in conv["members"]:
        raise HTTPException(status_code=403, detail="Not a member")
    
    receiver_id = next((m for m in conv["members"] if m != me), None)

    doc = MessageDocument(
        conversation_id=conv_id,
        sender_id=me,
        receiver_id=receiver_id,
        content=body.content,
        message_type=body.message_type,
    )
    result = await messages_collection.insert_one(doc.dict())
    msg_id = str(result.inserted_id)

    # Update conversation last message
    await conversations_collection.update_one(
        {"_id": ObjectId(conv_id)},
        {"$set": {"last_message": body.content, "last_message_at": datetime.utcnow()}}
    )

    # Fan-out via WebSocket
    payload = {
        "type": "message",
        "conversation_id": conv_id,
        "message_id": msg_id,
        "sender_id": me,
        "sender_name": user.get("name", me),
        "content": body.content,
        "message_type": body.message_type,
        "created_at": doc.created_at.isoformat(),
    }
    await manager.broadcast_to_members(conv["members"], payload, exclude_user_id=me)

    return {"message_id": msg_id, "conversation_id": conv_id}

# Message deletion by sender only
@router.delete("/conversations/{conv_id}/messages/{msg_id}")
async def delete_message(
    conv_id: str,
    msg_id: str,
    user: dict = Depends(get_current_user)
):
    try:
        msg = await messages_collection.find_one({"_id": ObjectId(msg_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message id")
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg["sender_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Cannot delete others' messages")

    await messages_collection.delete_one({"_id": ObjectId(msg_id)})
    return {"message": "Deleted"}


# Online user status
@router.get("/online")
async def get_online_users(user: dict = Depends(get_current_user)):
    return {"online_users": manager.online_users()}

# WebSocket endpoint for real-time messaging and presence
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: dict = Depends(get_user_from_token_param)
):
    
    me      = user["user_id"]
    my_name = user.get("name", me)

    await manager.connect(me, websocket)

    # Let all conversations know this user is now online
    my_convs = await conversations_collection.find({"members": me}).to_list(length=200)
    member_ids_across_convs = {uid for c in my_convs for uid in c["members"] if uid != me}
    await manager.broadcast_to_members(
        list(member_ids_across_convs),
        {"type": "user_online", "user_id": me, "user_name": my_name}
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = WSIncoming(**json.loads(raw))
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "detail": "Invalid payload"}))
                continue

            # Typing indicator
            if data.type == "typing":
                conv = await conversations_collection.find_one(
                    {"_id": ObjectId(data.conversation_id), "members": me}
                )
                if conv:
                    await manager.broadcast_to_members(
                        conv["members"],
                        {"type": "typing", "conversation_id": data.conversation_id,
                         "user_id": me, "user_name": my_name},
                        exclude_user_id=me
                    )

            # Read receipt 
            elif data.type == "read":
                await messages_collection.update_many(
                    {"conversation_id": data.conversation_id, "sender_id": {"$ne": me}},
                    {"$set": {"is_read": True}}
                )

            # Chat message 
            elif data.type == "message":
                if not data.content or not data.content.strip():
                    continue

                conv = await conversations_collection.find_one(
                    {"_id": ObjectId(data.conversation_id), "members": me}
                )
                if not conv:
                    await websocket.send_text(json.dumps({
                        "type": "error", "detail": "Conversation not found or not a member"
                    }))
                    continue

                receiver_id = next((m for m in conv["members"] if m != me), None)

                doc = MessageDocument(
                    conversation_id=data.conversation_id,
                    sender_id=me,
                    sender_name=my_name,
                    content=data.content.strip(),
                )
                result = await messages_collection.insert_one(doc.dict())
                msg_id = str(result.inserted_id)

                await conversations_collection.update_one(
                    {"_id": ObjectId(data.conversation_id)},
                    {"$set": {"last_message": data.content.strip(),
                              "last_message_at": datetime.utcnow()}}
                )

                payload = {
                    "type": "message",
                    "conversation_id": data.conversation_id,
                    "message_id": msg_id,
                    "sender_id": me,
                    "sender_name": my_name,
                    "content": data.content.strip(),
                    "message_type": MessageType.TEXT,
                    "created_at": doc.created_at.isoformat(),
                }

                # Echo back to sender + fan-out
                await websocket.send_text(json.dumps({**payload, "is_own": True}))
                await manager.broadcast_to_members(conv["members"], payload, exclude_user_id=me)

    except WebSocketDisconnect:
        manager.disconnect(me)
        await manager.broadcast_to_members(
            list(member_ids_across_convs),
            {"type": "user_offline", "user_id": me, "user_name": my_name}
        )