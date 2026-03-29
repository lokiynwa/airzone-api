from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.security import generate_session_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.auth import (
    AuthenticationError,
    DuplicateUserError,
    authenticate_user,
    create_session,
    create_user,
    delete_session_by_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DBSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _set_session_cookie(
    response: Response,
    settings: Settings,
    token: str,
    expires_at: datetime,
) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        expires=expires_at,
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def _build_auth_response(user: User) -> AuthResponse:
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    db: DBSession,
    settings: AppSettings,
) -> AuthResponse:
    try:
        user = create_user(db, email=payload.email, password=payload.password)
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from exc

    raw_token = generate_session_token()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    create_session(db, user=user, raw_token=raw_token, expires_at=expires_at)
    _set_session_cookie(response, settings, raw_token, expires_at)

    return _build_auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: DBSession,
    settings: AppSettings,
) -> AuthResponse:
    try:
        user = authenticate_user(db, email=payload.email, password=payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc

    raw_token = generate_session_token()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    create_session(db, user=user, raw_token=raw_token, expires_at=expires_at)
    _set_session_cookie(response, settings, raw_token, expires_at)

    return _build_auth_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: DBSession,
    settings: AppSettings,
) -> Response:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        delete_session_by_token(db, raw_token)

    _clear_session_cookie(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthResponse)
def me(current_user: CurrentUser) -> AuthResponse:
    return _build_auth_response(current_user)
