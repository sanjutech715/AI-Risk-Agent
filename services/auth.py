"""
utils/auth.py
─────────────
Authentication utilities for JWT tokens and API keys.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from core.database import get_db_session
from core.models import APIKey

logger = logging.getLogger(__name__)

# ── OAuth2 Scheme ─────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

# ── Password Hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _hash_api_key(api_key: str) -> str:
    """Create a deterministic HMAC-SHA256 fingerprint for an API key."""
    secret = settings.secret_key.encode("utf-8")
    return hmac.new(secret, api_key.encode("utf-8"), hashlib.sha256).hexdigest()


# ── JWT Token Management ──────────────────────────────────────────────────────
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


# ── API Key Management ────────────────────────────────────────────────────────
async def verify_api_key(api_key: str) -> Optional[APIKey]:
    """Verify API key against database."""
    if not settings.enable_authentication:
        return None

    # Check if key is in configured list (simple mode)
    if api_key in settings.api_keys:
        # Create a mock APIKey object for simple mode
        class MockAPIKey:
            def __init__(self, key_id: str):
                self.id = key_id
                self.name = f"configured-key-{key_id[:8]}"
                self.is_active = True
                self.permissions = ["read", "write"]
        return MockAPIKey(api_key)

    # Check database (advanced mode)
    try:
        async with get_db_session() as session:
            key_hash = _hash_api_key(api_key)

            result = await session.execute(
                "SELECT * FROM api_keys WHERE key_hash = :key_hash AND is_active = true",
                {"key_hash": key_hash}
            )
            row = result.first()

            if row:
                return APIKey(**row._asdict())
    except Exception as e:
        logger.error(f"API key verification error: {e}")

    return None


async def create_api_key(name: str, permissions: list = None) -> tuple[str, APIKey]:
    """Create a new API key."""
    if permissions is None:
        permissions = ["read", "write"]

    # Generate a random key
    import secrets
    api_key = secrets.token_urlsafe(32)
    key_hash = _hash_api_key(api_key)

    api_key_obj = APIKey(
        key_hash=key_hash,
        name=name,
        permissions=permissions,
        is_active=True
    )

    try:
        async with get_db_session() as session:
            session.add(api_key_obj)
            await session.commit()
            await session.refresh(api_key_obj)
            return api_key, api_key_obj
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise


# ── Authentication Middleware Helpers ─────────────────────────────────────────
def get_token_from_header(authorization: str) -> Optional[str]:
    """Extract token from Authorization header."""
    if not authorization.startswith("Bearer "):
        return None
    return authorization[7:]


def get_api_key_from_header(headers: Dict[str, str]) -> Optional[str]:
    """Extract API key from headers."""
    return headers.get(settings.api_key_header)