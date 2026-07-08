SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "temporary_password",
        "current_password",
        "new_password",
        "new_password_confirmation",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "cookies",
        "set-cookie",
        "secret",
        "token",
        "jwt_secret_key",
    }
)


def sanitize_for_audit(data: dict | None) -> dict | None:
    if data is None:
        return None
    return _sanitize_value(data)


def _sanitize_value(value):
    if isinstance(value, dict):
        return {
            key: ("***" if key.lower() in SENSITIVE_KEYS else _sanitize_value(val))
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value
