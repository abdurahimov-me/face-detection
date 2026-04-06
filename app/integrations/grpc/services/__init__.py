__all__ = (
    "user_service",
)

from .user import UserGRPCClientService
from ..client import grpc_client

# user grpc service
user_service = UserGRPCClientService(grpc_client)
