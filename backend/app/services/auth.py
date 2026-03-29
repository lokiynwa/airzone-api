from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_session_token, verify_password
from app.models.session import UserSession
from app.models.user import User


class DuplicateUserError(Exception):
    pass


class AuthenticationError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_user(db: Session, *, email: str, password: str) -> User:
    normalized_email = normalize_email(email)
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user:
        raise DuplicateUserError

    user = User(email=normalized_email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    normalized_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user or not verify_password(password, user.password_hash):
        raise AuthenticationError
    return user


def create_session(db: Session, *, user: User, raw_token: str, expires_at: datetime) -> UserSession:
    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=expires_at,
        last_seen_at=datetime.now(UTC),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def resolve_user_from_session_token(db: Session, raw_token: str) -> User | None:
    token_hash = hash_session_token(raw_token)
    user_session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if not user_session:
        return None

    now = datetime.now(UTC)
    if _as_utc(user_session.expires_at) <= now:
        db.delete(user_session)
        db.commit()
        return None

    user_session.last_seen_at = now
    db.add(user_session)
    db.commit()

    return db.get(User, user_session.user_id)


def delete_session_by_token(db: Session, raw_token: str) -> None:
    token_hash = hash_session_token(raw_token)
    user_session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if not user_session:
        return

    db.delete(user_session)
    db.commit()
