from decimal import Decimal


def to_decimal(v):
    if type(v) == Decimal:
        return v

    return Decimal(str(v))