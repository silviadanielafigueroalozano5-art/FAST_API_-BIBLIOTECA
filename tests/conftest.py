import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

os.environ["ENVIRONMENT"] = "test"


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: str | None = None


os.environ["DATABASE_URL"] = TestSettings().test_database_url or "sqlite://"
os.environ.setdefault("SECRET_KEY", "local-test-secret-key-at-least-32-characters")
os.environ.setdefault("CORS_ORIGINS", "[]")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.database import engine
from app.core.limiter import limiter
from app.main import app


def migrate(revision: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        if revision == "base":
            command.downgrade(config, "base")
        else:
            command.upgrade(config, revision)


@pytest.fixture
def client():
    migrate("base")
    migrate("head")
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    migrate("base")
