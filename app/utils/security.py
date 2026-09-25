"""
AUTOSAR HLD AI - Security Utilities
Password hashing, JWT tokens, and security helpers.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import hmac
import secrets
from jose import JWTError, jwt

from app.utils.config import settings


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


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.
    """
    import re
    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\s\-.]', '', filename)
    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")
    # Limit length
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
