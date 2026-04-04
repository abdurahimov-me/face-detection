from utils import IntEnum


class ProductStatus(IntEnum):
    WAITING_AI = 0
    WAITING_HUMAN = 1
    ACCEPTED = 2
    REJECTED = 3


class CommonStatus(IntEnum):
    REJECTED = -1
    PENDING = 0
    APPROVED = 1


class Providers(IntEnum):
    CLICK = 1
    PAYME = 2
    WALLET = 3
