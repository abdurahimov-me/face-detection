from utils.customs import IntEnum


class ConversationType(IntEnum):
    DIRECT = 1
    GROUP = 2


class MemberType(IntEnum):
    ADMIN = 1
    MEMBER = 2


class MessageFileType(IntEnum):
    PHOTO = 1
    AUDIO = 2
    DOCUMENT = 3
    VIDEO = 4
