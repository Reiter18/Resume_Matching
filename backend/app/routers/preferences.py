from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import SearchPreferences, User
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
    return row
