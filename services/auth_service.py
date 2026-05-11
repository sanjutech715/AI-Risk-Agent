"""Authentication service for user management and token operations."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel


def _load_jose():
    try:
        from jose import jwt, JWTError
        return jwt, JWTError
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing required dependency 'python-jose[cryptography]'. "
            "Install it in the active environment or activate the project's virtualenv."
        ) from exc

from config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    """User model for authentication."""

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    is_admin: bool = False


USER_STORE: Dict[str, Dict[str, Any]] = {}


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user(username: str) -> Optional[User]:
    user_data = USER_STORE.get(username)
    if not user_data:
        return None

    return User(
        username=user_data["username"],
        email=user_data.get("email"),
        full_name=user_data.get("full_name"),
        disabled=user_data.get("disabled", False),
        is_admin=user_data.get("is_admin", False),
    )


def create_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    is_admin: bool = False,
) -> User:
    if username in USER_STORE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    USER_STORE[username] = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "disabled": False,
        "is_admin": is_admin,
        "hashed_password": _hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
    }

    return get_user(username)


def authenticate_user(username: str, password: str) -> Optional[User]:
    user_data = USER_STORE.get(username)
    if not user_data:
        return None

    if not _verify_password(password, user_data["hashed_password"]):
        return None

    return get_user(username)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    jwt, _ = _load_jose()
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return username."""
    try:
        jwt, JWTError = _load_jose()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        username: Optional[str] = payload.get("sub")
        return username
    except JWTError:
        return None


async def get_current_user(token: str) -> Optional[User]:
    """Get current user from token."""
    username = verify_token(token)
    if username is None:
        return None
    return get_user(username)


async def get_current_active_user(current_user: Optional[User]) -> User:
    """Get current active user."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user