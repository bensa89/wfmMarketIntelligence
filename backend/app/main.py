from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import secrets
from app.config import settings

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(
        credentials.username, settings.auth_username
    )
    correct_password = secrets.compare_digest(
        credentials.password, settings.auth_password
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


app = FastAPI(
    title="WFM Market Intelligence Hub",
    version="1.0.0",
    dependencies=[Depends(verify_credentials)],
)

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
    discovered_pages,
)  # noqa: E402

app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(digests.router, prefix="/api/digests", tags=["digests"])
app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(
    discovered_pages.router, prefix="/api/discovered-pages", tags=["discovered-pages"]
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
