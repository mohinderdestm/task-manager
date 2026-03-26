from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()

        user_id = user_id.lower()  # ✅ normalize

        self.active_connections[user_id] = websocket

        print(f"✅ Connected: {user_id}")
        print(f"🔍 Active users: {list(self.active_connections.keys())}")

    def disconnect(self, user_id: str):
        user_id = user_id.lower()

        if user_id in self.active_connections:
            del self.active_connections[user_id]

            print(f"❌ Disconnected: {user_id}")
            print(f"🔍 Active users: {list(self.active_connections.keys())}")

    async def send_personal_message(self, message: str, user_id: str):
        user_id = user_id.lower()

        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)
        else:
            print(f"❌ User {user_id} not connected")

manager = ConnectionManager()