from datetime import datetime, timedelta, timezone

import pytest

from app.sharing import build_public_payload, hash_token, is_active, new_token, validate_fields

MATCHES = [
    {"title": "Dev", "company": "Acme", "url": "https://x/1", "score": 0.9, "breakdown": {"skills": 0.9},
     "resume_text": "СЕКРЕТ", "email": "a@b.c"},
    {"title": "Low", "company": "B", "url": "https://x/2", "score": 0.4, "breakdown": {}},
]


def test_token_is_random_and_only_hash_is_comparable():
    t1, t2 = new_token(), new_token()
    assert t1 != t2 and len(t1) >= 40
    assert hash_token(t1) == hash_token(t1) != hash_token(t2) and t1 not in hash_token(t1)


def test_cannot_share_resume_or_contacts():
    with pytest.raises(ValueError):
        validate_fields(["matches", "resume_text"])
    with pytest.raises(ValueError):
        validate_fields(["email"])
    assert validate_fields([]) == ["matches"]


def test_payload_never_leaks_private_fields():
    out = build_public_payload(MATCHES, ["matches", "score_breakdown", "resume_text", "email"])
    text = str(out)
    assert "СЕКРЕТ" not in text and "a@b.c" not in text
    assert "breakdown" in out["matches"][0]


def test_breakdown_hidden_unless_allowed_and_min_score_filters():
    out = build_public_payload(MATCHES, ["matches"], min_score=0.7)
    assert len(out["matches"]) == 1 and "breakdown" not in out["matches"][0]
    assert build_public_payload(MATCHES, ["skills"]) == {}


def test_expiry_and_revoke():
    now = datetime.now(timezone.utc)
    assert is_active(None, None)
    assert not is_active(now - timedelta(seconds=1), None, now)
    assert not is_active(None, now)
