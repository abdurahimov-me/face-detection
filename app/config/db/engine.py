__all__ = (
    'DatabaseHelper',
    'db_helper',
    'get_db',
)

from asyncio import current_task
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, async_scoped_session

from config.settings import DB_SETTINGS


class DatabaseHelper:
    def __init__(self, url, echo: bool):
        self.engine = create_async_engine(url, echo=echo)
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
        )

    def get_scoped_session(self):
        session = async_scoped_session(
            session_factory=self.session_factory,
            scopefunc=current_task,
        )
        return session

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self.session_factory is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


db_helper = DatabaseHelper(DB_SETTINGS.URL, DB_SETTINGS.ECHO)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with db_helper.session() as session:
        yield session
