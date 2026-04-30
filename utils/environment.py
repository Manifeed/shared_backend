from __future__ import annotations

import os
from collections.abc import Mapping


TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})
LOCAL_ENVIRONMENTS = frozenset({"", "dev", "development", "local", "test", "testing"})


def is_truthy_env_value(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUTHY_VALUES


def get_runtime_environment(env: Mapping[str, str] | None = None) -> str:
    environment = env or os.environ
    return environment.get("APP_ENV", environment.get("ENVIRONMENT", "")).strip().lower()


def is_local_environment(env: Mapping[str, str] | None = None) -> bool:
    environment = env or os.environ
    if is_truthy_env_value(environment.get("REQUIRE_INTERNAL_SERVICE_TOKEN")):
        return False
    runtime_environment = get_runtime_environment(environment)
    if runtime_environment:
        return runtime_environment in LOCAL_ENVIRONMENTS
    return True
