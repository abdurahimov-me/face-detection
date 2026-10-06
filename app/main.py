from fastapi import FastAPI

from config import APP_SETTINGS
from config.server import Server


def app(_=None) -> FastAPI:
    main = FastAPI(
        title=APP_SETTINGS.PROJECT_NAME,
        debug=APP_SETTINGS.DEBUG,
        version=APP_SETTINGS.VERSION,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
        },
        lifespan=Server.lifespan,
        root_path=APP_SETTINGS.ROOT_PATH,
    )

    @main.get('/api/health', include_in_schema=False)
    def health():
        return {'status': 'ok'}

    return Server(main).get_app()
