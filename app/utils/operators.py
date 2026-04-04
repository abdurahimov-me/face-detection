import operator

OPERATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b
}
