from decimal import Decimal


def to_decimal(v):
    if type(v) == float:
        return Decimal(str(v))

    return Decimal(v)