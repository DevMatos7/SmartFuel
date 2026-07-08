import re


def normalize_text(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip())
    return cleaned.upper()


def normalize_name(value: str) -> str:
    return normalize_text(value)
