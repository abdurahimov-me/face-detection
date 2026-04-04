__all__ = (
    'get_user_or_none',
    'user_or_none',
)

from typing import Union, Annotated

from fastapi import Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import get_db
from utils.jwt import Payload
from .current_payload import get_token_payload_or_none

User = None


async def get_user_or_none(
        db: Annotated[AsyncSession, Depends(get_db)],
        payload: Annotated[Payload, Depends(get_token_payload_or_none)],
) -> Union[User, None]:
    if payload:
        user = await User.repo.db_first(session=db, id=payload.id)

        if user:
            if user.is_active is False:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User is not active')
            return user

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User does not exist')


user_or_none = Annotated[User, Depends(get_user_or_none)]
