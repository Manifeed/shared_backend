from __future__ import annotations

from collections.abc import Iterable
import os
from urllib.parse import urlsplit, urlunsplit


def normalize_public_http_url(value: str | None, *, require_https: bool = False) -> str | None:
    raw_value = (value or "").strip()
    if not raw_value:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_value):
        return None

    try:
        parsed_url = urlsplit(raw_value)
        scheme = parsed_url.scheme.lower()
        hostname = parsed_url.hostname
        parsed_url.port
    except ValueError:
        return None

    if scheme not in {"http", "https"}:
        return None
    if require_https and scheme != "https":
        return None
    if not hostname:
        return None
    if parsed_url.username or parsed_url.password:
        return None

    return raw_value


def normalize_public_base_url(value: str | None, *, require_https: bool = False) -> str | None:
    raw_value = normalize_public_http_url(value, require_https=require_https)
    if raw_value is None:
        return None

    parsed_url = urlsplit(raw_value)
    if parsed_url.query or parsed_url.fragment:
        return None

    scheme = parsed_url.scheme.lower()
    hostname = (parsed_url.hostname or "").lower()
    port = parsed_url.port

    netloc = hostname
    if port is not None and not (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    ):
        netloc = f"{netloc}:{port}"

    path = parsed_url.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def require_public_base_url(
    *,
    env_name: str = "PUBLIC_BASE_URL",
    require_https: bool = False,
) -> str:
    normalized_base_url = normalize_public_base_url(
        os.getenv(env_name),
        require_https=require_https,
    )
    if normalized_base_url is None:
        raise RuntimeError(
            f"{env_name} must be configured as an absolute public http(s) URL"
        )
    return normalized_base_url


def build_public_url(base_url: str, path: str) -> str:
    normalized_base_url = normalize_public_base_url(base_url)
    if normalized_base_url is None:
        raise RuntimeError("base_url must be a valid public http(s) URL")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{normalized_base_url}{normalized_path}"


def resolve_allowed_hosts(
    *,
    public_base_url: str | None = None,
    raw_allowed_hosts: str = "",
    extra_hosts: Iterable[str] | None = None,
) -> list[str]:
    allowed_hosts = {"localhost", "127.0.0.1", "[::1]", "testserver"}

    normalized_base_url = normalize_public_base_url(public_base_url)
    if normalized_base_url is not None:
        hostname = urlsplit(normalized_base_url).hostname
        if hostname:
            allowed_hosts.add(hostname.lower())

    for raw_host in raw_allowed_hosts.split(","):
        host = raw_host.strip().lower()
        if host:
            allowed_hosts.add(host)

    for host in extra_hosts or ():
        normalized_host = host.strip().lower()
        if normalized_host:
            allowed_hosts.add(normalized_host)

    return sorted(allowed_hosts)
