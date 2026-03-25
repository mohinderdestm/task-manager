from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import datetime
from typing import Dict, List
from bson import ObjectId

from db import user_collection, message_collection, conversation_collection
from auth import create_token, verify_token

app = FastAPI()
templates = Jinja2Templates(directory="templates")

connections: Dict[str, List[WebSocket]] = {}

# ------------------ UI ------------------

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/home")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat/{conversation_id}")
async def chat_page(request: Request, conversation_id: str):
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "conversation_id": conversation_id}
    )

# ------------------ AUTH ------------------

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

# ------------------ CREATE CHAT ------------------
@app.post("/create-chat")
async def create_chat(request: Request, data: dict):
    token = request.headers.get("Authorization").split(" ")[1]
    user_data = verify_token(token)

    if not user_data:
        return {"error": "Unauthorized"}

    user_email = user_data["email"]
    other_user = data["other_user"]

    # ✅ CHECK IF CHAT EXISTS
    existing = await conversation_collection.find_one({
        "participants": {
            "$all": [user_email, other_user],
            "$size": 2
        },
        "is_group": {"$ne": True} 
    })

    if existing:
        return {"conversation_id": str(existing["_id"])}

    # ✅ CREATE NEW CHAT
    convo = {
        "participants": [user_email, other_user],
        "created_at": datetime.utcnow()
    }

    result = await conversation_collection.insert_one(convo)

    return {"conversation_id": str(result.inserted_id)}

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

    # ✅ include creator automatically
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

    if user_data["email"] != convo["admin"]:
        return {"error": "Only admin can add users"}

    new_users = data.get("users", [])

    await conversation_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$addToSet": {"participants": {"$each": new_users}}}
    )

    return {"message": "Users added"}

# ------------------ GET USER CONVERSATIONS ------------------

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
        "participants": user_email
    }).to_list(100)

    # clean response
    result = []
    for chat in chats:
        result.append({
            "conversation_id": str(chat["_id"]),
            "is_group": chat.get("is_group", False),
            "group_name": chat.get("group_name"),
            "participants": chat["participants"]
        })

    return result

# ------------------ GET MESSAGES ------------------

from bson import ObjectId
@app.get("/messages/{conversation_id}")
async def get_messages(conversation_id: str):
    data = await message_collection.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", 1).to_list(50)

    for msg in data:
        msg["_id"] = str(msg["_id"])

    return data
# ------------------ WEBSOCKET ------------------

@app.websocket("/ws/{conversation_id}")
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




# from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
# from fastapi.templating import Jinja2Templates
# from datetime import datetime
# from typing import Dict, List

# from db import message_collection, conversation_collection

# app = FastAPI()

# templates = Jinja2Templates(directory="templates")

# # store connections per conversation
# active_connections: Dict[str, List[WebSocket]] = {}


# # ------------------ WEBSOCKET ------------------
# @app.websocket("/ws/{conversation_id}/{user_id}")
# async def websocket_endpoint(websocket: WebSocket, conversation_id: str, user_id: str):
#     await websocket.accept()

#     if conversation_id not in active_connections:
#         active_connections[conversation_id] = []

#     active_connections[conversation_id].append(websocket)

#     try:
#         while True:
#             text = await websocket.receive_text()

#             # save message
#             msg = {
#                 "conversation_id": conversation_id,
#                 "sender": user_id,
#                 "text": text,
#                 "created_at": datetime.utcnow()
#             }

#             await message_collection.insert_one(msg)

#             # broadcast
#             for conn in active_connections[conversation_id]:
#                 await conn.send_text(f"{user_id}: {text}")

#     except WebSocketDisconnect:
#         active_connections[conversation_id].remove(websocket)


# # ------------------ CREATE CHAT ------------------
# @app.post("/create-chat")
# async def create_chat(data: dict):
#     convo = {
#         "participants": [data["user1"], data["user2"]],
#         "created_at": datetime.utcnow()
#     }

#     result = await conversation_collection.insert_one(convo)

#     return {"conversation_id": str(result.inserted_id)}


# # ------------------ GET MESSAGES ------------------
# @app.get("/messages/{conversation_id}")
# async def get_messages(conversation_id: str):
#     data = await message_collection.find(
#         {"conversation_id": conversation_id}
#     ).sort("created_at", 1).to_list(100)

#     return data


# # ------------------ UI ------------------
# @app.get("/")
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})


# @app.get("/chat/{conversation_id}/{user_id}")
# async def chat_page(request: Request, conversation_id: str, user_id: str):
#     return templates.TemplateResponse("chat.html", {
#         "request": request,
#         "conversation_id": conversation_id,
#         "user_id": user_id
#     })