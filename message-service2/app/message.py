from fastapi import APIRouter
from app.db import message_collection

router = APIRouter()

@router.get("/messages/{conversation_id}")
async def get_messages(conversation_id: str):
    data = await message_collection.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", 1).to_list(50)

    for msg in data:
        msg["_id"] = str(msg["_id"])

    return data