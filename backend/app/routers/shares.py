from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import ShareLink, User
from app.schemas.api import ShareCreate, ShareCreated, ShareOut
from app.sharing import hash_token, is_active, new_token

router = APIRouter(prefix="/shares", tags=["shares"])
MAX_ACTIVE = 20


def _out(link: ShareLink) -> dict:
    return dict(
        id=link.id, title=link.title, allowed_fields=link.allowed_fields,
        min_score=None if link.min_score is None else round(link.min_score * 100),
        expires_at=link.expires_at, revoked_at=link.revoked_at, created_at=link.created_at,
        view_count=link.view_count, last_viewed_at=link.last_viewed_at, active=is_active(link.expires_at, link.revoked_at),
    )  # fmt: skip


def _mine(db: Session, user: User) -> list[ShareLink]:
    return list(
        db.scalars(
            select(ShareLink)
            .where(ShareLink.user_id == user.id)
            .order_by(ShareLink.created_at.desc(), ShareLink.id.desc())
        )
    )


@router.post("", response_model=ShareCreated, status_code=201)
def create_share(body: ShareCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    if sum(is_active(link.expires_at, link.revoked_at) for link in _mine(db, user)) >= MAX_ACTIVE:
        raise HTTPException(409, "Слишком много активных ссылок: отзовите ненужные")
    token = new_token()
    link = ShareLink(
        user_id=user.id, token_hash=hash_token(token), title=body.title, allowed_fields=body.allowed_fields,
        min_score=None if body.min_score is None else body.min_score / 100,
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_in_days),
    )  # fmt: skip
    db.add(link)
    db.commit()
    db.refresh(link)
    return {**_out(link), "token": token}  


@router.get("", response_model=list[ShareOut])
def list_shares(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_out(link) for link in _mine(db, user)]


@router.delete("/{link_id}", response_model=ShareOut)
def revoke_share(link_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    link = db.scalar(select(ShareLink).where(ShareLink.id == link_id, ShareLink.user_id == user.id).with_for_update())
    if link is None:
        raise HTTPException(404, "Ссылка не найдена")
    if link.revoked_at is None:
        link.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(link)
    return _out(link)
