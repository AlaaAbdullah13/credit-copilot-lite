"""Seed demo users after `alembic upgrade head`.

Passwords are read only from LOAN_OFFICER_PASSWORD and CREDIT_OFFICER_PASSWORD.
"""

from src.application.api.main import seed_demo_users


def main() -> None:
    seed_demo_users()


if __name__ == "__main__":
    main()
