from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, get_db
from app.models import Resume, User
from app.resume_parser import ResumeError, detect_language, extract_text, finalize
from app.schemas.api import ResumeFullTextOut, ResumeOut, ResumeTextIn

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _out(r: Resume) -> ResumeOut:
    return ResumeOut(
        id=r.id, original_filename=r.original_filename, char_count=len(r.raw_text), language=r.language,
        preview=r.raw_text[:500], skills=r.skills or [], created_at=r.created_at,
    )  


def _replace_resume(db: Session, user: User, filename: str, text: str) -> Resume:
    """У пользователя одно резюме: новое заменяет старое (старый текст не копится в базе)."""
    db.execute(delete(Resume).where(Resume.user_id == user.id))
    resume = Resume(
        user_id=user.id, original_filename=filename[:255], raw_text=text, skills=[], language=detect_language(text)
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def _my_resume(db: Session, user: User) -> Resume:
    resume = db.scalar(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id.desc()))
    if resume is None:
        raise HTTPException(404, "Резюме не загружено")
    return resume


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def upload_resume(file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Загрузка файла: PDF, DOCX или TXT до 5 МБ."""
    data = file.file.read(settings.max_resume_bytes + 1)
    if len(data) > settings.max_resume_bytes:
        raise HTTPException(413, "Файл больше 5 МБ")
    try:
        text = extract_text(file.filename or "", data)
    except ResumeError as e:
        raise HTTPException(422, str(e)) from e
    return _out(_replace_resume(db, user, file.filename or "", text))


@router.post("/text", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def paste_resume(body: ResumeTextIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Резюме, вставленное текстом (без файла)."""
    try:
        text = finalize(body.text)
    except ResumeError as e:
        raise HTTPException(422, str(e)) from e
    return _out(_replace_resume(db, user, "Вставленный текст", text))


@router.get("/me", response_model=ResumeOut)
def my_resume(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(_my_resume(db, user))


@router.get("/me/text", response_model=ResumeFullTextOut)
def my_resume_text(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Полный извлечённый текст: пользователь может проверить, что парсер понял резюме правильно."""
    return ResumeFullTextOut(text=_my_resume(db, user).raw_text)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_resume(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.execute(delete(Resume).where(Resume.user_id == user.id))
    db.commit()
