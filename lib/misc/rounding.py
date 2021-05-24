import decimal
from decimal import Decimal


def to_precision(value: Decimal, precision: int, round_down=True) -> Decimal:
    rounding = decimal.ROUND_DOWN if round_down else decimal.ROUND_UP
    v = value.quantize(Decimal("1." + "0" * precision), rounding=rounding)
    return v