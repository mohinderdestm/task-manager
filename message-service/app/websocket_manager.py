from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        
        user_id = user_id.lower()
        self.active_connections[user_id] = websocket
        print(f"Connected: {user_id}")

    def disconnect(self, user_id: str):
        user_id = user_id.lower()
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"Disconnected: {user_id}")

    #  Send to specific user
    async def send_personal_message(self, message: str, user_id: str):
        user_id = user_id.lower()
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)
        else:
            print(f"User {user_id} not connected")

    # Broadcast message to receiver
    async def send_message(self, message: str, receiver_id: str, sender_name: str = None):
        receiver_id = receiver_id.lower()
        
        # Send to receiver
        if receiver_id in self.active_connections:
            display_msg = f"{sender_name}: {message}" if sender_name else message
            await self.active_connections[receiver_id].send_text(display_msg)
        
        print(f"Sent to {receiver_id}: {display_msg}")

manager = ConnectionManager()