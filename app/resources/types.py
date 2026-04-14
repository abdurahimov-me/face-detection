import typing as t



MessageEvent = t.Literal[
    "created_group",
    "created_direct",
    "group_avatar_changed",
    "group_name_changed",
]