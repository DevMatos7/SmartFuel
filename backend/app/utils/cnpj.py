import re


def _only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def validate_cnpj(cnpj: str) -> bool:
    digits = _only_digits(cnpj)
    if len(digits) != 14:
        return False
    if digits == digits[0] * 14:
        return False

    def calc_digit(nums: str, weights: list[int]) -> str:
        total = sum(int(n) * w for n, w in zip(nums, weights, strict=True))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = calc_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = calc_digit(digits[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits[-2:] == first + second


def normalize_cnpj(cnpj: str) -> str:
    return _only_digits(cnpj)


def format_cnpj(cnpj: str) -> str:
    digits = _only_digits(cnpj)
    if len(digits) != 14:
        return cnpj
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
