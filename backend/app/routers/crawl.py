import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List

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
from app.crawler.pipeline import run_crawl_source

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

        for i, source_id in enumerate(source_ids):
            source = thread_db.query(Source).filter(Source.id == source_id).first()
            if not source:
                continue

            crs = (
                thread_db.query(CrawlRunSource)
                .filter(
                    CrawlRunSource.crawl_run_id == crawl_run_id,
                    CrawlRunSource.source_id == source_id,
                )
                .first()
            )
            if not crs:
                continue

            crs.status = CrawlRunSourceStatus.running
            crs.started_at = datetime.now(timezone.utc)
            thread_db.commit()

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_start",
                    "crawl_run_id": crawl_run_id,
                    "source_id": source.id,
                    "url": source.url,
                    "index": i + 1,
                    "total": total,
                },
            )

            def make_callback(sid: str, crs_id: str):
                def callback(event: dict) -> None:
                    event_copy = dict(event)
                    event_copy["crawl_run_id"] = crawl_run_id
                    event_copy["source_id"] = sid
                    if event["type"] == "step":
                        crs_obj = (
                            thread_db.query(CrawlRunSource)
                            .filter(CrawlRunSource.id == crs_id)
                            .first()
                        )
                        if crs_obj:
                            step_name = event.get("step")
                            if step_name and step_name in [
                                e.value for e in CrawlRunStep
                            ]:
                                crs_obj.current_step = CrawlRunStep(step_name)
                                thread_db.commit()
                    loop.call_soon_threadsafe(queue.put_nowait, event_copy)

                return callback

            try:
                result = run_crawl_source(
                    source,
                    thread_db,
                    analyse=True,
                    progress_callback=make_callback(source.id, crs.id),
                )
            except Exception as e:
                thread_db.rollback()
                result = {"new_documents": 0, "skipped": 0, "errors": 1}
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "error",
                        "crawl_run_id": crawl_run_id,
                        "source_id": source.id,
                        "message": str(e),
                    },
                )

            total_new += result.get("new_documents", 0)
            total_skipped += result.get("skipped", 0)
            total_errors += result.get("errors", 0)

            crs.status = CrawlRunSourceStatus.completed
            crs.current_step = None
            crs.new_documents = result.get("new_documents", 0)
            crs.skipped = result.get("skipped", 0)
            crs.errors = result.get("errors", 0)
            crs.finished_at = datetime.now(timezone.utc)
            if (
                result.get("errors", 0) > 0
                and not result.get("new_documents")
                and not result.get("skipped")
            ):
                crs.status = CrawlRunSourceStatus.failed
                if result.get("errors", 0) > 0:
                    crs.error_message = "Errors during crawl"
            thread_db.commit()

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_done",
                    "crawl_run_id": crawl_run_id,
                    "source_id": source.id,
                    "new_documents": result["new_documents"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
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

            # Trigger competitor summaries for companies with new signals in this run
            try:
                from app.models.signal import Signal
                from app.models.company import Company
                from app.assessor.summarizer import generate_competitor_summary

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
                            except Exception as e:
                                logger.warning("Summary gen failed for %s/%s: %s", company.name, period, e)
            except Exception as e:
                logger.warning("Post-crawl summary trigger failed: %s", e)

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "crawl_done",
                "crawl_run_id": crawl_run_id,
                "sources_processed": total,
                "total_new": total_new,
                "total_errors": total_errors,
            },
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
    source_ids: List[str], db: Session
) -> AsyncGenerator[str, None]:
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
        results.append(result)
    return {"sources_processed": len(active_sources), "results": results}


@router.post("/run/{source_id}")
def crawl_single_source(
    source_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return run_crawl_source(source, db, analyse=True)


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


@router.get("/reconnect")
async def reconnect_crawl(db: Session = Depends(get_db)) -> StreamingResponse:
    running_run = (
        db.query(CrawlRun).filter(CrawlRun.status == CrawlRunStatus.running).first()
    )
    if not running_run:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'no_active_run'})}\n\n"]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    sources_data = []
    for crs in running_run.sources:
        sources_data.append(
            {
                "source_id": crs.source_id,
                "url": crs.url,
                "status": crs.status.value if crs.status else "pending",
                "current_step": crs.current_step.value if crs.current_step else None,
                "new_documents": crs.new_documents,
                "skipped": crs.skipped,
                "errors": crs.errors,
                "error_message": crs.error_message,
            }
        )

    initial_event = {
        "type": "initial_state",
        "crawl_run_id": running_run.id,
        "total": running_run.total_sources,
        "sources": sources_data,
    }

    async def generate():
        yield f"data: {json.dumps(initial_event)}\n\n"
        yield f"data: {json.dumps({'type': 'reconnect_complete'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
