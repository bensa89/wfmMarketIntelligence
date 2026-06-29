import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth import verify_credentials, hash_password

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

logger = logging.getLogger(__name__)


def _seed_initial_admin():
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    db = SessionLocal()
    try:
        if not db.query(User).first():
            admin = User(
                username="admin",
                hashed_password=hash_password("changeme"),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Seeded initial admin user (admin/changeme)")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, SessionLocal
    from app.models.schedule import ScheduleConfig
    from app import scheduler as sched_module
    from app import log_stream
    from app.settings_overrides import load_overrides_from_db

    log_stream.install()
    _seed_initial_admin()

    try:
        sched_module.startup_scheduler(engine)

        db = SessionLocal()
        config = None
        try:
            config = db.query(ScheduleConfig).filter(ScheduleConfig.id == 1).first()
            if config is None:
                config = ScheduleConfig()
                db.add(config)
                db.commit()
                db.refresh(config)
            load_overrides_from_db(db)
        finally:
            db.close()

        sched_module.apply_schedule(config)
    except Exception as exc:
        logger.warning("Scheduler startup failed (likely test environment): %s", exc)

    yield

    sched_module.shutdown_scheduler()


app = FastAPI(
    title="WFM Market Intelligence Hub",
    version="1.0.0",
    dependencies=[Depends(verify_credentials)],
    lifespan=lifespan,
)

UPLOAD_DIR = pathlib.Path("/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "logos").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import (
    companies,
    sources,
    documents,
    signals,
    digests,
    context,
    crawl,
    crawl_runs,
    discovered_pages,
    search,
    stats,
    briefings,
    intelligence,
    intelligence_briefing,
    benchmark,
    scorecards,
    schedule,
    logs,
    llm_usage,
    settings_admin,
)  # noqa: E402

app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(digests.router, prefix="/api/digests", tags=["digests"])
app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(crawl_runs.router, prefix="/api/crawl-runs", tags=["crawl-runs"])
app.include_router(
    discovered_pages.router, prefix="/api/discovered-pages", tags=["discovered-pages"]
)
app.include_router(search.search_router, prefix="/api/search", tags=["search"])
app.include_router(
    search.candidates_router,
    prefix="/api/source-candidates",
    tags=["source-candidates"],
)
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(briefings.router, prefix="/api/crawl-briefings", tags=["crawl-briefings"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(intelligence_briefing.router, prefix="/api/intelligence-briefings", tags=["intelligence-briefings"])
app.include_router(benchmark.router)
app.include_router(scorecards.router)
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(llm_usage.router, prefix="/api/llm-usage", tags=["llm-usage"])
app.include_router(settings_admin.router, prefix="/api/admin/settings", tags=["settings-admin"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
