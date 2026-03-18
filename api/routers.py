from utils.routes import Routes, WSDispatchers
from . import webscoket

__routes__ = Routes(
    routers=()
)

__ws_routes__ = Routes(
    routers=(
        webscoket.router,
    )
)

