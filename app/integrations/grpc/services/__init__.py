__all__ = (
    "user_grpc_service",
)

from .user import UserGRPCClientService
from ..client import grpc_client

user_grpc_service: UserGRPCClientService = UserGRPCClientService(grpc_client)
