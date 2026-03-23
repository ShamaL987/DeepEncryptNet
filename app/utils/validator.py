import secrets
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.user_api import _build_api_token_hash
from app.database.models import User


def validate_ingest_api_token(db: Session, raw_token: str):
    token = (raw_token or "").strip()

    if not token or "_" not in token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token.",
        )

    token_prefix = token.rsplit("_", 1)[0]
    token_hash = _build_api_token_hash(token)

    current_user = (
        db.query(User)
        .filter(User.api_token_prefix == token_prefix)
        .first()
    )

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token.",
        )

    if current_user.api_token_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token is not configured for this user.",
        )

    if getattr(current_user, "is_token_revoked", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token has been revoked.",
        )

    if not secrets.compare_digest(current_user.api_token_hash, token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token.",
        )

    return current_user