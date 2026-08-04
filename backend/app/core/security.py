import datetime as dt

import jwt

from app.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM


def _now() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def create_access_token(user_id: int, role: str) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": settings.TOKEN_ISSUER,
        "iat": now,
        "exp": now + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "typ": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode + validate an access token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
        issuer=settings.TOKEN_ISSUER,
        options={"require": ["sub", "exp", "iat"]},
    )
