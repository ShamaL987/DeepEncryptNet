from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import bcrypt
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import get_settings_manager_from_request
from app.database.db import get_db
from app.database.models import User

router = APIRouter(prefix="/user", tags=["Users"])


class AdminCreateUserRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    identifier: str
    password: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_jwt_secret(request: Request) -> str:
    return get_settings_manager_from_request(request).jwt_secret_key


def _get_admin_bootstrap_token(request: Request) -> str:
    return get_settings_manager_from_request(request).admin_bootstrap_token


def _get_jwt_algorithm(request: Request) -> str:
    return get_settings_manager_from_request(request).jwt_algorithm


def _get_jwt_access_token_expire_minutes(request: Request) -> int:
    return get_settings_manager_from_request(request).jwt_access_token_expire_minutes


def _get_api_token_encryption_key(request: Request) -> str:
    return get_settings_manager_from_request(request).api_token_encryption_key


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _build_api_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _get_api_token_cipher(request: Request) -> Fernet:
    return Fernet(_get_api_token_encryption_key(request).encode())


def _encrypt_api_token(raw_token: str, request: Request) -> str:
    return _get_api_token_cipher(request).encrypt(raw_token.encode("utf-8")).decode("utf-8")


def _decrypt_api_token(encrypted_token: str, request: Request) -> str:
    return _get_api_token_cipher(request).decrypt(encrypted_token.encode("utf-8")).decode("utf-8")


def _generate_api_token() -> tuple[str, str, str]:
    token_prefix = f"den_{secrets.token_hex(4)}"
    token_secret = secrets.token_hex(32)
    raw_token = f"{token_prefix}_{token_secret}"
    token_hash = _build_api_token_hash(raw_token)
    return raw_token, token_prefix, token_hash


def _create_access_token(user: User, request: Request) -> str:
    expire_at = _utc_now() + timedelta(minutes=_get_jwt_access_token_expire_minutes(request))
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
        "exp": expire_at,
    }
    return jwt.encode(
        payload,
        _get_jwt_secret(request),
        algorithm=_get_jwt_algorithm(request),
    )


def _decode_access_token(token: str, request: Request) -> dict:
    try:
        return jwt.decode(
            token,
            _get_jwt_secret(request),
            algorithms=[_get_jwt_algorithm(request)],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    return token


def _get_current_user(
    db: Session,
    authorization: Optional[str],
    request: Request,
) -> User:
    bearer_token = _extract_bearer_token(authorization)
    payload = _decode_access_token(bearer_token, request)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token payload",
        )

    user = db.query(User).filter(User.id == str(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active or does not exist",
        )

    return user


def get_user_by_external_token(
    db: Session,
    raw_token: str,
) -> User:
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token",
        )

    if "_" not in raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token format",
        )

    token_prefix = raw_token.rsplit("_", 1)[0]
    user = db.query(User).filter(User.api_token_prefix == token_prefix).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    if user.is_token_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token is revoked",
        )

    if not user.api_token_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token is not configured",
        )

    incoming_hash = _build_api_token_hash(raw_token)
    if incoming_hash != user.api_token_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )

    return user


@router.post("/create")
def create_user(
    payload: AdminCreateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_admin_token: Optional[str] = Header(default=None),
):
    if x_admin_token != _get_admin_bootstrap_token(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    normalized_username = payload.username.strip()
    normalized_email = payload.email.strip().lower()

    existing_user = (
        db.query(User)
        .filter((User.username == normalized_username) | (User.email == normalized_email))
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with the same username or email already exists",
        )

    new_user = User(
        id=str(uuid4()),
        username=normalized_username,
        email=normalized_email,
        password_hash=_hash_password(payload.password),
        is_active=True,
    )

    new_user.save(db=db)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "is_active": new_user.is_active,
        "api_token_generated": False,
    }


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    normalized_identifier = payload.identifier.strip()

    user = (
        db.query(User)
        .filter((User.email == normalized_identifier.lower()) | (User.username == normalized_identifier))
        .first()
    )

    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    access_token = _create_access_token(user, request)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": _get_jwt_access_token_expire_minutes(request) * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    }


@router.get("/me")
def get_current_logged_in_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    current_user = _get_current_user(
        db=db,
        authorization=authorization,
        request=request,
    )

    readable_api_token = None
    if current_user.api_token_encrypted and not current_user.is_token_revoked:
        readable_api_token = _decrypt_api_token(current_user.api_token_encrypted, request)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "api_token_generated": bool(current_user.api_token_hash),
        "is_token_revoked": bool(current_user.is_token_revoked),
        "token_created_at": current_user.token_created_at.isoformat() if current_user.token_created_at else None,
        "token_revoked_at": current_user.token_revoked_at.isoformat() if current_user.token_revoked_at else None,
        "api_token": readable_api_token,
    }


@router.post("/auth/generate")
def generate_api_token_for_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    current_user = _get_current_user(
        db=db,
        authorization=authorization,
        request=request,
    )

    replaced_existing = bool(current_user.api_token_hash)
    raw_token, token_prefix, token_hash = _generate_api_token()

    current_user.api_token_prefix = token_prefix
    current_user.api_token_hash = token_hash
    current_user.api_token_encrypted = _encrypt_api_token(raw_token, request)
    current_user.is_token_revoked = False
    current_user.token_created_at = _utc_now()
    current_user.token_revoked_at = None
    current_user.save(db=db)

    return {
        "token": raw_token,
        "token_prefix": token_prefix,
        "generated_at": current_user.token_created_at.isoformat() if current_user.token_created_at else None,
        "replaced_existing": replaced_existing,
    }


@router.post("/auth/revoke")
def revoke_api_token_for_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    current_user = _get_current_user(
        db=db,
        authorization=authorization,
        request=request,
    )

    if not current_user.api_token_hash:
        return {
            "revoked": False,
            "message": "No API token exists for this user",
        }

    current_user.is_token_revoked = True
    current_user.token_revoked_at = _utc_now()
    current_user.api_token_hash = None
    current_user.api_token_prefix = None
    current_user.api_token_encrypted = None
    current_user.save(db=db)

    return {
        "revoked": True,
        "revoked_at": current_user.token_revoked_at.isoformat() if current_user.token_revoked_at else None,
    }


@router.get("/external/validate")
def validate_external_api_token(
    request: Request,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
):
    raw_token = x_api_key
    if not raw_token and authorization:
        raw_token = _extract_bearer_token(authorization)

    current_user = get_user_by_external_token(db=db, raw_token=raw_token)

    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        },
    }