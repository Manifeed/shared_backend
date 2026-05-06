from __future__ import annotations

import os
from collections.abc import Generator, Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DB_POOL_SIZE = 20
DEFAULT_DB_MAX_OVERFLOW = 40
DEFAULT_DB_POOL_TIMEOUT_SECONDS = 30
DEFAULT_DB_POOL_RECYCLE_SECONDS = 1800


def _read_int_env(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    environment = env or os.environ
    raw_value = environment.get(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    if minimum is not None and parsed < minimum:
        return default
    return parsed


def normalize_database_url(database_url: str) -> str:
    normalized_url = database_url.strip()
    if normalized_url.startswith("postgresql://") and "+psycopg" not in normalized_url:
        return normalized_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized_url


def resolve_database_url(
    primary_env: str,
    *fallback_env_names: str,
    env: Mapping[str, str] | None = None,
) -> str:
    environment = env or os.environ
    for env_name in (primary_env,) + fallback_env_names:
        candidate = environment.get(env_name)
        if candidate and candidate.strip():
            return normalize_database_url(candidate)
    raise RuntimeError(f"{primary_env} must be configured")


def create_sqlalchemy_engine(
    database_url: str,
    *,
    env: Mapping[str, str] | None = None,
) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=_read_int_env("DB_POOL_SIZE", DEFAULT_DB_POOL_SIZE, minimum=1, env=env),
        max_overflow=_read_int_env("DB_MAX_OVERFLOW", DEFAULT_DB_MAX_OVERFLOW, minimum=0, env=env),
        pool_timeout=_read_int_env(
            "DB_POOL_TIMEOUT_SECONDS",
            DEFAULT_DB_POOL_TIMEOUT_SECONDS,
            minimum=1,
            env=env,
        ),
        pool_recycle=_read_int_env(
            "DB_POOL_RECYCLE_SECONDS",
            DEFAULT_DB_POOL_RECYCLE_SECONDS,
            minimum=1,
            env=env,
        ),
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def open_db_session(session_factory: sessionmaker[Session]) -> Session:
    return session_factory()


def get_db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    db = open_db_session(session_factory)
    try:
        yield db
    finally:
        db.close()


def check_database_ready(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@dataclass(frozen=True)
class DatabaseAccess:
    read_url: str
    write_url: str
    read_engine: Engine
    write_engine: Engine
    read_session_factory: sessionmaker[Session]
    write_session_factory: sessionmaker[Session]


def configure_database_access(
    *,
    write_env: str,
    read_env: str | None = None,
    write_fallback_env_names: Sequence[str] = (),
    read_fallback_env_names: Sequence[str] = (),
    env: Mapping[str, str] | None = None,
) -> DatabaseAccess:
    write_url = resolve_database_url(write_env, *write_fallback_env_names, env=env)
    if read_env is None:
        read_url = write_url
    else:
        try:
            read_url = resolve_database_url(read_env, *read_fallback_env_names, env=env)
        except RuntimeError:
            read_url = write_url

    write_engine = create_sqlalchemy_engine(write_url, env=env)
    if read_url == write_url:
        read_engine = write_engine
    else:
        read_engine = create_sqlalchemy_engine(read_url, env=env)

    return DatabaseAccess(
        read_url=read_url,
        write_url=write_url,
        read_engine=read_engine,
        write_engine=write_engine,
        read_session_factory=create_session_factory(read_engine),
        write_session_factory=create_session_factory(write_engine),
    )
