import typing as t
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class ConnectionManager:
    connections: t.Dict[str, WebSocket] = field(default_factory=dict)
    channels: t.DefaultDict[str, t.Set[str]] = field(default_factory=lambda: __import__('collections').defaultdict(set))

    async def connect(self, con_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[con_id] = ws

    def disconnect(self, con_id: str):
        self.connections.pop(con_id, None)
        for members in self.channels.values():
            members.discard(con_id)

    def join_channel(self, con_id: str, channel_id: str):
        self.channels[channel_id].add(con_id)

    def leave_channel(self, con_id: str, channel_id: str):
        self.channels[channel_id].discard(con_id)

    async def send(self, con_id: str, message: dict):
        ws = self.connections.get(con_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, channel_id: str, message: dict, exclude: str = None):
        for con_id in self.channels.get(channel_id, set()):
            if con_id == exclude:
                continue
            await self.send(con_id, message)


connections = ConnectionManager()
