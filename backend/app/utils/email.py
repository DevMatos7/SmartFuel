import re


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email_format(email: str) -> bool:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email.strip()))
