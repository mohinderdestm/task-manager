from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
from bson import ObjectId

from app.db import message_collection, conversation_collection
from app.jwt_auth import verify_token

router = APIRouter()
connections = {}

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    token = websocket.query_params.get("token")
    user_data = verify_token(token)

    if not user_data:
        await websocket.close()
        return

    user_name = user_data.get("name") or user_data.get("email")
    user_email = user_data["email"]

    convo = await conversation_collection.find_one({
        "_id": ObjectId(conversation_id)
    })

    if not convo or user_email not in convo["participants"]:
        await websocket.close()
        return

    if conversation_id not in connections:
        connections[conversation_id] = []

    connections[conversation_id].append(websocket)

    print("CONNECTED:", user_email, "→", conversation_id)
    print("TOTAL CONNECTIONS:", len(connections[conversation_id]))

    try:
        while True:
            text = await websocket.receive_text()

            msg = {
                "conversation_id": conversation_id,
                "sender": user_name,
                "text": text,
                "created_at": datetime.utcnow()
            }

            await message_collection.insert_one(msg)

            for conn in connections[conversation_id]:
                await conn.send_text(f"{user_name}: {text}")

    except WebSocketDisconnect:
        if websocket in connections[conversation_id]:
            connections[conversation_id].remove(websocket)