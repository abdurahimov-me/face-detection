import json
import asyncio
from dataclasses import dataclass, field
from fastapi import WebSocket
from typing import Dict, Set


@dataclass
class Channels:
    channels: Dict[str, Set[WebSocket]] = field(default_factory=dict)

    def add(self, channel: str, websocket: WebSocket):
        if channel in self.channels:
            self.channels[channel].add(websocket)
        else:
            self.channels[channel] = {websocket}

    def remove(self, channel: str, websocket: WebSocket):
        if channel in self.channels and websocket in self.channels[channel]:
            self.channels[channel].remove(websocket)

        if len(self.channels[channel]) == 0:
            del self.channels[channel]

    def __getitem__(self, item):
        if item in self.channels:
            return self.channels[item]


@dataclass
class Connections:
    conns: Dict[str, WebSocket] = field(default_factory=dict)

    def add(self, conn_id: str, conn: WebSocket):
        self.conns[conn_id] = conn

    def remove(self, conn_id: str):
        if conn_id in self.conns:
            del self.conns[conn_id]

    def get(self, conn_id: str):
        return self.conns.get(conn_id)

    @staticmethod
    def get_cleared_data(data):
        if data is not str:
            return json.dumps(data)
        return data

    async def send_all(self, data):

        data = self.get_cleared_data(data)
        await asyncio.gather(
            *[ws.send_text(data) for ws in self.conns.values()],
        )

    async def send_text(self, conn, data):
        data = self.get_cleared_data(data)
        if conn in self.conns:
            await self.conns[conn].send_text(data)

    def __iter__(self):
        return self.conns


connections = Connections()
channels = Channels()
