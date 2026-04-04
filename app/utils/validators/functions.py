import re


def compare_vehicle_number(value: str) -> bool:
    value = re.split(r'\s+', value)
    digit = False
    upper = False

    checking = []
    for char in value:
        isdigit = char.isdigit()
        isupper = char.isupper()
        digit = digit or isdigit
        upper = upper or isupper

        checking.append(isupper or isdigit)
    return digit and upper and all(checking)


def validate_list_phone(value: list[str]):
    return all([item.isdigit() and len(item) == 12 for item in value])
