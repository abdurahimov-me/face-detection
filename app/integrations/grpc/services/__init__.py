__all__ = (
    "user_service",
)

from .user import UserGRPCService
from ..client import grpc_client

# user grpc service
user_service = UserGRPCService(grpc_client)
