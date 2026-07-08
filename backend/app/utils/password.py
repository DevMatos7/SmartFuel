import re

from app.core.exceptions import AppError
from app.utils.email import normalize_email


def validate_password(password: str, email: str | None = None) -> None:
    if len(password) < 8:
        raise AppError(
            "A senha deve possuir no mínimo 8 caracteres.",
            status_code=400,
            code="PASSWORD_POLICY_VIOLATION",
        )
    if not re.search(r"[A-Za-z]", password):
        raise AppError(
            "A senha deve possuir ao menos uma letra.",
            status_code=400,
            code="PASSWORD_POLICY_VIOLATION",
        )
    if not re.search(r"\d", password):
        raise AppError(
            "A senha deve possuir ao menos um número.",
            status_code=400,
            code="PASSWORD_POLICY_VIOLATION",
        )
    if email and password.lower() == normalize_email(email):
        raise AppError(
            "A senha não pode ser igual ao e-mail.",
            status_code=400,
            code="PASSWORD_POLICY_VIOLATION",
        )
