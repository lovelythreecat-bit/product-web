"""Password hashing and opaque credentials. Account identifiers are ASCII case-insensitive."""

import hashlib
import re
import secrets
import unicodedata

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError
from fastapi import HTTPException

HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, type=Type.ID)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))


def normalize_account(account):
    normalized = unicodedata.normalize("NFKC", account).strip().lower()
    if not re.fullmatch(r"[a-z0-9_][a-z0-9_.-]{2,63}", normalized):
        raise HTTPException(422)
    return normalized


def verify_password(encoded, password):
    try:
        return HASHER.verify(encoded, password)
    except VerificationError:
        return False


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()
