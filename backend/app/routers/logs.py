from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.log_stream import stream_logs

router = APIRouter()


@router.get("/stream")
async def log_stream():
    return StreamingResponse(
        stream_logs(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
