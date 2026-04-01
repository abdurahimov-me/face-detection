from utils.customs import IntEnum


class ConversationType(IntEnum):
    DIRECT = 1
    GROUP = 2


class MemberType(IntEnum):
    ADMIN = 1
    MEMBER = 2


class FileType(IntEnum):
    PHOTO = 1
    AUDIO = 2
    DOCUMENT = 3
    VIDEO = 4


class MessageType(IntEnum):
    TEXT = 1
    IMAGE = 2
    AUDIO = 3
    PHOTO = 4
