import io

import pymupdf
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from tests.test_auth import login_headers


@pytest.fixture()
def client(db):
    return TestClient(app)


def pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


CV = "Ivan Petrov. Backend developer. Skills: Python, FastAPI, PostgreSQL, Docker, Git"


def upload(client, headers, data, name="cv.pdf"):
    return client.post("/resumes", files={"file": (name, data, "application/octet-stream")}, headers=headers)


def test_upload_get_delete(client):
    h = login_headers(client)
    assert client.get("/resumes/me", headers=h).status_code == 404
    r = upload(client, h, pdf_bytes(CV))
    assert r.status_code == 201
    body = r.json()
    assert body["original_filename"] == "cv.pdf" and "FastAPI" in body["preview"] and body["char_count"] > 30
    assert client.get("/resumes/me", headers=h).json()["id"] == body["id"]
    assert client.delete("/resumes/me", headers=h).status_code == 204
    assert client.get("/resumes/me", headers=h).status_code == 404


def test_new_upload_replaces_old_one(client):
    h = login_headers(client)
    upload(client, h, pdf_bytes(CV))
    second = upload(client, h, (CV + " Kubernetes extra line").encode(), "cv.txt").json()
    assert client.get("/resumes/me", headers=h).json()["id"] == second["id"]


def test_users_cannot_see_each_others_resumes(client):
    a = login_headers(client, "a@example.com")
    b = login_headers(client, "b@example.com")
    upload(client, a, pdf_bytes(CV))
    assert client.get("/resumes/me", headers=b).status_code == 404  
    assert client.delete("/resumes/me", headers=b).status_code == 204
    assert client.get("/resumes/me", headers=a).status_code == 200  


def test_bad_files_get_clear_errors(client):
    h = login_headers(client)
    assert upload(client, h, b"", "cv.txt").status_code == 422
    assert upload(client, h, b"PK\x03\x04docx", "cv.docx").status_code == 422
    assert upload(client, h, b"%PDF-1.4 broken", "cv.pdf").status_code == 422


def test_too_large_file_rejected(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_resume_bytes", 100)
    h = login_headers(client)
    assert upload(client, h, b"x" * 101, "cv.txt").status_code == 413


def test_upload_requires_login(client):
    assert upload(client, {}, pdf_bytes(CV)).status_code == 401


def docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_docx_upload_and_language_detection(client):
    h = login_headers(client)
    body = upload(
        client,
        h,
        docx_bytes(
            "Python-разработчик с опытом работы три года: разрабатывал веб-сервисы на FastAPI, PostgreSQL, Docker"
        ),
        "cv.docx",
    ).json()
    assert body["language"] == "ru" and "FastAPI" in body["preview"]
    english = upload(client, h, pdf_bytes(CV)).json()
    assert english["language"] == "en"


def test_paste_text_and_read_full_text(client):
    h = login_headers(client)
    long_text = "Backend developer. " + "Python FastAPI PostgreSQL Docker. " * 60
    r = client.post("/resumes/text", json={"text": long_text}, headers=h)
    assert r.status_code == 201 and r.json()["original_filename"] == "Вставленный текст"
    assert len(r.json()["preview"]) == 500 < r.json()["char_count"]
    full = client.get("/resumes/me/text", headers=h).json()["text"]
    assert full.startswith("Backend developer.") and len(full) == r.json()["char_count"]


def test_paste_text_validation(client):
    h = login_headers(client)
    assert client.post("/resumes/text", json={"text": "short"}, headers=h).status_code == 422
    assert client.post("/resumes/text", json={"text": ""}, headers=h).status_code == 422
    assert client.post("/resumes/text", json={"text": CV}).status_code == 401
    assert client.get("/resumes/me/text", headers=h).status_code == 404


def test_full_text_is_private(client):
    a = login_headers(client, "a@example.com")
    b = login_headers(client, "b@example.com")
    upload(client, a, pdf_bytes(CV))
    assert client.get("/resumes/me/text", headers=a).status_code == 200
    assert client.get("/resumes/me/text", headers=b).status_code == 404
