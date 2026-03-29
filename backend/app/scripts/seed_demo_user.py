import argparse
import sys

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth import create_user, normalize_email


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed a local Airzone demo user.")
    parser.add_argument("--email", required=True, help="Email for the demo user")
    parser.add_argument("--password", required=True, help="Password for the demo user")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    email = normalize_email(args.email)

    with SessionLocal() as db:
        try:
            existing_user = db.scalar(select(User).where(User.email == email))
        except OperationalError:
            parser.error("Database tables are missing. Run Alembic migrations first.")

        if existing_user:
            print(f"Demo user already exists: {email}")
            return 0

        create_user(db, email=email, password=args.password)
        print(f"Created demo user: {email}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
