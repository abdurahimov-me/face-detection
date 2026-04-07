import typing as t
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class ConnectionManager:
    connections: t.Dict[str, WebSocket] = field(default_factory=dict)
    channels: t.DefaultDict[str, t.Set[str]] = field(default_factory=lambda: __import__('collections').defaultdict(set))

    def check_connection(self, conn_id: str) -> bool:
        return conn_id in self.connections

    async def connect(self, conn_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[conn_id] = ws

    def disconnect(self, conn_id: str):
        self.connections.pop(conn_id, None)
        for members in self.channels.values():
            members.discard(conn_id)

    def join_channel(self, conn_id: str, channel_id: str):
        if self.check_connection(conn_id):
            self.channels[channel_id].add(conn_id)

    def leave_channel(self, conn_id: str, channel_id: str):
        self.channels[channel_id].discard(conn_id)

    async def send(self, conn_id: str, message: dict):
        ws = self.connections.get(conn_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, channel_id: str, message: dict, exclude: str = None):
        for conn_id in self.channels.get(channel_id, set()):
            if conn_id == exclude:
                continue
            await self.send(conn_id, message)


    def __repr__(self):
        return f"ConnectionsManager(connections={self.connections})"


connections_manager: ConnectionManager = ConnectionManager()
