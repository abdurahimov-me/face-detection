import asyncio
from dataclasses import dataclass, field

from aiortc import RTCPeerConnection


@dataclass
class TrackIdentity:
    user_id: str | None = None
    full_name: str = "Noma'lum"
    score: float | None = None


@dataclass
class RTCConnection:
    _peer_connections: set[RTCPeerConnection] = field(default_factory=set)

    def add(self, peer_connection: RTCPeerConnection) -> None:
        self._peer_connections.add(peer_connection)

    def remove(self, peer_connection: RTCPeerConnection) -> None:
        self._peer_connections.discard(peer_connection)

    @property
    def peer_connections(self) -> set[RTCPeerConnection]:
        return self._peer_connections

    async def close(self) -> None:
        peers = list(self.peer_connections)
        self._peer_connections.clear()
        await asyncio.gather(*(peer.close() for peer in peers), return_exceptions=True)


peer_connections: RTCConnection = RTCConnection()
