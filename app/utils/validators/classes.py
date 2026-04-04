from .base import BaseValidator
from .functions import (
    compare_vehicle_number,
    validate_list_phone
)


class VehicleNumber(str, BaseValidator):
    functions = (compare_vehicle_number,)
    example = '71 A 777 AA'


class ListPhone(list, BaseValidator):
    functions = (validate_list_phone,)
    example = ["998912324191"]
    json_schema = {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of strings"
    }
