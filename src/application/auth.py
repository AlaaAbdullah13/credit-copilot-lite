import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from src.domain.exceptions import AuthorityLimitExceeded

API_KEY_HEADER = APIKeyHeader(name="X-Role", auto_error=False)


def require_role(role: str):
    def _checker(x_role: str = Security(API_KEY_HEADER)):
        if x_role is None:
            raise HTTPException(status_code=401, detail="Missing role header")

        normalized = x_role.strip().lower().replace(" ", "_")
        allowed_roles = {"loan_officer", "credit_officer", "admin"}
        if normalized not in allowed_roles:
            raise HTTPException(status_code=403, detail="Unknown role")

        if role == "loan_officer" and normalized != "loan_officer":
            raise HTTPException(status_code=403, detail="Requires Loan Officer role")
        if role == "credit_officer" and normalized not in {"credit_officer", "admin"}:
            raise HTTPException(status_code=403, detail="Requires Credit Officer role")
        if role == "admin" and normalized != "admin":
            raise HTTPException(status_code=403, detail="Requires Admin role")

        return normalized

    return _checker


def enforce_authority_limit(amount: float, *, actor_role: str | None = None, authority_limit: float | None = None):
    normalized_role = (actor_role or "credit_officer").strip().lower().replace(" ", "_")
    limit = float(authority_limit if authority_limit is not None else os.getenv("CREDIT_OFFICER_AUTHORITY_LIMIT", "250000"))
    if amount > limit and normalized_role != "admin":
        raise AuthorityLimitExceeded(
            f"Requested amount {amount} exceeds the assigned authority limit of {limit}."
        )
    return True
