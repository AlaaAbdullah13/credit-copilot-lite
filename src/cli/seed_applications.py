"""Seed the five synthetic packs into the isolated untrusted collection."""

from src.infrastructure.ingestion.application_packs import seed_application_packs
from src.infrastructure.llm.provider_factory import create_llm_provider
from src.infrastructure.vector_store.untrusted_application_store import (
    UntrustedApplicationStore,
)


def main() -> None:
    print(seed_application_packs(UntrustedApplicationStore(create_llm_provider())))


if __name__ == "__main__":
    main()
