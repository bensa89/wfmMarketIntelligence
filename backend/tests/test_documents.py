import pytest
from app.models.document import Document


@pytest.fixture
def seed_document(db_session):
    from app.models.company import Company, CompanyType
    from app.models.source import Source, SourceType

    company = Company(name="ATOSS", slug="atoss-doc", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()
    source = Source(
        company_id=company.id, url="https://atoss.com/docs", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()
    doc = Document(
        source_id=source.id,
        url="https://atoss.com/docs/post-1",
        title="Test Post",
        content_markdown="## Hello",
        content_hash="abc123def456",
    )
    db_session.add(doc)
    db_session.commit()
    return doc


def test_list_documents(client, seed_document):
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_document_by_id(client, seed_document):
    response = client.get(f"/api/documents/{seed_document.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Post"
    assert response.json()["content_markdown"] == "## Hello"


def test_get_nonexistent_document(client):
    response = client.get("/api/documents/nonexistent-id")
    assert response.status_code == 404


def test_filter_documents_by_source(client, seed_document):
    response = client.get(f"/api/documents?source_id={seed_document.source_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["source_id"] == seed_document.source_id
