from typing import Iterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    user_id = decode_access_token(creds.credentials)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise unauthorized
    return user
