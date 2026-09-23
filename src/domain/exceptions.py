class PolicyEditionNotFound(Exception):
    """Raised when a requested policy edition does not exist."""


class InvalidApplication(Exception):
    """Raised when required application payload fields are missing or malformed."""


class UnverifiedExtraction(Exception):
    """Raised when extracted data fails exact quote verification against source documents."""


class InvalidLLMOutput(Exception):
    """Raised when LLM output cannot be parsed into the target Pydantic schema or JSON structure."""


class AuthorityLimitExceeded(Exception):
    """Raised when a Credit Officer attempts to approve an application exceeding their limit."""


__all__ = [
    "AuthorityLimitExceeded",
    "InvalidApplication",
    "InvalidLLMOutput",
    "PolicyEditionNotFound",
    "UnverifiedExtraction",
]
