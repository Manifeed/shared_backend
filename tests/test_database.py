from __future__ import annotations

from shared_backend.database import configure_database_access, normalize_database_url


def test_normalize_database_url_adds_psycopg_driver() -> None:
    assert normalize_database_url("postgresql://user:pass@localhost:5432/app") == (
        "postgresql+psycopg://user:pass@localhost:5432/app"
    )


def test_configure_database_access_falls_back_read_to_write() -> None:
    access = configure_database_access(
        write_env="CONTENT_WRITE_DATABASE_URL",
        read_env="CONTENT_READ_DATABASE_URL",
        write_fallback_env_names=("CONTENT_DATABASE_URL",),
        env={"CONTENT_DATABASE_URL": "postgresql://user:pass@localhost:5432/content"},
    )

    assert access.write_url == "postgresql+psycopg://user:pass@localhost:5432/content"
    assert access.read_url == access.write_url
    assert access.read_engine is access.write_engine
