__all__ = (
    'File',
)

from typing import TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

T = TypeVar("T", bound="Base")

from ..base import BaseModel
from ..mixinis import DeletedMixin


class File(BaseModel, DeletedMixin):
    __tablename__ = "files"

    file: Mapped[str] = mapped_column(
        sa.String(255),
    )
    ext: Mapped[str] = mapped_column(
        sa.String(255),
    )
    filename: Mapped[str] = mapped_column(
        sa.String(255),
    )
