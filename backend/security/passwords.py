"""Password hashing and verification utilities using bcrypt."""

import logging
from typing import Optional
import bcrypt

logger = logging.getLogger("banksim.security.passwords")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with automated salting.

    Password hashes must never be logged or exposed to API responses.
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    # bcrypt limits passwords to 72 bytes; encode to utf-8
    pwd_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Returns False safely on mismatch, None hash, or malformed hash format.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        pwd_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as exc:
        logger.warning("Password verification failure due to invalid hash format: %s", type(exc).__name__)
        return False
