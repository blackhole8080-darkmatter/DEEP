"""
interface/ws/manager.py

WebSocket connection manager for DEEP real-time endpoints.
"""
from fastapi import WebSocket
from typing import Set

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
    
    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
    
    async def send(self, ws: WebSocket, message: dict):
        try:
            await ws.send_json(message)
        except Exception:
            pass

manager = ConnectionManager()
