from __future__ import annotations

import os
from collections.abc import Mapping


_DEVELOPMENT_ENVIRONMENTS = frozenset(
    {"dev", "development", "local", "test", "testing"}
)
_PRODUCTION_LIKE_ENVIRONMENTS = frozenset({"prod", "production", "staging"})
_ENVIRONMENT_VARIABLES = ("APP_ENV", "ENVIRONMENT", "NODE_ENV")


def is_development_environment(env: Mapping[str, str] | None = None) -> bool:
    normalized_environment = _read_environment_name(env)
    if normalized_environment in _DEVELOPMENT_ENVIRONMENTS:
        return True
    if normalized_environment in _PRODUCTION_LIKE_ENVIRONMENTS:
        return False
    return False


def is_production_like_environment(env: Mapping[str, str] | None = None) -> bool:
    normalized_environment = _read_environment_name(env)
    if normalized_environment in _PRODUCTION_LIKE_ENVIRONMENTS:
        return True
    if normalized_environment in _DEVELOPMENT_ENVIRONMENTS:
        return False
    return False


def _read_environment_name(env: Mapping[str, str] | None = None) -> str:
    environment = env or os.environ
    for env_var in _ENVIRONMENT_VARIABLES:
        raw_value = environment.get(env_var)
        if raw_value is None:
            continue
        return raw_value.strip().lower()
    return ""
