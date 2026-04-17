from utils.routes import Routes

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
