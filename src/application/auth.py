from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
import os

# Simple header-based role check for boilerplate/demo purposes
API_KEY_HEADER = APIKeyHeader(name="X-Role", auto_error=False)


def require_role(role: str):
    def _checker(x_role: str = Security(API_KEY_HEADER)):
        if x_role is None:
            raise HTTPException(status_code=401, detail="Missing role header")
        if x_role != role:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return x_role

    return _checker


def enforce_authority_limit(amount: float):
    limit = float(os.getenv("CREDIT_OFFICER_AUTHORITY_LIMIT", "250000"))
    if amount > limit:
        raise HTTPException(status_code=403, detail="Authority limit exceeded")
