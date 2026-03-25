from fastapi import APIRouter, Request
from datetime import datetime
from bson import ObjectId
from app.jwt_auth import  verify_token

from app.db import conversation_collection

router = APIRouter()

@router.post("/create-chat")
async def create_chat(request: Request, data: dict):
    token = request.headers.get("Authorization").split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Unauthorized"}

    user_email = user_data["email"]
    other_user = data["other_user"]

    existing = await conversation_collection.find_one({
        "participants": {
            "$all": [user_email, other_user],
            "$size": 2
        },
        "is_group": {"$ne": True}
    })

    if existing:
        return {"conversation_id": str(existing["_id"])}

    convo = {
        "participants": [user_email, other_user],
        "created_at": datetime.utcnow()
    }

    result = await conversation_collection.insert_one(convo)

    return {"conversation_id": str(result.inserted_id)}


@router.post("/create-group")
async def create_group(request: Request, data: dict):
    auth = request.headers.get("Authorization")
    if not auth:
        return {"error": "Unauthorized"}

    token = auth.split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Invalid token"}

    creator = user_data["email"]

    group_name = data.get("group_name")
    members = data.get("members", [])

    participants = list(set(members + [creator]))

    convo = {
        "participants": participants,
        "is_group": True,
        "group_name": group_name,
        "admin": creator,
        "created_at": datetime.utcnow()
    }

    result = await conversation_collection.insert_one(convo)

    return {"conversation_id": str(result.inserted_id)}


@router.post("/add-to-group/{conversation_id}")
async def add_to_group(conversation_id: str, request: Request, data: dict):
    auth = request.headers.get("Authorization")
    if not auth:
        return {"error": "Unauthorized"}

    token = auth.split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Unauthorized"}

    convo = await conversation_collection.find_one({
        "_id": ObjectId(conversation_id)
    })

    if not convo or not convo.get("is_group"):
        return {"error": "Not a group"}

    if user_data["email"] != convo["admin"]:
        return {"error": "Only admin can add users"}

    new_users = data.get("users", [])

    await conversation_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$addToSet": {"participants": {"$each": new_users}}}
    )

    return {"message": "Users added"}


@router.get("/my-chats")
async def get_my_chats(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        return {"error": "Unauthorized"}

    token = auth.split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Invalid token"}

    user_email = user_data["email"]

    chats = await conversation_collection.find({
        "participants": user_email
    }).to_list(100)

    result = []
    for chat in chats:
        result.append({
            "conversation_id": str(chat["_id"]),
            "is_group": chat.get("is_group", False),
            "group_name": chat.get("group_name"),
            "participants": chat["participants"]
        })

    return result