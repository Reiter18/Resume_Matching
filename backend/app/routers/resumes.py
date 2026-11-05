from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, get_db
from app.models import Resume, User
from app.resume_parser import ResumeError, detect_language, extract_text, finalize
from app.schemas.api import ResumeFullTextOut, ResumeOut, ResumeSkillsIn, ResumeTextIn
from app.skills import SkillDictionary

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _out(r: Resume, db: Session) -> ResumeOut:
    skills = r.skills or []
    _, unknown = SkillDictionary.load(db).normalize(skills) if skills else ([], [])
    return ResumeOut(
        id=r.id, original_filename=r.original_filename, char_count=len(r.raw_text), language=r.language,
        preview=r.raw_text[:500], skills=skills, unknown_skills=unknown, created_at=r.created_at,
    )  # fmt: skip


def _replace_resume(db: Session, user: User, filename: str, text: str) -> Resume:
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
    return _out(_replace_resume(db, user, file.filename or "", text), db)


@router.post("/text", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def paste_resume(body: ResumeTextIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        text = finalize(body.text)
    except ResumeError as e:
        raise HTTPException(422, str(e)) from e
    return _out(_replace_resume(db, user, "Вставленный текст", text), db)


@router.get("/me", response_model=ResumeOut)
def my_resume(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(_my_resume(db, user), db)


@router.put("/me/skills", response_model=ResumeOut)
def update_skills(body: ResumeSkillsIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = _my_resume(db, user)
    resume.skills, _ = SkillDictionary.load(db).normalize(body.skills)
    db.commit()
    db.refresh(resume)
    return _out(resume, db)


@router.get("/me/text", response_model=ResumeFullTextOut)
def my_resume_text(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ResumeFullTextOut(text=_my_resume(db, user).raw_text)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_resume(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.execute(delete(Resume).where(Resume.user_id == user.id))
    db.commit()
