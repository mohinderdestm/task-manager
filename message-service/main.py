import os
import json
import uuid
from bson import ObjectId
from datetime import datetime
from typing import Dict, List
from fastapi import UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request

from db import user_collection, message_collection, conversation_collection
from auth import create_token, verify_token

app = FastAPI()
templates = Jinja2Templates(directory="templates")

connections: Dict[str, List[WebSocket]] = {}


os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/home")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(data: dict):
    user = await user_collection.find_one({"email": data["email"]})
    if user:
        return {"error": "User already exists"}

    await user_collection.insert_one({
        "name": data["name"],
        "email": data["email"],
        "password": data["password"]
    })

    return {"message": "User created"}

@app.post("/login")
async def login(data: dict):
    user = await user_collection.find_one({"email": data["email"]})

    if not user or user["password"] != data["password"]:
        return {"error": "Invalid credentials"}

    token = create_token(user)

    return {"token": token}

@app.post("/create-chat")
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

        if user_email in existing.get("deleted_for", []):
            await conversation_collection.update_one(
                {"_id": existing["_id"]},
                {"$pull": {"deleted_for": user_email}}
            )

        return {"conversation_id": str(existing["_id"])}

    convo = {
        "participants": [user_email, other_user],
        "created_at": datetime.utcnow(),
        "deleted_for": [],
        "cleared_at": {}   # 🔥 ADD THIS
    }

    result = await conversation_collection.insert_one(convo)

    return {"conversation_id": str(result.inserted_id)}


@app.get("/chat/{conversation_id}")
async def chat_page(request: Request, conversation_id: str):
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "conversation_id": conversation_id}
    )


@app.get("/users")
async def get_users(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        return {"error": "Unauthorized"}

    token = auth.split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Invalid token"}

    current_email = user_data["email"]

    users = await user_collection.find(
        {}, {"_id": 0, "name": 1, "email": 1}
    ).to_list(100)

    users = [u for u in users if u["email"] != current_email]

    return users

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):

    # ✅ Validate type
    if not file.content_type.startswith("image/"):
        return {"error": "Only images allowed"}

    content = await file.read()

    # ✅ Validate size (2MB)
    if len(content) > 2 * 1024 * 1024:
        return {"error": "Max 2MB allowed"}

    import uuid
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    filepath = f"uploads/{filename}"

    with open(filepath, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{filename}"}

@app.post("/create-group")
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
        "admins": [creator],
        "created_at": datetime.utcnow()
    }

    result = await conversation_collection.insert_one(convo)

    return {"conversation_id": str(result.inserted_id)}

@app.post("/add-to-group/{conversation_id}")
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

    admins = convo.get("admins", [])

    if user_data["email"] not in (admins or []):
        return {"error": "Only admin can add users"}

    names = data.get("names", [])
    emails = []

    for name in names:
       user = await user_collection.find_one({"name": name})
       if user:
        emails.append(user["email"])

    await conversation_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$addToSet": {"participants": {"$each": emails}}}
    )

    return {"message": "Users added"}


@app.get("/my-chats")
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
        "participants": user_email,
        "deleted_for": {"$ne": user_email}  
    }).sort("last_message_at", -1).to_list(100)

    result = []
    for chat in chats:
        result.append({
            "conversation_id": str(chat["_id"]),
            "is_group": chat.get("is_group", False),
            "group_name": chat.get("group_name"),
            "participants": chat["participants"],
            "admins": chat.get("admins",[]),
            "last_message": chat.get("last_message", "")
        })

    return result

@app.post("/remove-from-group/{conversation_id}")
async def remove_from_group(conversation_id: str, request: Request, data: dict):
    token = request.headers.get("Authorization").split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Unauthorized"}

    convo = await conversation_collection.find_one({
        "_id": ObjectId(conversation_id)
    })

    if not convo or not convo.get("is_group"):
        return {"error": "Not a group"}

    admins = convo.get("admins", [])

    if user_data["email"] not in (admins or []):
        return {"error": "Only admin can promote"}

    email = data.get("email")

    if email in convo.get("admins", []):
        return {"error": "Cannot remove another admin"}

    await conversation_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$pull": {"participants": email}}
    )

    return {"message": "User removed"}

@app.post("/make-admin/{conversation_id}")
async def make_admin(conversation_id: str, request: Request, data: dict):
    token = request.headers.get("Authorization").split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Unauthorized"}

    convo = await conversation_collection.find_one({
        "_id": ObjectId(conversation_id)
    })

    if not convo:
        return {"error": "Not found"}
    
    admins = convo.get("admins", [])

    if user_data["email"] not in (admins or []):
        return {"error": "Only admin can promote"}

    email = data.get("email")

    await conversation_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$addToSet": {"admins": email}}
    )

    return {"message": "User promoted to admin"}

@app.post("/delete-for-me/{conversation_id}")
async def delete_for_me(conversation_id: str, request: Request):

    auth = request.headers.get("Authorization")
    if not auth:
        return {"error": "Unauthorized"}

    token = auth.split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Invalid token"}

    user_email = user_data["email"]

    await conversation_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {
            "$addToSet": {"deleted_for": user_email},
            "$set": {f"cleared_at.{user_email}": datetime.utcnow()}  # 🔥 KEY LINE
        }
    )

    return {"message": "Chat cleared for you"}

@app.get("/messages/{conversation_id}")
async def get_messages(conversation_id: str, request: Request):

    auth = request.headers.get("Authorization")
    if not auth:
        return []

    token = auth.split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return []

    user_email = user_data["email"]

    convo = await conversation_collection.find_one({
        "_id": ObjectId(conversation_id)
    })

    cleared_time = None
    if convo:
        cleared_time = convo.get("cleared_at", {}).get(user_email)

    query = {"conversation_id": conversation_id}

    if cleared_time:
        query["created_at"] = {"$gt": cleared_time}

    data = await message_collection.find(query).sort("created_at", 1).to_list(50)

    for msg in data:
        msg["_id"] = str(msg["_id"])

    return data

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    token = websocket.query_params.get("token")
    user_data = verify_token(token)

    if not user_data:
        await websocket.close()
        return

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

    try:
        while True:
            data = json.loads(await websocket.receive_text())

            if data.get("type") == "typing":
                for conn in connections[conversation_id]:
                    if conn != websocket:
                        await conn.send_text(json.dumps({
                            "type": "typing",
                            "sender": user_email
                        }))
                continue
            text = data.get("text", "")
            image = data.get("image", None)

            if not text and not image:
                continue

            participants = convo["participants"]
            receivers = [p for p in participants if p != user_email]

            msg = {
                "conversation_id": conversation_id,
                "sender": user_email,
                "receivers": receivers,
                "text": text,
                "image": image,
                "created_at": datetime.utcnow()
            }

            await message_collection.insert_one(msg)

            await conversation_collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "last_message": text or "Image",
                        "last_message_at": datetime.utcnow()
                    }
                }
            )

            for conn in connections[conversation_id]:
                await conn.send_text(json.dumps({
                    "type": "message",
                    "sender": user_email,
                    "text": text,
                    "image": data.get("image")
                }))

    except WebSocketDisconnect:
        if websocket in connections[conversation_id]:
            connections[conversation_id].remove(websocket)

@app.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str, request: Request):

    auth = request.headers.get("Authorization")
    if not auth:
        return {"error": "Unauthorized"}

    token = auth.split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Invalid token"}

    convo = await conversation_collection.find_one({
        "_id": ObjectId(conversation_id)
    })

    if not convo:
        return {"error": "Conversation not found"}

    admins = convo.get("admins", [])

    return {
        "is_group": convo.get("is_group", False),
        "group_name": convo.get("group_name"),
        "admins": admins or [],
        "participants": convo.get("participants", [])
    }