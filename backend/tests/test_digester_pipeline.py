import json
import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType
from app.models.digest import WeeklyDigest
from app.digester.pipeline import generate_digest


@pytest.fixture
def seeded(db_session):
    company = Company(name="Acme", slug="acme", type=CompanyType.competitor)
    db_session.add(company)
    db_session.commit()

    source = Source(
        company_id=company.id, url="https://acme.com", source_type=SourceType.news
    )
    db_session.add(source)
    db_session.commit()

    doc = Document(
        source_id=source.id,
        url="https://acme.com/news/1",
        title="Article 1",
        content_hash="h1",
    )
    db_session.add(doc)
    db_session.commit()

    today = date.today()
    signal = Signal(
        document_id=doc.id,
        company_id=company.id,
        title="Acme AI Feature",
        signal_type=SignalType.ai_announcement,
        relevance_score=0.9,
        created_at=datetime.combine(today, datetime.min.time()).replace(
            tzinfo=timezone.utc
        ),
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def test_generate_digest_creates_record(db_session, seeded):
    signal = seeded

    def fake_llm(prompt: str, max_tokens: int = 1024) -> str:
        if "selected_items" in prompt:
            return json.dumps(
                {
                    "selected_items": [
                        {
                            "signal_id": signal.id,
                            "narrative": "Big move.",
                            "implication_for_us": "React now.",
                        }
                    ]
                }
            )
        return json.dumps({"summary": "A big week."})

    with patch("app.digester.curator.call_llm", side_effect=fake_llm):
        digest = generate_digest(db_session)

    assert digest.id is not None
    assert digest.week_start is not None
    assert digest.week_end is not None
    assert isinstance(digest.sections, list)


def test_generate_digest_sections_contain_item(db_session, seeded):
    signal = seeded

    def fake_llm(prompt: str, max_tokens: int = 1024) -> str:
        if "selected_items" in prompt:
            return json.dumps(
                {
                    "selected_items": [
                        {
                            "signal_id": signal.id,
                            "narrative": "Big move.",
                            "implication_for_us": "React now.",
                        }
                    ]
                }
            )
        return json.dumps({"summary": "A big week."})

    with patch("app.digester.curator.call_llm", side_effect=fake_llm):
        digest = generate_digest(db_session)

    all_items = [
        item for section in digest.sections for item in section.get("items", [])
    ]
    assert any(item["signal_id"] == signal.id for item in all_items)


def test_generate_digest_summary_set(db_session, seeded):
    signal = seeded

    def fake_llm(prompt: str, max_tokens: int = 1024) -> str:
        if "selected_items" in prompt:
            return json.dumps(
                {
                    "selected_items": [
                        {
                            "signal_id": signal.id,
                            "narrative": "Big move.",
                            "implication_for_us": "React now.",
                        }
                    ]
                }
            )
        return json.dumps({"summary": "A big week."})

    with patch("app.digester.curator.call_llm", side_effect=fake_llm):
        digest = generate_digest(db_session)

    assert digest.summary == "A big week."


def test_generate_digest_empty_week_produces_no_sections(db_session):
    with patch(
        "app.digester.curator.call_llm", return_value=json.dumps({"selected_items": []})
    ):
        digest = generate_digest(db_session)

    assert digest.sections == []
