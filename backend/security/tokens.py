"""Cryptographic token generation and verification for BankSim."""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from backend.config import get_settings

logger = logging.getLogger("banksim.security.tokens")


class TokenError(Exception):
    """Base exception for token validation failures."""

    pass


class TokenExpiredError(TokenError):
    """Raised when an authentication token has expired."""

    pass


class TokenInvalidError(TokenError):
    """Raised when an authentication token is malformed or invalid."""

    pass


def create_access_token(
    claims: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Tokens and signing secrets are never logged.
    """
    settings = get_settings()
    to_encode = claims.copy()
    now_utc = datetime.now(timezone.utc)

    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now_utc,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token.

    Raises TokenExpiredError if expired, or TokenInvalidError if signature/format invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Authentication token has expired.") from exc
    except InvalidTokenError as exc:
        raise TokenInvalidError("Invalid or tampered authentication token.") from exc
