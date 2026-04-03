from fastapi import APIRouter, WebSocket, WebSocketDisconnect,Request
from app.websocket_manager import manager
from app.database import message_collection, group_collection
from datetime import datetime
from app.models import Group
from fastapi import HTTPException, Depends
from app.auth import get_current_user
import jwt
import os
from dotenv import load_dotenv
import httpx


load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

router = APIRouter()

# WebSocket Endpoint (SECURE)
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        name = payload.get("name") 

        if not user_id:
            await websocket.close(code=1008)
            return

        user_id = user_id.lower()

    except Exception as e:
        print("JWT ERROR:", e)
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()

            # 🖼️ IMAGE DETECTION (new)
            if "🖼️" in data:
                pass 
            
            # GROUP MESSAGE
            if data.startswith("group:"):
                try:
                    _, group_id, message = data.split(":", 2)
                except ValueError:
                    await websocket.send_text("Invalid group format")
                    continue

                group_id = group_id.lower()

                group = await group_collection.find_one({"group_id": group_id})
                if not group:
                    await websocket.send_text("Group not found")
                    continue

                # Sender gets "You:"
                await manager.send_personal_message(f"You: {message}", user_id)

                # Others get "Name:"
                for member in group["members"]:
                    member = member.lower()
                    if member != user_id and member in manager.active_connections:
                        await manager.send_personal_message(f"{name}: {message}", member)

                await message_collection.insert_one({
                    "sender": user_id,
                    "sender_name": name,
                    "receiver": group_id,
                    "content": message,
                    "type": "group",
                    "timestamp": datetime.utcnow()
                })

            # PERSONAL MESSAGE
            else:
                if ":" not in data:
                    await websocket.send_text("Invalid format")
                    continue

                receiver_id, message = data.split(":", 1)
                receiver_id = receiver_id.lower()

                await message_collection.insert_one({
                    "sender": user_id,
                    "sender_name": name,
                    "receiver": receiver_id,
                    "content": message,
                    "type": "direct",
                    "timestamp": datetime.utcnow()
                })

                # Receiver gets "Name:"
                await manager.send_personal_message(f"{name}: {message}", receiver_id)
                
                # Sender gets "You:"
                await manager.send_personal_message(f"You: {message}", user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)



@router.post("/auth/login")
async def proxy_login(request: Request):
    body = await request.json()

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "http://localhost:8000/auth/login",
            json=body
        )

    return res.json()


# CREATE GROUP
@router.post("/create-group")
async def create_group(
    group: Group,
    current_user: dict = Depends(get_current_user)
):
    creator = current_user["user_id"].lower()

    members_names = []

    for name in group.members:
        if not name:
            raise HTTPException(status_code=400, detail="Invalid user name")

        members_names.append(name.lower())

    #  Add creator automatically
    if creator not in members_names:
        members_names.append(creator)

    await group_collection.insert_one({
        "group_id": group.group_id.lower(),
        "members": members_names,
        "timestamp": datetime.utcnow()
    })

    return {"message": "Group created successfully"}


#  GET USER CONVERSATIONS
@router.get("/conversations")
async def get_conversations(
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"].lower()

    sent_to = await message_collection.distinct(
        "receiver",
        {"sender": user_id, "type": "direct"}
    )

    received_from = await message_collection.distinct(
        "sender",
        {"receiver": user_id, "type": "direct"}
    )

    direct_users = list(set(sent_to + received_from))

    groups = await group_collection.find(
        {"members": user_id}
    ).to_list(None)

    group_ids = [g["group_id"] for g in groups]

    return {
        "direct": direct_users,
        "groups": group_ids
    }


# GET OLD MESSAGES
@router.get("/messages/{chat_type}/{chat_id}")
async def get_messages(
    chat_type: str,
    chat_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"].lower()
    chat_id = chat_id.lower()

    if chat_type == "direct":
        messages = await message_collection.find({
            "type": "direct",
            "$or": [
                {"sender": user_id, "receiver": chat_id},
                {"sender": chat_id, "receiver": user_id}
            ]
        }).sort("timestamp", 1).to_list(None)

    else:
        messages = await message_collection.find({
            "type": "group",
            "receiver": chat_id
        }).sort("timestamp", 1).to_list(None)

    return [
        {
            "sender": msg.get("sender_name", msg["sender"]),
            "message": msg["content"]
        }
        for msg in messages
    ]


@router.get("/group/{group_id}")
async def get_group(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await group_collection.find_one({"group_id": group_id.lower()})

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return {
        "group_id": group["group_id"],
        "members": group["members"]
    }