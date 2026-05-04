"""Authentication router for user management and token operations."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from services.auth import get_token_from_header, oauth2_scheme
from services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user as create_user_in_store,
    get_current_active_user,
    get_current_user,
    User,
)
from config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model."""
    username: str | None = None


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False


async def get_authenticated_user(token: str = Depends(oauth2_scheme)) -> User:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_current_user(token)
    return await get_current_active_user(user)


async def require_admin_user(token: str = Depends(oauth2_scheme)) -> Optional[User]:
    if not settings.enable_authentication:
        return None

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user = await get_current_user(token)
    active_user = await get_current_active_user(current_user)
    if not active_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return active_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """Authenticate user and return access token."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.jwt_expiration_hours * 60)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_authenticated_user),
) -> User:
    """Get current user information."""
    return current_user


@router.post("/users", response_model=User)
async def create_user_endpoint(
    user: UserCreate,
    current_user: Optional[User] = Depends(require_admin_user),
) -> User:
    """Create a new user."""
    return create_user_in_store(
        username=user.username,
        password=user.password,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
    )