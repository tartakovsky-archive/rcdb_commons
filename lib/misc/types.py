from decimal import Decimal


def to_decimal(v):
    if v is None:
        return v

    if type(v) == Decimal:
        return v

    return Decimal(str(v))