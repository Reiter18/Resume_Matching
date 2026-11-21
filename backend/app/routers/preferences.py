from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import tasks
from app.deps import get_current_user, get_db
from app.models import Resume, SearchPreferences, User
from app.schemas.api import Preferences

router = APIRouter(prefix="/me/preferences", tags=["preferences"])


@router.get("", response_model=Preferences)
def get_preferences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.get(SearchPreferences, user.id) or Preferences()


@router.put("", response_model=Preferences)
def save_preferences(body: Preferences, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(SearchPreferences, user.id) or SearchPreferences(user_id=user.id)
    for field, value in body.model_dump().items():
        setattr(row, field, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    resume_id = db.scalar(select(Resume.id).where(Resume.user_id == user.id))
    if resume_id:
        tasks.enqueue_match(resume_id)  
    return row
