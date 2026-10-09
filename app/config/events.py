import asyncio

from fastapi import FastAPI

from config.qdrant import qdrant_db
from resources.detection.data import peer_connections
from resources.detection.engine import get_face_engine
from resources.repositories import FacesRepository


async def on_startup(app: FastAPI):
    await qdrant_db.connect()
    await FacesRepository(qdrant_db.client).ensure_collection()
    app.state.qdrant = qdrant_db.client
    await asyncio.to_thread(get_face_engine)


async def on_shutdown(app: FastAPI):
    await peer_connections.close()
    await qdrant_db.close()
