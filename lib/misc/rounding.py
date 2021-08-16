import decimal
from decimal import Decimal


def to_precision(value: Decimal, precision: int, round_down=True) -> Decimal:
    rounding = decimal.ROUND_DOWN if round_down else decimal.ROUND_UP
    v = value.quantize(Decimal("1." + "0" * precision), rounding=rounding)
    return v


class Rounder:
    ROUND_UP = decimal.ROUND_UP
    ROUND_DOWN = decimal.ROUND_DOWN
    ROUND_FLOOR = decimal.ROUND_FLOOR
    ROUND_HALF_UP = decimal.ROUND_HALF_UP
    ROUND_HALF_EVEN = decimal.ROUND_HALF_EVEN

    @staticmethod
    def to_precision(value: Decimal, precision: int, rounding) -> Decimal:
        v = value.quantize(Decimal("1." + "0" * precision), rounding=rounding)
        return v
