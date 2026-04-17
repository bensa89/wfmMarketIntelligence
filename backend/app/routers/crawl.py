import asyncio
import json
import threading
from typing import AsyncGenerator, Dict, Any, List, NamedTuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.source import Source
from app.crawler.pipeline import run_crawl_source

router = APIRouter()


@router.post("/run")
def crawl_all_sources(db: Session = Depends(get_db)) -> Dict[str, Any]:
    active_sources = db.query(Source).filter(Source.is_active == True).all()  # noqa: E712
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


def _run_sources_in_thread(
    sources: List[Source],
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
) -> None:
    thread_db = SessionLocal()
    try:
        total = len(sources)
        loop.call_soon_threadsafe(
            queue.put_nowait, {"type": "crawl_start", "total": total}
        )
        total_new = 0
        total_errors = 0

        for i, source in enumerate(sources):
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_start",
                    "source_id": source.id,
                    "url": source.url,
                    "index": i + 1,
                    "total": total,
                },
            )

            def make_callback(sid: str):
                def callback(event: dict) -> None:
                    loop.call_soon_threadsafe(queue.put_nowait, event)

                return callback

            result = run_crawl_source(
                source,
                thread_db,
                analyse=True,
                progress_callback=make_callback(source.id),
            )
            total_new += result.get("new_documents", 0)
            total_errors += result.get("errors", 0)

            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "source_done",
                    "source_id": source.id,
                    "new_documents": result["new_documents"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
            )

        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "crawl_done",
                "sources_processed": total,
                "total_new": total_new,
                "total_errors": total_errors,
            },
        )
    except Exception as e:
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"type": "error", "source_id": None, "message": str(e)},
        )
    finally:
        thread_db.close()
        loop.call_soon_threadsafe(queue.put_nowait, None)


async def _sse_generator(sources: List[Source]) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    thread = threading.Thread(
        target=_run_sources_in_thread,
        args=(sources, loop, queue),
        daemon=True,
    )
    thread.start()

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"


@router.get("/stream")
async def stream_all_sources(db: Session = Depends(get_db)) -> StreamingResponse:
    sources = db.query(Source).filter(Source.is_active == True).all()  # noqa: E712
    return StreamingResponse(
        _sse_generator(sources),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/stream/{source_id}")
async def stream_single_source(
    source_id: str, db: Session = Depends(get_db)
) -> StreamingResponse:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return StreamingResponse(
        _sse_generator([source]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
