from fastapi import FastAPI, Request

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
        root_path="/chat-back",
    )

    @main.get('/', include_in_schema=False)
    def index(request: Request):
        return {'docs': f'{request.url}docs'}

    return Server(main).get_app()
