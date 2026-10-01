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


class PricingNotFound(Exception):
    """Raised when no pricing-table row applies to an application."""


class PolicySourceUnavailable(Exception):
    """Raised when a required policy source cannot be read at runtime."""


class LLMProviderError(Exception):
    """Raised when an external LLM provider cannot complete a request safely."""


__all__ = [
    "AuthorityLimitExceeded",
    "InvalidApplication",
    "InvalidLLMOutput",
    "LLMProviderError",
    "PolicyEditionNotFound",
    "PolicySourceUnavailable",
    "PricingNotFound",
    "UnverifiedExtraction",
]
