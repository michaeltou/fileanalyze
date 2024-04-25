from decimal import Decimal, ROUND_HALF_UP


def mce_round(value, n_digits):
    return float(Decimal(str(value)).quantize(Decimal(f'0.{"0" * n_digits}'), rounding=ROUND_HALF_UP))