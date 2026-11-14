from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import User
from app.schemas.api import ChangePasswordIn, DeleteAccountIn, UpdateProfileIn, UserOut
from app.security import hash_password, verify_password

router = APIRouter(prefix="/me", tags=["account"])


@router.patch("", response_model=UserOut)
def update_profile(body: UpdateProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = " ".join(body.full_name.split()) if body.full_name else ""
    user.full_name = name or None
    db.commit()
    db.refresh(user)
    return user


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный текущий пароль")
    if body.new_password == body.current_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Новый пароль совпадает с текущим")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(body: DeleteAccountIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Удаление аккаунта вместе с резюме, предпочтениями, ссылками и уведомлениями (каскад в БД). Нужен пароль."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный пароль")
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
