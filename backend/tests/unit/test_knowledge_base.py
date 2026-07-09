import pytest
from app.models.models import KnowledgeDocument, User
from app.services.knowledge_service import KnowledgeBaseService
from app.core.security import hash_password

@pytest.fixture
def auth_headers_admin(client, db_session):
    user = db_session.query(User).filter(User.email == "admin@sentinelflow.ai").first()
    if not user:
        user = User(
            email="admin@sentinelflow.ai",
            hashed_password=hash_password("adminpass"),
            full_name="Administrator",
            role="admin",
            is_active=True
        )
        db_session.add(user)
    else:
        user.hashed_password = hash_password("adminpass")
        user.full_name = "Administrator"
    db_session.commit()
    db_session.refresh(user)

    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@sentinelflow.ai",
        "password": "adminpass"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_knowledge_text_extraction():
    # TXT Format
    txt_content = b"Memory leak troubleshooting steps"
    res = KnowledgeBaseService.extract_text("playbook.txt", txt_content)
    assert "Memory leak" in res

    # XML docx fallback
    docx_content = b"Mock zip archive payload"
    res = KnowledgeBaseService.extract_text("guide.docx", docx_content)
    assert "docx" in res.lower() or "extraction" in res.lower()

def test_create_and_approve_document(client, db_session, auth_headers_admin):
    doc = KnowledgeBaseService.create_document(
        db=db_session,
        title="Seeding playbook",
        filename="seed.md",
        category="playbooks",
        subcategory="kubernetes",
        tags="oom,restart",
        author="Admin",
        content="Step 1: Check pod memory metrics. Step 2: Restart container."
    )
    assert doc.id is not None
    assert doc.status == "draft"

    resp = client.post(f"/api/v1/knowledge/documents/{doc.id}/approve", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["approved_by"] == "Administrator"

def test_list_and_search_documents(client, db_session, auth_headers_admin):
    # Create its own document first to guarantee presence
    doc = KnowledgeBaseService.create_document(
        db=db_session,
        title="List testing playbook",
        filename="list_test.md",
        category="playbooks",
        subcategory="kubernetes",
        tags="oom,restart",
        author="Admin",
        content="Testing content here."
    )
    db_session.commit()

    resp = client.get("/api/v1/knowledge/documents", headers=auth_headers_admin)
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) >= 1
    assert any(d["title"] == "List testing playbook" for d in docs)

    # Verify search endpoint returns successfully
    search_resp = client.get("/api/v1/knowledge/search?q=testing&category=playbooks", headers=auth_headers_admin)
    assert search_resp.status_code == 200
    hits = search_resp.json()
    assert isinstance(hits, list)
