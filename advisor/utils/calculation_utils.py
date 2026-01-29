from decimal import Decimal


def sum_decimal(fist_dec: Decimal, second: float | int) -> Decimal:
    return fist_dec + Decimal(second)
