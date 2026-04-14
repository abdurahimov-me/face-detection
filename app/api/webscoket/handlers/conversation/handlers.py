import sqlalchemy as sa
from fastapi import WebSocket
from sqlalchemy import orm

from config import AWS_SETTINGS
from config.db import db_helper
from config.redis import cache
from models import User, Message, MessageRead, Conversation, SecondaryFile, File, Member
from resources.enums import ConversationType
from resources.managers.ws.dispatcher import WSDispatcher
from resources.managers.ws.manager import chat_ws_manager
from utils.exceptions import WSException
from . import schemas

dp = WSDispatcher()

ReplyMessage = orm.aliased(Message)
ReplyUser = orm.aliased(User)


@dp.command("get_messages")
async def handle_get_messages(
        websocket: WebSocket,
        payload: schemas.GetMessagesModel,
        user: User,
):
    async with db_helper.session() as session:
        cursor = payload.cursor
        direction = payload.direction

        if cursor is None:
            first_unread = await session.scalar(
                sa.select(sa.func.min(Message.id))
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Message.deleted.is_(False),
                    Message.sender_id != user.id,
                    Conversation.uuid == payload.conversation_uuid,
                    ~sa.exists().where(
                        sa.and_(
                            MessageRead.message_id == Message.id,
                            MessageRead.user_id == user.id,
                        )
                    )
                )
            )
            cursor = first_unread

        unread_count = await session.scalar(
            sa.select(sa.func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.uuid == payload.conversation_uuid,
                Message.deleted.is_(False),
                Message.sender_id != user.id,
                ~sa.exists().where(
                    sa.and_(
                        MessageRead.message_id == Message.id,
                        MessageRead.user_id == user.id,
                    )
                )
            )
        )

        files_subquery = (
            sa.select(
                SecondaryFile.message_id,
                sa.func.json_agg(
                    sa.func.json_build_object(
                        "id", File.id,
                        "file", File.file,
                        "ext", File.ext,
                        "filename", File.filename,
                        "size", File.size,
                        "user_id", File.user_id,
                        "type", File.type,
                        "meta_data", File.meta_data,
                    )
                ).label("files")
            )
            .join(File, File.id == SecondaryFile.file_id)
            .group_by(SecondaryFile.message_id)
            .subquery()
        )

        base_stmt = (
            sa.select(
                Message.id,
                Message.text,
                Message.sender_id,
                Message.created_at,
                Message.reply_id,
                Message.conversation_id,
                Message.type,
                ReplyUser.first_name.label("reply_first_name"),
                ReplyUser.last_name.label("reply_last_name"),
                sa.func.left(ReplyMessage.text, 20).label("reply_text"),
                ReplyMessage.type.label("reply_type"),
                User.user_id,
                User.first_name,
                User.last_name,
                User.face,
                sa.select(
                    sa.exists().where(
                        sa.and_(
                            MessageRead.message_id == Message.id,
                        )
                    )
                ).scalar_subquery().label("read"),
                sa.func.coalesce(files_subquery.c.files, sa.cast(sa.text("'[]'"), sa.JSON)).label("files"),
            )
            .join(User, User.id == Message.sender_id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(ReplyMessage, ReplyMessage.id == Message.reply_id, isouter=True)
            .join(ReplyUser, ReplyUser.id == ReplyMessage.sender_id, isouter=True)
            .outerjoin(files_subquery, files_subquery.c.message_id == Message.id)
            .where(
                Conversation.uuid == payload.conversation_uuid,
                Message.deleted.is_(False),
            )
            .limit(20)
        )

        if direction == "up" and cursor:
            stmt = base_stmt.where(Message.id < cursor).order_by(Message.id.desc())
            result = (await session.execute(stmt)).mappings().all()
            prev_cursor = result[-1]["id"] if len(result) == 20 else None
            next_cursor = cursor

        elif direction == "down" and cursor:
            stmt = base_stmt.where(Message.id >= cursor).order_by(Message.id.asc())
            result = (await session.execute(stmt)).mappings().all()
            next_cursor = result[-1]["id"] + 1 if len(result) == 20 else None
            prev_cursor = cursor

        else:
            if cursor is not None:
                up_stmt = base_stmt.where(Message.id < cursor).order_by(Message.id.desc()).limit(10)
                down_stmt = base_stmt.where(Message.id >= cursor).order_by(Message.id.asc()).limit(10)

                up_result = (await session.execute(up_stmt)).mappings().all()
                down_result = (await session.execute(down_stmt)).mappings().all()

                result = list(reversed(up_result)) + list(down_result)
                prev_cursor = up_result[-1]["id"] if len(up_result) == 10 else None
                next_cursor = down_result[-1]["id"] + 1 if len(down_result) == 10 else None
            else:
                stmt = base_stmt.order_by(Message.id.desc())
                result = (await session.execute(stmt)).mappings().all()
                result = list(reversed(result))
                prev_cursor = result[0]["id"] - 1 if len(result) == 20 else None
                next_cursor = None

    return schemas.ResponseMessageModel(
        prev_cursor=prev_cursor,
        next_cursor=next_cursor,
        unread_count=unread_count,
        messages=result,
    )


@dp.command("mark_as_read")
async def handle_mark_as_read(
        websocket: WebSocket,
        payload: schemas.MarkAsReadModel,
        user: User,
):
    async with db_helper.session() as session:
        conversation_id = await session.scalar(
            sa.select(Conversation.id)
            .where(Conversation.uuid == payload.conversation_uuid)
        )

        if not conversation_id:
            return {
                "marked": 0
            }

        unread_ids = (await session.execute(
            sa.select(Message.id)
            .where(
                Message.conversation_id == conversation_id,
                Message.id <= payload.message_id,
                Message.sender_id != user.id,
                Message.deleted.is_(False),
                ~sa.exists().where(
                    sa.and_(
                        MessageRead.message_id == Message.id,
                        MessageRead.user_id == user.id,
                    )
                )
            )
        )).scalars().all()

        if not unread_ids:
            return {
                "marked": 0
            }

        await session.execute(
            sa.insert(MessageRead).values([
                {"message_id": msg_id, "user_id": user.id}
                for msg_id in unread_ids
            ])
        )
        await session.commit()
        event_data = {
            "conversation_uuid": str(payload.conversation_uuid),
            "messages": [unread_ids]
        }
        await chat_ws_manager.send_to_conv(
            conversation_id,
            data=event_data,
            event="message_read",
            exclude_conn=user.conn_id,
        )
        return {
            "marked": len(unread_ids)
        }


@dp.command("get_read_users")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.GetReadUsersModel,
        user: User,
):
    async with db_helper.session() as session:
        # conv_id = await Conversation.get_conversation_field(session, payload.conversation_uuid, "id")
        users_stmt = (
            sa.select(User.id, User.first_name, User.last_name, User.face, MessageRead.read_at)
            .select_from(MessageRead)
            .join(User, User.id == MessageRead.user_id)
            .join(Message, Message.id == MessageRead.message_id)
            .where(
                MessageRead.message_id == payload.message_id,
                MessageRead.user_id != user.id,
                Message.sender_id == user.id,
            )
        )
        users = (await session.execute(users_stmt)).mappings().all()
        return schemas.ReadUsersModelResponse(users=users)


@dp.command("conversation_info")
async def conversation_info(
        websocket: WebSocket,
        payload: schemas.ConversationInfoModel,
        user: User,
):
    conversation_uuid = payload.conversation_uuid
    async with db_helper.session() as session:
        if conversation_uuid is None and payload.partner:
            print(payload.partner)
            partner: User = await User.repo.db_first(
                session=session,
                user_id=payload.partner.user_id,
                tenant=payload.partner.tenant,
            )
            if not partner:
                raise WSException("Partner not found")
            conv_stmt = (
                sa.select(Conversation.uuid)
                .select_from(Conversation)
                .join(Member, Member.conversation_id == Conversation.id)
                .where(Member.user_id == user.id)
                .limit(1)
            )
            conversation_uuid = (await session.execute(conv_stmt)).scalar_one_or_none()
            if not conversation_uuid:
                return {
                    "name": partner.full_name,
                    "encrypt": partner.encrypt,
                    "poster": AWS_SETTINGS.make_hr_cdn_url(partner.face),
                    "online": await partner.is_online(),
                }

        if conversation_uuid:
            conv_stmt = (
                sa.select(
                    Conversation.id,
                    Conversation.uuid,
                    Conversation.name,
                    Conversation.type,
                    Conversation.created_at,
                    Conversation.poster_id,
                    File.file.label("poster"),
                )
                .select_from(Conversation)
                .join(File, File.id == Conversation.poster_id, isouter=True)
                .where(Conversation.uuid == conversation_uuid)
                .limit(1)
            )

            item = (await session.execute(conv_stmt)).mappings().first()
            if item is None:
                raise WSException("Conversation not found")
            data = {
                "uuid": str(item.uuid),
                "name": item.name,
                "type": item.type,
                "poster": AWS_SETTINGS.make_cdn_url(item.poster),
                "created_at": item.created_at.isoformat(),
                "online": False,
                "poster_id": item.poster_id,
            }
            members_base_stmt = (
                sa.select(User)
                .join(Member, Member.user_id == user.id)
                .where(Member.conversation_id == item.id)
            )

            if item.type == ConversationType.DIRECT:
                partner_stmt = (
                    members_base_stmt
                    .where(Member.user_id != User.id)
                    .limit(1)
                )
                partner = (await session.execute(partner_stmt)).scalar_one_or_none()
                if partner is None:
                    raise WSException("Partner not found")

                data["name"] = partner.full_name
                data["poster"] = AWS_SETTINGS.make_hr_cdn_url(partner.face)
                data["online"] = await partner.is_online()
                data["encrypt"] = partner.encrypt

            return data

    raise WSException("Method not implemented")
