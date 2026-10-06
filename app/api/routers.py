from utils.routes import Routes
from api.detection.router import router as detection_router
from api.faces.router import router as faces_router

__routes__ = Routes(
    routers=(
        detection_router,
        faces_router,
    )
)

__ws_routes__ = Routes(
    routers=(
    )
)
