from app.integrations.grpc.client import GRPCClient
from app.integrations.grpc.stubs.user import user_pb2


class UserGRPCService:
    def __init__(self, client: GRPCClient) -> None:
        self._client = client

    async def get_user(self, user_id: int, tenant: str) -> user_pb2.UserResponse:
        return await self._client.user.GetUser(
            user_pb2.GetUserRequest(user_id=user_id, tenant=tenant)
        )

    async def get_users(self, user_ids: list[int], tenant: str) -> list[user_pb2.UserResponse]:
        response = await self._client.user.GetUsers(
            user_pb2.GetUsersRequest(user_ids=user_ids, tenant=tenant)
        )
        return list(response.users)
