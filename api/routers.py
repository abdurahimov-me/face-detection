from utils.routes import Routes
from . import webscoket, common

__routes__ = Routes(
    routers=(
        common.router,
    )
)

__ws_routes__ = Routes(
    routers=(
        webscoket.router,
    )
)
