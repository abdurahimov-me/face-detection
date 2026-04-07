import typing as t

import grpc

from integrations.grpc.client import GRPCClient
from integrations.grpc.stubs.user import user_pb2


class UserGRPCClientService:
    def __init__(self, client: GRPCClient) -> None:
        self._client = client

    @property
    def client(self) -> GRPCClient:
        return self._client

    @client.setter
    def client(self, client: GRPCClient) -> None:
        self._client = client

    async def get_user(self, user_id: int, tenant: str) -> t.Optional[user_pb2.UserResponse]:
        try:
            return await self._client.user.GetUser(
                user_pb2.GetUserRequest(user_id=user_id, tenant=tenant)
            )
        except grpc.aio.AioRpcError as e:
            print(e)
            return None

    async def get_users(self, user_ids: t.List[int], tenant: str) -> t.Optional[t.List[user_pb2.UserResponse]]:
        try:
            response = await self._client.user.GetUsers(
                user_pb2.GetUsersRequest(user_ids=user_ids, tenant=tenant)
            )
            return list(response.users)
        except grpc.aio.AioRpcError as e:
            print(e)
            return None
