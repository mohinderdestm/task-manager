from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"[WS] User {user_id} connected. Online: {len(self.active_connections)}")
    
    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        logger.info(f"[WS] Wser {user_id} disconnected. Online: {len(self.active_connections)}")

    async def send_to_user(self,user_id: str, payload: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception as e:
                logger.warning(f"[WS] Failed to send to {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast_to_members(
            self,
            member_ids: list[str],
            payload: dict,
            exclude_user_id: str | None = None,
    ):
        for uid in member_ids:
            if uid == exclude_user_id:
                continue
            await self.send_to_user(uid, payload)
    
    def is_online(self, user_id: str) -> bool:
        return user_id in self.active_connections
    
    def online_users(self) -> list[str]:
        return list(self.active_connections.keys())
    

manager = ConnectionManager()