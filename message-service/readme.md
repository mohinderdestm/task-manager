# message-service

Real-time messaging microservice for Task Manager.
**Port:** `3008`

## Features
- One-to-one direct messaging
- Group conversations (create, add/remove members)
- Real-time WebSocket delivery with typing indicators
- Message history via REST API
- Online presence tracking
- Chat UI at `/chat` (Jinja2 template, no frontend framework needed)

## Folder Structure
```
message-service/
├── main.py                  ← FastAPI app, template route, startup
├── models.py                ← Pydantic models
├── database.py              ← Motor (MongoDB) connection
├── dependencies.py          ← JWT auth (Bearer + WS query param)
├── requirements.txt
├── .env.example             ← copy to .env and fill in
├── messaging/
│   ├── __init__.py
│   ├── router.py            ← All REST + WebSocket endpoints
│   └── ws_manager.py        ← WebSocket connection manager
├── templates/
│   └── chat.html            ← Full chat UI
└── static/                  ← (empty, for future assets)
```

## Setup (Windows PowerShell)

```powershell
# 1. Navigate into the service
cd message-service

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env
Copy-Item .env.example .env
# Edit .env with your MONGO_URI and JWT_SECRET_KEY

# 5. Run the service
python main.py
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET    | `/` | No | Health / info |
| GET    | `/health` | No | Health check |
| GET    | `/chat` | No | Chat UI (pass ?token=JWT) |
| WS     | `/messaging/ws?token=JWT` | JWT (query param) | Real-time WebSocket |
| POST   | `/messaging/conversations/direct` | JWT | Start DM |
| POST   | `/messaging/conversations/group` | JWT | Create group |
| GET    | `/messaging/conversations` | JWT | List my conversations |
| GET    | `/messaging/conversations/{id}` | JWT | Get one conversation |
| POST   | `/messaging/conversations/{id}/members` | JWT | Add member to group |
| DELETE | `/messaging/conversations/{id}/members/{uid}` | JWT | Remove member |
| GET    | `/messaging/conversations/{id}/messages` | JWT | Message history |
| POST   | `/messaging/conversations/{id}/messages` | JWT | Send via HTTP |
| DELETE | `/messaging/conversations/{id}/messages/{mid}` | JWT | Delete message |
| GET    | `/messaging/online` | JWT | List online users |

## Chat UI
Open `http://localhost:3008/chat` in the browser.
- Paste JWT token → Connect
- New DM: click ✉ button in sidebar
- New Group: click 👥 button
- WebSocket auto-reconnects on drop

## WebSocket Protocol

**Client → Server:**
```json
{ "type": "message", "conversation_id": "<id>", "content": "Hello!" }
{ "type": "typing",  "conversation_id": "<id>" }
{ "type": "read",    "conversation_id": "<id>" }
```

**Server → Client:**
```json
{ "type": "message",      "conversation_id": "...", "sender_id": "...", "content": "...", "created_at": "..." }
{ "type": "typing",       "conversation_id": "...", "user_id": "...", "user_name": "..." }
{ "type": "user_online",  "user_id": "...", "user_name": "..." }
{ "type": "user_offline", "user_id": "...", "user_name": "..." }
{ "type": "group_created","conversation_id": "...", "name": "..." }
{ "type": "member_added", "conversation_id": "...", "user_id": "...", "user_name": "..." }
{ "type": "error",        "detail": "..." }
```

## MongoDB Collections
- `messages` — all messages
- `conversations` — conversation metadata + member lists