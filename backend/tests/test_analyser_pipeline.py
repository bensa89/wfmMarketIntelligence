import pytest
from unittest.mock import MagicMock, patch
from app.analyser.pipeline import _build_context_dict, analyse_document
from app.models.context import InternalCompanyContext


def _make_ctx(**kwargs):
    ctx = MagicMock(spec=InternalCompanyContext)
    ctx.company_name = kwargs.get("company_name", "Acme")
    ctx.short_description = kwargs.get("short_description", "A company")
    ctx.target_industries = kwargs.get("target_industries", ["HR"])
    ctx.target_segments = kwargs.get("target_segments", [])
    ctx.core_capabilities = kwargs.get("core_capabilities", [])
    ctx.strategic_priorities = kwargs.get("strategic_priorities", [])
    ctx.differentiators = kwargs.get("differentiators", [])
    ctx.relevant_competitive_areas = kwargs.get("relevant_competitive_areas", [])
    ctx.non_focus_areas = kwargs.get("non_focus_areas", [])
    return ctx


def test_build_context_dict_with_record():
    ctx = _make_ctx(company_name="TestCo", target_industries=["Retail"])
    result = _build_context_dict(ctx)
    assert result["company_name"] == "TestCo"
    assert result["target_industries"] == ["Retail"]


def test_build_context_dict_with_none():
    result = _build_context_dict(None)
    assert result == {}


def test_analyse_document_uses_preloaded_context(db_session):
    """When preloaded_context is passed, no DB query for InternalCompanyContext."""
    from app.models.document import Document
    from datetime import datetime, timezone

    doc = Document(
        source_id="src-1",
        url="https://example.com/article",
        content_markdown="word " * 60,
        content_hash="abc123",
        crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.commit()

    preloaded = {"company_name": "Preloaded Co", "target_industries": ["SaaS"]}

    with patch("app.analyser.pipeline.call_llm", return_value='{"signal_type": "product_update", "title": "T", "topic": "X", "summary": "S", "why_it_matters": "W", "relevance_score": 0.1, "confidence_score": 0.9, "published_at": null}'):
        with patch.object(db_session, "query") as mock_query:
            # Should NOT query InternalCompanyContext
            analyse_document(doc, "company-1", db_session, preloaded_context=preloaded)
            queried_models = [call.args[0] for call in mock_query.call_args_list]
            from app.models.context import InternalCompanyContext
            assert InternalCompanyContext not in queried_models
