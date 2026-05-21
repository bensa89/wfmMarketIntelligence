import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.source import Source
from app.models.crawl_run import (
    CrawlRun,
    CrawlRunStatus,
    CrawlRunSource,
    CrawlRunSourceStatus,
    CrawlRunStep,
)
from app.crawler.pipeline import run_crawl_source, analyse_unanalysed_for_source
from app.config import settings
from app.schemas.crawl_run import CrawlRunRead, CrawlQueuedRunStatus, CrawlStatusResponse

router = APIRouter()


def _cancel_running_crawl_runs(db: Session) -> None:
    running = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).all()
    for run in running:
        run.status = CrawlRunStatus.cancelled
        run.finished_at = datetime.now(timezone.utc)
    db.commit()


def _create_crawl_run(source_ids: List[str], db: Session) -> CrawlRun:
    _cancel_running_crawl_runs(db)
    crawl_run = CrawlRun(
        status=CrawlRunStatus.running,
        total_sources=len(source_ids),
    )
    db.add(crawl_run)
    db.flush()

    for source_id in source_ids:
        source = db.query(Source).filter(Source.id == source_id).first()
        if source:
            crs = CrawlRunSource(
                crawl_run_id=crawl_run.id,
                source_id=source_id,
                url=source.url,
                status=CrawlRunSourceStatus.pending,
            )
            db.add(crs)
    db.commit()
    return crawl_run


def _crawl_source_worker(
    source_id: str,
    crs_id: str,
    crawl_run_id: str,
) -> Dict:
    worker_db = SessionLocal()
    try:
        source = worker_db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return {"new_documents": 0, "skipped": 0, "errors": 0}

        crs = worker_db.query(CrawlRunSource).filter(CrawlRunSource.id == crs_id).first()
        if not crs:
            return {"new_documents": 0, "skipped": 0, "errors": 0}

        crs.status = CrawlRunSourceStatus.running
        crs.started_at = datetime.now(timezone.utc)
        worker_db.commit()

        def make_callback(sid: str, crs_id_val: str):
            def callback(event: dict) -> None:
                if event.get("type") == "step":
                    step_name = event.get("step")
                    if step_name and step_name in [e.value for e in CrawlRunStep]:
                        crs_obj = (
                            worker_db.query(CrawlRunSource)
                            .filter(CrawlRunSource.id == crs_id_val)
                            .first()
                        )
                        if crs_obj:
                            crs_obj.current_step = CrawlRunStep(step_name)
                            worker_db.commit()
                elif event.get("type") == "discovery_progress":
                    crs_obj = (
                        worker_db.query(CrawlRunSource)
                        .filter(CrawlRunSource.id == crs_id_val)
                        .first()
                    )
                    if crs_obj:
                        crs_obj.discover_pages_crawled = event.get("pages_crawled")
                        crs_obj.discover_pages_found = event.get("pages_found")
                        worker_db.commit()
            return callback

        try:
            result = run_crawl_source(
                source,
                worker_db,
                analyse=True,
                progress_callback=make_callback(source_id, crs_id),
            )
        except Exception as e:
            worker_db.rollback()
            result = {"new_documents": 0, "skipped": 0, "errors": 1}

        timings = result.get("timings", {})

        crs = worker_db.query(CrawlRunSource).filter(CrawlRunSource.id == crs_id).first()
        if crs:
            crs.status = CrawlRunSourceStatus.completed
            crs.current_step = None
            crs.new_documents = result.get("new_documents", 0)
            crs.skipped = result.get("skipped", 0)
            crs.errors = result.get("errors", 0)
            crs.finished_at = datetime.now(timezone.utc)
            crs.fetch_ms = timings.get("fetch_ms")
            crs.extract_ms = timings.get("extract_ms")
            crs.discover_ms = timings.get("discover_ms")
            if (
                result.get("errors", 0) > 0
                and not result.get("new_documents")
                and not result.get("skipped")
            ):
                crs.status = CrawlRunSourceStatus.failed
                crs.error_message = "Errors during crawl"
            worker_db.commit()

        return result
    finally:
        worker_db.close()


def _run_crawl_background(
    crawl_run_id: str,
    source_ids: List[str],
) -> None:
    thread_db = SessionLocal()
    try:
        total_new = 0
        total_skipped = 0
        total_errors = 0

        crs_map: Dict[str, str] = {}
        for sid in source_ids:
            crs_obj = (
                thread_db.query(CrawlRunSource)
                .filter(
                    CrawlRunSource.crawl_run_id == crawl_run_id,
                    CrawlRunSource.source_id == sid,
                )
                .first()
            )
            if crs_obj:
                crs_map[sid] = crs_obj.id

        with ThreadPoolExecutor(max_workers=settings.crawl_concurrency) as executor:
            future_to_source = {}
            for source_id in source_ids:
                crs_id = crs_map.get(source_id)
                if not crs_id:
                    continue
                source = thread_db.query(Source).filter(Source.id == source_id).first()
                if not source:
                    continue
                future = executor.submit(
                    _crawl_source_worker,
                    source_id,
                    crs_id,
                    crawl_run_id,
                )
                future_to_source[future] = source_id

            for future in as_completed(future_to_source):
                source_id = future_to_source[future]
                try:
                    result = future.result()
                    total_new += result.get("new_documents", 0)
                    total_skipped += result.get("skipped", 0)
                    total_errors += result.get("errors", 0)
                except Exception as e:
                    total_errors += 1
                    logger.warning("Crawl worker failed for source %s: %s", source_id, e)

        crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        if crawl_run:
            crawl_run.total_new = total_new
            crawl_run.total_skipped = total_skipped
            crawl_run.total_errors = total_errors
            thread_db.commit()

            from app.models.source import AnalysisStatus as _AS

            thread_db.expire_all()

            analysis_needed = total_new > 0
            if not analysis_needed:
                for crs in crawl_run.sources:
                    src = thread_db.query(Source).filter(Source.id == crs.source_id).first()
                    if src and src.analysis_status == _AS.pending:
                        analysis_needed = True
                        break

            if analysis_needed:
                crawl_run = (
                    thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
                )
                for crs in crawl_run.sources:
                    if crs.status not in (CrawlRunSourceStatus.completed, CrawlRunSourceStatus.failed):
                        continue
                    src = thread_db.query(Source).filter(Source.id == crs.source_id).first()
                    if not src or src.analysis_status != _AS.pending:
                        if crs.new_documents <= 0:
                            continue

                    crs.status = CrawlRunSourceStatus.analysing
                    crs.analyse_started_at = datetime.now(timezone.utc)
                    thread_db.commit()

                    source = thread_db.query(Source).filter(Source.id == crs.source_id).first()
                    analysis_result = {"analysed": 0, "errors": 0, "analyse_ms": 0}
                    if source:
                        def make_analysis_callback(crs_id_val: str):
                            def cb(event: dict) -> None:
                                if event.get("type") == "analysis_progress":
                                    crs_obj = (
                                        thread_db.query(CrawlRunSource)
                                        .filter(CrawlRunSource.id == crs_id_val)
                                        .first()
                                    )
                                    if crs_obj:
                                        crs_obj.analyse_docs_done = event.get("current", 0)
                                        crs_obj.analyse_docs_total = event.get("total", 0)
                                        crs_obj.analyse_current_url = event.get("url") or None
                                        thread_db.commit()
                            return cb

                        try:
                            analysis_result = analyse_unanalysed_for_source(
                                source,
                                thread_db,
                                progress_callback=make_analysis_callback(crs.id),
                            )
                        except Exception as analysis_exc:
                            logger.warning(
                                "Analysis failed for source %s: %s",
                                crs.source_id,
                                analysis_exc,
                            )
                            analysis_result = {"analysed": 0, "errors": 1, "analyse_ms": 0}
                            try:
                                source.analysis_status = _AS.analysis_failed
                                thread_db.commit()
                            except Exception:
                                thread_db.rollback()

                    crs.analyse_ms = analysis_result.get("analyse_ms", 0)
                    crs.analyse_finished_at = datetime.now(timezone.utc)
                    crs.analyse_current_url = None
                    crs.status = CrawlRunSourceStatus.completed
                    thread_db.commit()

            crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
            if crawl_run:
                crawl_run.status = CrawlRunStatus.completed
                crawl_run.finished_at = datetime.now(timezone.utc)
                thread_db.commit()

            try:
                from app.analyser.briefing import generate_briefing_content
                from app.models.crawl_briefing import CrawlBriefing

                briefing_content = generate_briefing_content(thread_db, crawl_run_id=crawl_run_id)
                briefing = CrawlBriefing(
                    crawl_run_id=crawl_run_id,
                    content=briefing_content,
                    generated_at=datetime.now(timezone.utc),
                )
                thread_db.add(briefing)
                thread_db.commit()
            except Exception as e:
                logger.warning("Auto-briefing generation failed: %s", e)

            try:
                from app.models.signal import Signal
                from app.models.company import Company
                from app.assessor.summarizer import generate_competitor_summary

                crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
                if crawl_run and crawl_run.started_at is not None:
                    company_ids_with_new_signals = (
                        thread_db.query(Signal.company_id)
                        .filter(Signal.created_at >= crawl_run.started_at)
                        .distinct()
                        .all()
                    )
                    for (cid,) in company_ids_with_new_signals:
                        company = thread_db.query(Company).filter(Company.id == cid).first()
                        if company:
                            for period in ("7d", "30d"):
                                try:
                                    generate_competitor_summary(company, period, thread_db)
                                except Exception as period_exc:
                                    logger.warning(
                                        "Summary gen failed for %s/%s: %s",
                                        company.name,
                                        period,
                                        period_exc,
                                    )
                elif crawl_run:
                    logger.warning(
                        "Skipping post-crawl summary: crawl_run.started_at is None for run %s",
                        crawl_run_id,
                    )
            except Exception as e:
                logger.warning("Post-crawl summary trigger failed: %s", e)

            # Auto-start queued run if one exists
            queued_run = (
                thread_db.query(CrawlRun)
                .filter(CrawlRun.status == CrawlRunStatus.queued)
                .first()
            )
            if queued_run:
                queued_source_ids = [crs.source_id for crs in queued_run.sources]
                queued_run.status = CrawlRunStatus.running
                queued_run.started_at = datetime.now(timezone.utc)
                thread_db.commit()
                threading.Thread(
                    target=_run_crawl_background,
                    args=(queued_run.id, queued_source_ids),
                    daemon=True,
                ).start()

    except Exception as e:
        crawl_run = thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        if crawl_run:
            crawl_run.status = CrawlRunStatus.failed
            crawl_run.finished_at = datetime.now(timezone.utc)
            thread_db.commit()
        logger.exception("Background crawl failed for run %s: %s", crawl_run_id, e)
    finally:
        thread_db.close()


@router.post("/cancel")
def cancel_crawl(db: Session = Depends(get_db)) -> Dict[str, Any]:
    running = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).all()
    if not running:
        return {"cancelled": 0}
    for run in running:
        run.status = CrawlRunStatus.cancelled
        run.finished_at = datetime.now(timezone.utc)
        for crs in run.sources:
            if crs.status in (
                CrawlRunSourceStatus.pending,
                CrawlRunSourceStatus.running,
                CrawlRunSourceStatus.analysing,
            ):
                crs.status = CrawlRunSourceStatus.failed
                crs.finished_at = datetime.now(timezone.utc)
                if crs.analyse_started_at and not crs.analyse_finished_at:
                    crs.analyse_finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"cancelled": len(running)}


@router.post("/run")
def crawl_all_sources(db: Session = Depends(get_db)) -> Dict[str, Any]:
    active_sources = (
        db.query(Source)
        .filter(Source.is_active == True)  # noqa: E712
        .order_by(Source.last_crawled_at.asc().nullsfirst())
        .all()
    )
    results = []
    for source in active_sources:
        result = run_crawl_source(source, db, analyse=True)
        if result.get("new_documents", 0) > 0:
            source = db.query(Source).filter(Source.id == source.id).first()
            if source:
                analysis_result = analyse_unanalysed_for_source(source, db)
                result["analysis"] = analysis_result
        results.append(result)
    return {"sources_processed": len(active_sources), "results": results}


@router.post("/run/{source_id}")
def crawl_single_source(
    source_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    result = run_crawl_source(source, db, analyse=True)
    if result.get("new_documents", 0) > 0:
        source = db.query(Source).filter(Source.id == source_id).first()
        if source:
            analysis_result = analyse_unanalysed_for_source(source, db)
            result["analysis"] = analysis_result
    return result


@router.post("/enqueue/{source_id}", status_code=202)
def enqueue_source(source_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    queued_run = (
        db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()
    )

    if queued_run is None:
        queued_run = CrawlRun(
            status=CrawlRunStatus.queued,
            total_sources=0,
        )
        db.add(queued_run)
        db.flush()

    # No-op if source already queued
    already_queued = any(crs.source_id == source_id for crs in queued_run.sources)
    if not already_queued:
        crs = CrawlRunSource(
            crawl_run_id=queued_run.id,
            source_id=source_id,
            url=source.url,
            status=CrawlRunSourceStatus.pending,
        )
        db.add(crs)
        db.commit()
        db.refresh(queued_run)
        queued_run.total_sources = len(queued_run.sources)
        db.commit()

    db.refresh(queued_run)
    position = len(queued_run.sources)
    return {"queued": True, "position": position, "crawl_run_id": queued_run.id}


@router.post("/analyse/{source_id}")
def analyse_source(source_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    from app.models.source import AnalysisStatus

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.analysis_status == AnalysisStatus.analysing:
        source.analysis_status = AnalysisStatus.pending
        db.commit()

    result = analyse_unanalysed_for_source(source, db)
    return {
        "source_id": source_id,
        "analysed": result["analysed"],
        "errors": result["errors"],
        "analyse_ms": result["analyse_ms"],
    }


@router.post("/start", status_code=202)
def start_crawl_background(db: Session = Depends(get_db)) -> Dict[str, Any]:
    active_sources = (
        db.query(Source)
        .filter(Source.is_active == True)  # noqa: E712
        .order_by(Source.last_crawled_at.asc().nullsfirst())
        .all()
    )
    if not active_sources:
        return {"crawl_run_id": None, "status": "no_active_sources", "total_sources": 0}
    source_ids = [s.id for s in active_sources]
    crawl_run = _create_crawl_run(source_ids, db)
    threading.Thread(
        target=_run_crawl_background,
        args=(crawl_run.id, source_ids),
        daemon=True,
    ).start()
    return {"crawl_run_id": crawl_run.id, "status": "running", "total_sources": len(source_ids)}


@router.post("/start/{source_id}", status_code=202)
def start_single_source_background(
    source_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    crawl_run = _create_crawl_run([source_id], db)
    threading.Thread(
        target=_run_crawl_background,
        args=(crawl_run.id, [source_id]),
        daemon=True,
    ).start()
    return {"crawl_run_id": crawl_run.id, "status": "running", "total_sources": 1}


@router.get("/status", response_model=CrawlStatusResponse)
def get_crawl_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    active_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).first()

    if not active_run:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        active_run = (
            db.query(CrawlRun)
            .filter(
                CrawlRun.status.in_(
                    [CrawlRunStatus.completed, CrawlRunStatus.failed, CrawlRunStatus.cancelled]
                ),
                CrawlRun.finished_at >= cutoff,
            )
            .order_by(CrawlRun.finished_at.desc())
            .first()
        )

    queued_run = db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()

    return {
        "active_run": CrawlRunRead.model_validate(active_run).model_dump() if active_run else None,
        "queued_run": CrawlQueuedRunStatus(
            id=queued_run.id,
            sources=[{"source_id": crs.source_id, "url": crs.url} for crs in queued_run.sources],
        ).model_dump() if queued_run else None,
    }
