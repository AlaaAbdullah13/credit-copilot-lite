import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.domain.exceptions import AuthorityLimitExceeded

bearer = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    description="Paste the token returned by /login.",
)
ALGORITHM = "HS256"


def _scrypt_n() -> int:
    """Use the production-strength cost unless a test environment lowers it."""
    value = int(os.getenv("SCRYPT_N", str(2**14)))
    if value < 2 or value & (value - 1):
        raise ValueError("SCRYPT_N must be a power of two greater than one")
    return value


def _secret() -> str:
    secret = os.getenv("AUTH_TOKEN_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="AUTH_TOKEN_SECRET is required")
    return secret


def hash_password(password: str) -> str:
    """Store passwords with stdlib scrypt; never persist plaintext credentials."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_scrypt_n(), r=8, p=1)
    return base64.b64encode(salt + digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    raw = base64.b64decode(encoded.encode())
    salt, expected = raw[:16], raw[16:]
    actual = hashlib.scrypt(password.encode(), salt=salt, n=_scrypt_n(), r=8, p=1)
    return hmac.compare_digest(actual, expected)


def issue_token(username: str, role: str, authority_limit: float) -> str:
    return jwt.encode(
        {
            "sub": username,
            "role": role,
            "authority_limit": authority_limit,
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        },
        _secret(),
        algorithm=ALGORITHM,
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        return jwt.decode(credentials.credentials, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def require_role(*roles: str):
    def _checker(user: dict = Security(current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _checker


def enforce_authority_limit(amount: float, authority_limit: float | None = None):
    limit = (
        authority_limit
        if authority_limit is not None
        else float(os.getenv("CREDIT_OFFICER_AUTHORITY_LIMIT", "250000"))
    )
    if amount > limit:
        raise AuthorityLimitExceeded(
            f"Amount EGP {amount:,.0f} exceeds authority limit EGP {limit:,.0f}."
        )
