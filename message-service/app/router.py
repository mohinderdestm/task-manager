from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import manager
from app.database import message_collection, group_collection
from datetime import datetime
from app.models import Group
from fastapi import Header, HTTPException, Depends

router = APIRouter()

def get_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    return authorization.split(" ")[1]

# 🔌 WebSocket Endpoint
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):

    user_id = user_id.lower()  # ✅ normalize
    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()

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

                print(f"🔍 Group '{group_id}' members: {group['members']}")
                print(f"🔍 Active connections: {list(manager.active_connections.keys())}")

                # Send to sender
                await manager.send_personal_message(
                    f"[{group_id}] You: {message}",
                    user_id
                )

                # Send to others
                for member in group["members"]:
                    member = member.lower()

                    if member != user_id and member in manager.active_connections:
                        await manager.send_personal_message(
                            f"[{group_id}] {user_id}: {message}",
                            member
                        )

                await message_collection.insert_one({
                    "sender": user_id,
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
                    "receiver": receiver_id,
                    "content": message,
                    "type": "direct",
                    "timestamp": datetime.utcnow()
                })

                await manager.send_personal_message(
                    f"{user_id}: {message}",
                    receiver_id
                )

                await manager.send_personal_message(
                    f"You: {message}",
                    user_id
                )

    except WebSocketDisconnect:
        manager.disconnect(user_id)

# ✅ CREATE GROUP (NAME ONLY)
@router.post("/create-group")
async def create_group(group: Group, token: str = Depends(get_token)):

    members_names = []

    for name in group.members:
        if not name:
            raise HTTPException(status_code=400, detail="Invalid user name")

        members_names.append(name.lower())

    print("FINAL MEMBERS:", members_names)

    await group_collection.insert_one({
        "group_id": group.group_id.lower(),
        "members": members_names,
        "timestamp": datetime.utcnow()
    })

    return {"message": "Group created successfully"}

# ✅ GET USER CONVERSATIONS (SIDEBAR)
@router.get("/conversations/{user_id}")
async def get_conversations(user_id: str):

    user_id = user_id.lower()

    # DIRECT CHATS
    sent_to = await message_collection.distinct(
        "receiver",
        {"sender": user_id, "type": "direct"}
    )

    received_from = await message_collection.distinct(
        "sender",
        {"receiver": user_id, "type": "direct"}
    )

    direct_users = list(set(sent_to + received_from))

    # GROUPS
    groups = await group_collection.find(
        {"members": user_id}
    ).to_list(None)

    group_ids = [g["group_id"] for g in groups]

    return {
        "direct": direct_users,
        "groups": group_ids
    }

# ✅ GET OLD MESSAGES
@router.get("/messages/{chat_type}/{chat_id}/{user_id}")
async def get_messages(chat_type: str, chat_id: str, user_id: str):

    chat_id = chat_id.lower()
    user_id = user_id.lower()

    if chat_type == "direct":

        messages = await message_collection.find({
            "type": "direct",
            "$or": [
                {"sender": user_id, "receiver": chat_id},
                {"sender": chat_id, "receiver": user_id}
            ]
        }).sort("timestamp", 1).to_list(None)

    else:  # group

        messages = await message_collection.find({
            "type": "group",
            "receiver": chat_id
        }).sort("timestamp", 1).to_list(None)

    # clean response
    return [
        {
            "sender": msg["sender"],
            "message": msg["content"]
        }
        for msg in messages
    ]

