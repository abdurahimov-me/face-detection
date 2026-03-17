from django.db import models


class UserRoles(models.IntegerChoices):
    NONE = 0, 'None'
    CUSTOMER = 100, 'Customer'
    REGULAR_DRIVER = 200, 'Regular Driver'
    GARAGE_DRIVER = 201, 'Garage Driver'
    LEGAL_DRIVER = 202, 'Legal Driver'


class TruckStatus(models.TextChoices):
    EMPTY = 'empty', 'Empty'
    ACTIVE = 'active', 'Active'
    INVALID = 'invalid', 'Invalid'


class TrailerType(models.TextChoices):
    TENT = 'tent', 'Tent'
    REF = 'ref', 'Ref'
    CONTAINER = 'container', 'Container'


class TruckType(models.TextChoices):
    TRAILER = 'trailer', 'Trailer'
    WITHOUT_TRAILER = 'without_trailer', 'Without trailer'


class CheckingConditions(models.TextChoices):
    WAITING = 'waiting', 'Waiting'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class OrderStatus(models.IntegerChoices):
    WAITING = 0, 'Waiting'
    APPROVED = 1, 'Approved'
    REJECTED = -1, 'Rejected'


class OfferStatus(models.IntegerChoices):
    WAITING = 0, 'Waiting'
    APPROVED = 1, 'Approved'
    REJECTED = -1, 'Rejected'


class OrderType(models.TextChoices):
    DOMESTIC = 'domestic', 'Domestic'
    IMPORT = 'import', 'Import'
    EXPORT = 'export', 'Export'


class Rates(models.IntegerChoices):
    ONE = 1, 'One'
    TWO = 2, 'Two'
    THREE = 3, 'Three'
    FOUR = 4, 'Four'
    FIVE = 5, 'Five'


class ConditionStatus(models.TextChoices):
    WAITING = 'waiting', 'Waiting'
    PROCESSING = 'processing', 'Processing'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class LocConditionStatus(models.TextChoices):
    NEW = 'new', 'New'
    ARRIVED = 'arrived', 'Arrived'
    LOADED = 'loaded', 'Loaded'
    UNLOADED = 'unloaded', 'Unloaded'


class LocationType(models.TextChoices):
    LOADING = 'loading', 'Loading'
    UNLOADING = 'unloading', 'Unloading'
