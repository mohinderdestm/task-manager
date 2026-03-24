from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import manager
from app.database import message_collection, group_collection
from datetime import datetime
from app.models import Group
from fastapi import Header, HTTPException, Depends
import httpx

router = APIRouter()

def get_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    return authorization.split(" ")[1]


# 🔌 WebSocket Endpoint
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
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

                group = await group_collection.find_one({"group_id": group_id})

                if not group:
                    await websocket.send_text("Group not found")
                    continue

                for member in group["members"]:
                    if member == user_id:
                      await manager.send_personal_message(
                          f"[{group_id}] You: {message}",
                          member
                        )
                    else:
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

                await message_collection.insert_one({
                    "sender": user_id,
                    "receiver": receiver_id,
                    "content": message,
                    "type": "direct",
                    "timestamp": datetime.utcnow()
                })

                # send to receiver
                await manager.send_personal_message(
                    f"{user_id}: {message}",
                    receiver_id
                )

                # send to sender
                await manager.send_personal_message(
                    f"You: {message}",
                    user_id
                )

    except WebSocketDisconnect:
        manager.disconnect(user_id)


# Create Group API
@router.post("/create-group")
async def create_group(group: Group, token: str = Depends(get_token)):

    USER_SERVICE_URL = "http://localhost:8001/users"

    async with httpx.AsyncClient() as client:
        for user_id in group.members:

            res = await client.get(
                f"{USER_SERVICE_URL}/public/{user_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            if res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"User {user_id} not valid"
                )

    # SAVE GROUP 
    await group_collection.insert_one({
        "group_id": group.group_id,
        "members": group.members,
        "timestamp": datetime.utcnow()
    })

    return {"message": "Group created successfully"}