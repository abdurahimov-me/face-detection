from fastapi import FastAPI

from config.qdrant import qdrant_db


async def on_startup(app: FastAPI):
    await qdrant_db.connect()
    app.state.qdrant = qdrant_db.client


async def on_shutdown(app: FastAPI):
    await qdrant_db.close()
