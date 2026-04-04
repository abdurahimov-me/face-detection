import typing as t

EVENTS = t.Literal[
    "new_message",
    "message_read",
    "message_delivered",
    "message_edited",
    "message_deleted",
    "user_typing",
    "user_stop_typing",
    "user_online",
    "user_offline",
]
