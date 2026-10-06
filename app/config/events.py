import asyncio

from fastapi import FastAPI

from config.qdrant import qdrant_db
from api.detection.services import close_peer_connections, get_face_engine


async def on_startup(app: FastAPI):
    await qdrant_db.connect()
    app.state.qdrant = qdrant_db.client
    await asyncio.to_thread(get_face_engine)


async def on_shutdown(app: FastAPI):
    await close_peer_connections()
    await qdrant_db.close()
