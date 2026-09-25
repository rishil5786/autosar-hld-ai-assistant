"""
AUTOSAR HLD AI - Security & RBAC Utilities
Password hashing, JWT tokens, OAuth2 dependencies, and Role-Based Access Control.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Callable
import hashlib
import hmac
import secrets
import re
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.utils.config import settings
from app.backend.database import get_db
from app.backend.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using salted SHA-256 (standard & secure without passlib wrap bugs)."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its PBKDF2-SHA256 hash."""
    try:
        if "$" not in hashed_password:
            return False
        salt, key_hex = hashed_password.split("$", 1)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    FastAPI dependency to extract and authenticate current user from Bearer JWT.
    Throws 401 if missing or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub") or payload.get("username")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    """
    Extract current user if valid token provided; returns None otherwise.
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if not payload:
            return None
        username = payload.get("sub") or payload.get("username")
        if not username:
            return None
        return db.query(User).filter(User.username == username, User.is_active == True).first()
    except Exception:
        return None


def require_role(allowed_roles: List[str]) -> Callable:
    """
    RBAC dependency factory. Ensures current user possesses one of the allowed roles.
    Example: Depends(require_role(["admin", "architect", "engineer"]))
    """
    allowed_lower = [r.lower() for r in allowed_roles]

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = (current_user.role or "").lower()
        if "admin" in allowed_lower or user_role in allowed_lower:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: requires one of the following roles: {allowed_roles}. Current role: '{current_user.role}'."
        )

    return role_checker


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.
    """
    filename = filename.replace("/", "_").replace("\\", "_")
    filename = re.sub(r'[^\w\s\-.]', '', filename)
    filename = filename.lstrip(".")
    if len(filename) > 200:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:195] + ("." + ext if ext else "")
    return filename or "unnamed_file"


def validate_file_upload(filename: str, file_size: int) -> tuple[bool, str]:
    """
    Validate an uploaded file.
    """
    allowed_extensions = {".pdf"}
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_extensions:
        return False, f"Invalid file type '{ext}'. Only PDF files are allowed."

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        return False, f"File too large ({file_size / 1024 / 1024:.1f}MB). Maximum is {settings.MAX_UPLOAD_SIZE_MB}MB."

    if file_size == 0:
        return False, "File is empty."

    return True, ""
