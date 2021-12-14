import decimal
from decimal import Decimal


def to_precision(value: Decimal, precision: int, round_down=True) -> Decimal:
    rounding = decimal.ROUND_DOWN if round_down else decimal.ROUND_UP
    v = value.quantize(Decimal("1." + "0" * precision), rounding=rounding)
    return v


def count_zero_in_decimal_number(number):
    zeros = 0
    while number < Decimal("0.1"):
        number *= Decimal("10.0")
        zeros += 1
    return zeros


def to_auto_price_precision(v, rounding):
    """
    We want at maximum to keep 1/100 of 1bp price precision
    """
    return to_precision(v, count_zero_in_decimal_number(v * Decimal("0.0000001")) + 1, rounding)


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
