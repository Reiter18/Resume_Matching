from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import User
from app.ratelimit import LoginLimiter, RateLimited, get_login_limiter
from app.schemas.api import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


def _norm_email(email: str) -> str:
    return email.strip().lower()


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = _norm_email(body.email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже есть")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже есть") from None
    return user


@router.post("/auth/login", response_model=TokenOut)
def login(
    body: LoginIn,
    request: Request,
    db: Session = Depends(get_db),
    limiter: LoginLimiter = Depends(get_login_limiter),
):
    ip = request.client.host if request.client else "unknown"
    email = _norm_email(body.email)
    try:
        limiter.check(ip, email)
    except RateLimited as e:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Слишком много неудачных попыток входа. Повторите через {-(-e.retry_after // 60)} мин.",
            headers={"Retry-After": str(e.retry_after)},
        ) from None
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        limiter.failure(ip, email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    limiter.success(ip, email)
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
