from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config import settings
from app.models.company import Company
from app.models.context import InternalCompanyContext
from app.models.document import Document
from app.models.search_query import SearchQuery
from app.models.search_result import SearchResult, SearchResultStatus
from app.models.search_run import SearchRun, SearchRunStatus
from app.models.source import Source, SourceType
from app.models.source_candidate import SourceCandidate, SourceCandidateStatus
from app.analyser.pipeline import analyse_document
from app.crawler.extractor import extract_content
from app.crawler.fetcher import fetch_url
from app.searcher.client import search_tavily
from app.searcher.query_generator import (
    generate_queries_for_company,
    generate_trend_queries,
)


def _get_or_create_search_inbox_source(company: Company, db: Session) -> Source:
    inbox_url = f"search://{company.id}"
    source = db.query(Source).filter(Source.url == inbox_url).first()
    if not source:
        source = Source(
            company_id=company.id,
            url=inbox_url,
            label="Web Search Inbox",
            source_type=SourceType.news,
            is_active=False,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    return source


def _domain_has_active_source(domain: str, db: Session) -> bool:
    sources = db.query(Source).filter(Source.is_active == True).all()
    for s in sources:
        parsed = urlparse(s.url)
        if parsed.netloc.lstrip("www.") == domain:
            return True
    return False


def _domain_has_candidate(domain: str, db: Session) -> bool:
    return (
        db.query(SourceCandidate).filter(SourceCandidate.domain == domain).first()
        is not None
    )


def _get_context(db: Session) -> Dict:
    ctx = db.query(InternalCompanyContext).first()
    if not ctx:
        return {}
    return {
        "target_industries": ctx.target_industries or [],
        "target_segments": ctx.target_segments or [],
        "core_capabilities": ctx.core_capabilities or [],
        "strategic_priorities": ctx.strategic_priorities or [],
        "differentiators": ctx.differentiators or [],
        "relevant_competitive_areas": ctx.relevant_competitive_areas or [],
        "non_focus_areas": ctx.non_focus_areas or [],
    }


def _process_result(
    tavily_result,
    search_run: SearchRun,
    company: Company,
    inbox_source: Source,
    db: Session,
) -> SearchResult:
    # Create SearchResult record
    sr = SearchResult(
        search_run_id=search_run.id,
        title=tavily_result.title,
        url=tavily_result.url,
        domain=tavily_result.domain,
        snippet=tavily_result.snippet,
        relevance_score=tavily_result.score,
        processing_status=SearchResultStatus.pending,
    )
    db.add(sr)
    db.flush()

    # Skip low relevance
    if tavily_result.score < settings.search_relevance_threshold:
        sr.processing_status = SearchResultStatus.skipped
        db.commit()
        return sr

    # Check for existing document by URL
    existing_doc = db.query(Document).filter(Document.url == tavily_result.url).first()
    if existing_doc:
        sr.linked_document_id = existing_doc.id
        sr.processing_status = SearchResultStatus.fetched
        db.commit()
        return sr

    # Fetch and extract content
    fetch_result = fetch_url(tavily_result.url)
    if not fetch_result or not fetch_result.html:
        sr.processing_status = SearchResultStatus.error
        db.commit()
        return sr

    extraction = extract_content(fetch_result.html, fetch_result.final_url)

    # Check for duplicate by hash
    existing_hash = (
        db.query(Document)
        .filter(Document.content_hash == extraction.content_hash)
        .first()
    )
    if existing_hash:
        sr.linked_document_id = existing_hash.id
        sr.processing_status = SearchResultStatus.fetched
        db.commit()
        return sr

    # Create new document
    doc = Document(
        source_id=inbox_source.id,
        url=fetch_result.final_url,
        title=extraction.title,
        content_markdown=extraction.markdown,
        content_hash=extraction.content_hash,
        from_search=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Analyze document
    try:
        analyse_document(doc, company.id, db)
    except Exception:
        pass

    sr.linked_document_id = doc.id
    sr.processing_status = SearchResultStatus.fetched
    db.commit()

    # Create source candidate if new domain
    if not _domain_has_active_source(
        tavily_result.domain, db
    ) and not _domain_has_candidate(tavily_result.domain, db):
        candidate = SourceCandidate(
            url=tavily_result.url,
            domain=tavily_result.domain,
            title=tavily_result.title,
            snippet=tavily_result.snippet,
            found_via_query=search_run.query.query_text if search_run.query else None,
            company_id=company.id,
            source_type_guess=SourceType.news,
            relevance_score=tavily_result.score,
            status=SourceCandidateStatus.candidate,
        )
        db.add(candidate)
        db.commit()

    return sr


def run_search_for_company(company: Company, db: Session) -> Dict[str, Any]:
    context = _get_context(db)
    queries = generate_queries_for_company(
        company_name=company.name,
        company_type=company.type.value
        if hasattr(company.type, "value")
        else str(company.type),
        context=context,
    )

    inbox_source = _get_or_create_search_inbox_source(company, db)
    total_results = 0
    total_docs = 0

    for q in queries:
        sq = SearchQuery(
            query_text=q.query_text,
            company_id=company.id,
            search_intent=q.search_intent,
        )
        db.add(sq)
        db.commit()
        db.refresh(sq)

        run = SearchRun(search_query_id=sq.id, status=SearchRunStatus.running)
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            tavily_results = search_tavily(
                q.query_text, api_key=settings.tavily_api_key
            )
            run.result_count = len(tavily_results)
            total_results += len(tavily_results)

            for tr in tavily_results:
                sr = _process_result(tr, run, company, inbox_source, db)
                if (
                    sr.processing_status == SearchResultStatus.fetched
                    and sr.linked_document_id
                ):
                    existing = (
                        db.query(Document)
                        .filter(Document.id == sr.linked_document_id)
                        .first()
                    )
                    if existing and existing.from_search:
                        total_docs += 1

            run.status = SearchRunStatus.done
        except Exception as e:
            run.status = SearchRunStatus.error
            run.error_message = str(e)[:1000]

        db.commit()

    return {
        "company_id": company.id,
        "queries_generated": len(queries),
        "results_found": total_results,
        "documents_created": total_docs,
    }


def run_search_all_companies(db: Session) -> Dict[str, Any]:
    companies = db.query(Company).all()
    results = []
    for company in companies:
        result = run_search_for_company(company, db)
        results.append(result)

    ctx = _get_context(db)
    competitive_areas = ctx.get("relevant_competitive_areas", [])
    if competitive_areas:
        trend_queries = generate_trend_queries(competitive_areas)
        for q in trend_queries:
            sq = SearchQuery(
                query_text=q.query_text,
                company_id=None,
                search_intent=q.search_intent,
            )
            db.add(sq)
            db.commit()
            db.refresh(sq)

            run = SearchRun(search_query_id=sq.id, status=SearchRunStatus.running)
            db.add(run)
            db.commit()
            db.refresh(run)

            try:
                tavily_results = search_tavily(
                    q.query_text, api_key=settings.tavily_api_key
                )
                run.result_count = len(tavily_results)
                for tr in tavily_results:
                    sr = SearchResult(
                        search_run_id=run.id,
                        title=tr.title,
                        url=tr.url,
                        domain=tr.domain,
                        snippet=tr.snippet,
                        relevance_score=tr.score,
                        processing_status=SearchResultStatus.skipped,
                    )
                    db.add(sr)
                    if not _domain_has_active_source(
                        tr.domain, db
                    ) and not _domain_has_candidate(tr.domain, db):
                        candidate = SourceCandidate(
                            url=tr.url,
                            domain=tr.domain,
                            title=tr.title,
                            snippet=tr.snippet,
                            found_via_query=q.query_text,
                            company_id=None,
                            source_type_guess=SourceType.news,
                            relevance_score=tr.score,
                            status=SourceCandidateStatus.candidate,
                        )
                        db.add(candidate)
                db.commit()
                run.status = SearchRunStatus.done
            except Exception as e:
                run.status = SearchRunStatus.error
                run.error_message = str(e)[:1000]
            db.commit()

    return {"companies_searched": len(companies), "results": results}
