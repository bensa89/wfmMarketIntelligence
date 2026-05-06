import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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


def _crawl_single_source(
    source_id: str,
    source_url: str,
    crs_id: str,
    crawl_run_id: str,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> Dict:
    worker_db = SessionLocal()
    try:
        source = worker_db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return {"new_documents": 0, "skipped": 0, "errors": 0}

        crs = (
            worker_db.query(CrawlRunSource).filter(CrawlRunSource.id == crs_id).first()
        )
        if not crs:
            return {"new_documents": 0, "skipped": 0, "errors": 0}

        crs.status = CrawlRunSourceStatus.running
        crs.started_at = datetime.now(timezone.utc)
        worker_db.commit()

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "source_start",
                "crawl_run_id": crawl_run_id,
                "source_id": source_id,
                "url": source_url,
            },
        )

        def make_callback(sid: str, crs_id_val: str):
            def callback(event: dict) -> None:
                event_copy = dict(event)
                event_copy["crawl_run_id"] = crawl_run_id
                event_copy["source_id"] = sid
                if event.get("type") in ("step", "discovery_progress"):
                    crs_obj = (
                        worker_db.query(CrawlRunSource)
                        .filter(CrawlRunSource.id == crs_id_val)
                        .first()
                    )
                    if crs_obj:
                        if event.get("type") == "step":
                            step_name = event.get("step")
                            if step_name and step_name in [
                                e.value for e in CrawlRunStep
                            ]:
                                crs_obj.current_step = CrawlRunStep(step_name)
                        else:
                            crs_obj.discover_pages_crawled = event.get("pages_crawled")
                            crs_obj.discover_pages_found = event.get("pages_found")
                        worker_db.commit()
                loop.call_soon_threadsafe(queue.put_nowait, event_copy)

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
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "error",
                    "crawl_run_id": crawl_run_id,
                    "source_id": source_id,
                    "message": str(e),
                },
            )

        timings = result.get("timings", {})

        crs = (
            worker_db.query(CrawlRunSource).filter(CrawlRunSource.id == crs_id).first()
        )
        if crs:
            crs.status = CrawlRunSourceStatus.completed
            crs.current_step = None
            crs.new_documents = result.get("new_documents", 0)
            crs.skipped = result.get("skipped", 0)
            crs.errors = result.get("errors", 0)
            crs.finished_at = datetime.now(timezone.utc)
            crs.fetch_ms = timings.get("fetch_ms")
            crs.extract_ms = timings.get("extract_ms")
            crs.analyse_ms = timings.get("analyse_ms")
            crs.discover_ms = timings.get("discover_ms")
            if (
                result.get("errors", 0) > 0
                and not result.get("new_documents")
                and not result.get("skipped")
            ):
                crs.status = CrawlRunSourceStatus.failed
                if result.get("errors", 0) > 0:
                    crs.error_message = "Errors during crawl"
            worker_db.commit()

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "source_done",
                "crawl_run_id": crawl_run_id,
                "source_id": source_id,
                "new_documents": result.get("new_documents", 0),
                "skipped": result.get("skipped", 0),
                "errors": result.get("errors", 0),
                "timings": timings,
            },
        )

        return result
    finally:
        worker_db.close()


def _run_sources_in_thread(
    crawl_run_id: str,
    source_ids: List[str],
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> None:
    thread_db = SessionLocal()
    try:
        total = len(source_ids)
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"type": "crawl_start", "crawl_run_id": crawl_run_id, "total": total},
        )
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
                    _crawl_single_source,
                    source_id,
                    source.url,
                    crs_id,
                    crawl_run_id,
                    loop,
                    queue,
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
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        {
                            "type": "error",
                            "crawl_run_id": crawl_run_id,
                            "source_id": source_id,
                            "message": str(e),
                        },
                    )

        crawl_run = (
            thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        )
        if crawl_run:
            crawl_run.status = CrawlRunStatus.completed
            crawl_run.finished_at = datetime.now(timezone.utc)
            crawl_run.total_new = total_new
            crawl_run.total_skipped = total_skipped
            crawl_run.total_errors = total_errors
            thread_db.commit()

            try:
                from app.analyser.briefing import generate_briefing_content
                from app.models.crawl_briefing import CrawlBriefing

                briefing_content = generate_briefing_content(
                    thread_db, crawl_run_id=crawl_run_id
                )
                briefing = CrawlBriefing(
                    crawl_run_id=crawl_run_id,
                    content=briefing_content,
                    generated_at=datetime.now(timezone.utc),
                )
                thread_db.add(briefing)
                thread_db.commit()
            except Exception as e:
                logger.warning("Auto-briefing generation failed: %s", e)

            # Trigger competitor summaries for companies with new signals in this run
            try:
                from app.models.signal import Signal
                from app.models.company import Company
                from app.assessor.summarizer import generate_competitor_summary

                if crawl_run.started_at is not None:
                    company_ids_with_new_signals = (
                        thread_db.query(Signal.company_id)
                        .filter(Signal.created_at >= crawl_run.started_at)
                        .distinct()
                        .all()
                    )
                    for (cid,) in company_ids_with_new_signals:
                        company = (
                            thread_db.query(Company).filter(Company.id == cid).first()
                        )
                        if company:
                            for period in ("7d", "30d"):
                                try:
                                    generate_competitor_summary(
                                        company, period, thread_db
                                    )
                                except Exception as period_exc:
                                    logger.warning(
                                        "Summary gen failed for %s/%s: %s",
                                        company.name,
                                        period,
                                        period_exc,
                                    )
                else:
                    logger.warning(
                        "crawl_run.started_at is None — skipping post-crawl summary trigger"
                    )
            except Exception as e:
                logger.warning("Post-crawl summary trigger failed: %s", e)

            if total_new > 0:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "analysis_phase_start", "crawl_run_id": crawl_run_id},
                )

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "crawl_done",
                    "crawl_run_id": crawl_run_id,
                    "sources_processed": total,
                    "total_new": total_new,
                    "total_errors": total_errors,
                    "analysis_pending": total_new > 0,
                    "docs_to_analyse": total_new,
                },
            )

            if total_new > 0:
                crawl_run = (
                    thread_db.query(CrawlRun)
                    .filter(CrawlRun.id == crawl_run_id)
                    .first()
                )
                for crs in crawl_run.sources:
                    if (
                        crs.status != CrawlRunSourceStatus.completed
                        or crs.new_documents <= 0
                    ):
                        continue
                    crs.status = CrawlRunSourceStatus.analysing
                    crs.analyse_started_at = datetime.now(timezone.utc)
                    thread_db.commit()

                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        {
                            "type": "analysis_start",
                            "crawl_run_id": crawl_run_id,
                            "source_id": crs.source_id,
                            "url": crs.url,
                        },
                    )

                    source = (
                        thread_db.query(Source)
                        .filter(Source.id == crs.source_id)
                        .first()
                    )
                    analysis_result = {"analysed": 0, "errors": 0, "analyse_ms": 0}
                    if source:
                        try:
                            from app.models.source import AnalysisStatus

                            def make_analysis_callback(sid, crs_id_val):
                                def cb(event):
                                    event_copy = dict(event)
                                    event_copy["crawl_run_id"] = crawl_run_id
                                    event_copy["source_id"] = sid
                                    if event.get("type") == "analysis_progress":
                                        loop.call_soon_threadsafe(
                                            queue.put_nowait, event_copy
                                        )

                                return cb

                            analysis_result = analyse_unanalysed_for_source(
                                source,
                                thread_db,
                                progress_callback=make_analysis_callback(
                                    crs.source_id, crs.id
                                ),
                            )
                        except Exception as analysis_exc:
                            logger.warning(
                                "Analysis failed for source %s: %s",
                                crs.source_id,
                                analysis_exc,
                            )
                            analysis_result = {
                                "analysed": 0,
                                "errors": 1,
                                "analyse_ms": 0,
                            }
                            try:
                                source.analysis_status = AnalysisStatus.analysis_failed
                                thread_db.commit()
                            except Exception:
                                thread_db.rollback()

                    crs.analyse_ms = analysis_result.get("analyse_ms", 0)
                    crs.analyse_finished_at = datetime.now(timezone.utc)
                    crs.status = CrawlRunSourceStatus.completed
                    thread_db.commit()

                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        {
                            "type": "analysis_done",
                            "crawl_run_id": crawl_run_id,
                            "source_id": crs.source_id,
                            "url": crs.url,
                            "analysed": analysis_result.get("analysed", 0),
                            "analyse_ms": crs.analyse_ms,
                        },
                    )

                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "analysis_phase_done", "crawl_run_id": crawl_run_id},
                )
    except Exception as e:
        crawl_run = (
            thread_db.query(CrawlRun).filter(CrawlRun.id == crawl_run_id).first()
        )
        if crawl_run:
            crawl_run.status = CrawlRunStatus.failed
            crawl_run.finished_at = datetime.now(timezone.utc)
            thread_db.commit()
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "error",
                "crawl_run_id": crawl_run_id,
                "source_id": None,
                "message": str(e),
            },
        )
    finally:
        thread_db.close()
        loop.call_soon_threadsafe(queue.put_nowait, None)


async def _sse_generator(
    source_ids: List[str], db: Session, existing_run_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    if existing_run_id is not None:
        crawl_run = db.query(CrawlRun).filter(CrawlRun.id == existing_run_id).first()
        crawl_run.status = CrawlRunStatus.running
        crawl_run.started_at = datetime.now(timezone.utc)
        db.commit()
    else:
        crawl_run = _create_crawl_run(source_ids, db)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    thread = threading.Thread(
        target=_run_sources_in_thread,
        args=(crawl_run.id, source_ids, loop, queue),
        daemon=True,
    )
    thread.start()

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"


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


@router.get("/stream")
async def stream_all_sources(db: Session = Depends(get_db)) -> StreamingResponse:
    source_ids = [
        s.id
        for s in (
            db.query(Source)
            .filter(Source.is_active == True)  # noqa: E712
            .order_by(Source.last_crawled_at.asc().nullsfirst())
            .all()
        )
    ]
    return StreamingResponse(
        _sse_generator(source_ids, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/queued")
async def stream_queued_run(db: Session = Depends(get_db)) -> StreamingResponse:
    queued_run = (
        db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()
    )
    if not queued_run:
        raise HTTPException(status_code=404, detail="No queued run found")

    source_ids = [crs.source_id for crs in queued_run.sources]
    return StreamingResponse(
        _sse_generator(source_ids, db, existing_run_id=queued_run.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/{source_id}")
async def stream_single_source(
    source_id: str, db: Session = Depends(get_db)
) -> StreamingResponse:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return StreamingResponse(
        _sse_generator([source_id], db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.get("/reconnect")
async def reconnect_crawl(db: Session = Depends(get_db)) -> StreamingResponse:
    running_run = (
        db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).first()
    )
    queued_run = (
        db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.queued).first()
    )

    events: list[dict] = []

    if running_run:
        sources_data = []
        for crs in running_run.sources:
            sources_data.append(
                {
                    "source_id": crs.source_id,
                    "url": crs.url,
                    "status": crs.status.value if crs.status else "pending",
                    "current_step": crs.current_step.value
                    if crs.current_step
                    else None,
                    "new_documents": crs.new_documents,
                    "skipped": crs.skipped,
                    "errors": crs.errors,
                    "error_message": crs.error_message,
                    "fetch_ms": crs.fetch_ms,
                    "extract_ms": crs.extract_ms,
                    "analyse_ms": crs.analyse_ms,
                    "discover_ms": crs.discover_ms,
                    "discover_pages_crawled": crs.discover_pages_crawled,
                    "discover_pages_found": crs.discover_pages_found,
                }
            )
        analysis_phase_active = any(
            crs.status == CrawlRunSourceStatus.analysing
            for crs in running_run.sources
        )
        events.append(
            {
                "type": "initial_state",
                "crawl_run_id": running_run.id,
                "total": running_run.total_sources,
                "sources": sources_data,
                "analysis_phase_active": analysis_phase_active,
            }
        )

    if queued_run:
        queued_sources = [
            {"source_id": crs.source_id, "url": crs.url} for crs in queued_run.sources
        ]
        events.append(
            {
                "type": "queued_state",
                "crawl_run_id": queued_run.id,
                "sources": queued_sources,
            }
        )

    if not running_run and not queued_run:
        events.append({"type": "no_active_run"})

    events.append({"type": "reconnect_complete"})

    async def generate():
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
