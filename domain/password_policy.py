from __future__ import annotations

from shared_backend.errors.custom_exceptions import WeakPasswordError


MIN_PASSWORD_LENGTH = 12
COMMON_PASSWORDS = {
    "000000000000",
    "111111111111",
    "123456789012",
    "azertyuiopqs",
    "password1234",
    "password12345",
    "qwertyuiopas",
}


def validate_password_policy(password: str) -> None:
    candidate = password.strip()
    if len(candidate) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must contain at least {MIN_PASSWORD_LENGTH} characters"
        )
    if candidate.lower() in COMMON_PASSWORDS:
        raise WeakPasswordError("Password is too common")
    if len(set(candidate)) < 4:
        raise WeakPasswordError("Password must contain more varied characters")
