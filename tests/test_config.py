import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("database_url", "expected_url"),
    [
        (
            "postgres://usuario:clave@host:5432/biblioteca",
            "postgresql+psycopg://usuario:clave@host:5432/biblioteca",
        ),
        (
            "postgresql://usuario:clave@host:5432/biblioteca",
            "postgresql+psycopg://usuario:clave@host:5432/biblioteca",
        ),
        (
            "postgresql+psycopg://usuario:clave@host:5432/biblioteca",
            "postgresql+psycopg://usuario:clave@host:5432/biblioteca",
        ),
    ],
)
def test_database_url_uses_installed_psycopg_driver(database_url, expected_url):
    settings = Settings(
        _env_file=None,
        secret_key="x" * 32,
        database_url=database_url,
    )

    assert settings.database_url_efectiva == expected_url
