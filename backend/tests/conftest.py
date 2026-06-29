import base64
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db
import app.models  # noqa: F401 — ensures all models are registered with Base.metadata

TEST_DB_PATH = "./test_app.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(b"testuser:testpass").decode()
}
USER_AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(b"regularuser:userpass").decode()
}


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    # Code under test (e.g. app.analyser.client._record_llm_call) calls
    # `SessionLocal()` directly rather than going through the `get_db` DI
    # override used by the `client` fixture below. app.database.SessionLocal
    # is a module-level singleton bound to a pooled connection created at
    # import time, so without this alias it can hold a stale connection to
    # a previous test's (already deleted) sqlite file, causing spurious
    # "no such table" errors or invisible writes. Repoint it at this test's
    # engine for the duration of the test so direct SessionLocal() calls and
    # the `db_session` fixture observe the same database.
    import app.database as database_module
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    original_session_local = database_module.SessionLocal
    database_module.SessionLocal = test_session_factory

    yield engine

    database_module.SessionLocal = original_session_local
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(scope="function")
def db_session(db_engine):
    from app.models.user import User, UserRole
    from app.auth import hash_password

    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()

    admin = User(username="testuser", hashed_password=hash_password("testpass"), role=UserRole.admin, is_active=True)
    regular = User(username="regularuser", hashed_password=hash_password("userpass"), role=UserRole.user, is_active=True)
    session.add_all([admin, regular])
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.scheduler.startup_scheduler", lambda engine: None), \
         patch("app.scheduler.shutdown_scheduler", lambda: None), \
         patch("app.scheduler.apply_schedule", lambda config: None):
        with TestClient(app, headers=AUTH_HEADER) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user_client(db_session):
    """TestClient authenticated as a regular (non-admin) user."""
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.scheduler.startup_scheduler", lambda engine: None), \
         patch("app.scheduler.shutdown_scheduler", lambda: None), \
         patch("app.scheduler.apply_schedule", lambda config: None):
        with TestClient(app, headers=USER_AUTH_HEADER) as c:
            yield c

    app.dependency_overrides.clear()
