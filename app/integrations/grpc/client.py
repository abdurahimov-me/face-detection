from __future__ import annotations

__all__ = (
    "grpc_client",
    "GRPCClient"
)

from typing import Optional

import grpc.aio

from integrations.grpc.stubs.user import user_pb2_grpc as user_grpc
from config.settings import APP_SETTINGS


class GRPCClient:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._channel: Optional[grpc.aio.Channel] = None

    async def connect(self) -> None:
        self._channel = grpc.aio.insecure_channel(f"{self._host}:{self._port}")

    async def close(self) -> None:
        if self._channel:
            await self._channel.close()
            self._channel = None

    @property
    def channel(self) -> grpc.aio.Channel:
        if self._channel is None:
            raise RuntimeError("gRPC client ulanmagan")
        return self._channel

    @property
    def user(self) -> user_grpc.UserServiceStub:
        return user_grpc.UserServiceStub(self.channel)


grpc_client = GRPCClient(
    host=APP_SETTINGS.GRPC_HOST,
    port=APP_SETTINGS.GRPC_PORT,
)
