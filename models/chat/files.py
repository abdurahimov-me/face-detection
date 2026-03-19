__all__ = (
    'File',
    'SecondaryFile',
)

import typing as t

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from resources.enums import MessageFileType
from utils.customs import IntEnumField
from ..base import BaseModel, Base
from ..mixinis import DeletedMixin

if t.TYPE_CHECKING:
    from .message import Message


class SecondaryFile(Base):
    __tablename__ = "message_files"
    id = None
    product_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey('messages.id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
    )
    tag_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey('files.id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
    )


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
    size: Mapped[int] = mapped_column(
        sa.BigInteger(),
    )
    type: Mapped[int] = mapped_column(
        IntEnumField(MessageFileType),
        default=MessageFileType.PHOTO
    )

    products: Mapped[t.List['Message']] = relationship(
        "Message",
        secondary="message_files",
        back_populates="files",
        passive_deletes=True,
    )
