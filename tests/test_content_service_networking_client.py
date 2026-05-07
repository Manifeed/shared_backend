from __future__ import annotations

from datetime import datetime, timezone

import httpx

from shared_backend.clients import content_service_networking_client
from shared_backend.clients.content_service_networking_client import ContentServiceNetworkingClient
from shared_backend.clients.service_http_client import ServiceClientConfig
from shared_backend.schemas.analytics.analysis_schema import AnalysisOverviewRead
from shared_backend.schemas.sources.source_schema import RssSourcePageRead, UserSourceSearchPageRead


def _config() -> ServiceClientConfig:
    return ServiceClientConfig(
        base_url="http://content-service:8000",
        internal_token="x" * 32,
        timeout_seconds=10.0,
        service_name="Content",
    )


def test_list_admin_sources_calls_internal_content_path(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": 11,
                        "title": "Admin source",
                        "authors": [],
                        "url": "https://example.com/source",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "company_names": ["ACME"],
                        "image_url": None,
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            },
            request=httpx.Request("GET", "http://content-service:8000/internal/content/admin/sources/"),
        )

    monkeypatch.setattr(content_service_networking_client, "request_service", fake_request_service)
    client = ContentServiceNetworkingClient(_config())

    response = client.list_admin_sources(limit=50, offset=0, author_id=7)

    assert isinstance(response, RssSourcePageRead)
    assert seen["method"] == "GET"
    assert seen["path"] == "/internal/content/admin/sources/"
    assert seen["params"] == {"limit": 50, "offset": 0, "author_id": 7}


def test_read_analysis_overview_uses_internal_content_endpoint(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "total_sources": 12,
                "indexed_embeddings": 10,
                "qdrant_collection": "article_embeddings",
            },
            request=httpx.Request("GET", "http://content-service:8000/internal/content/analysis/overview"),
        )

    monkeypatch.setattr(content_service_networking_client, "request_service", fake_request_service)
    client = ContentServiceNetworkingClient(_config())

    response = client.read_analysis_overview()

    assert isinstance(response, AnalysisOverviewRead)
    assert response.total_sources == 12
    assert seen["path"] == "/internal/content/analysis/overview"


def test_search_user_sources_calls_internal_content_search_path(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={
                "raw_query": "finance",
                "subject_query": "finance",
                "applied_filters": [],
                "items": [],
                "limit": 24,
                "offset": 0,
                "has_more": False,
            },
            request=httpx.Request("GET", "http://content-service:8000/internal/content/sources/search"),
        )

    monkeypatch.setattr(content_service_networking_client, "request_service", fake_request_service)
    client = ContentServiceNetworkingClient(_config())

    response = client.search_user_sources(
        q="finance",
        limit=24,
        offset=0,
        language="fr",
        publisher_id=4,
        author_id=8,
        published_from="2026-01-01",
        published_to="2026-01-31",
    )

    assert isinstance(response, UserSourceSearchPageRead)
    assert seen["path"] == "/internal/content/sources/search"
    assert seen["params"] == {
        "q": "finance",
        "limit": 24,
        "offset": 0,
        "language": "fr",
        "publisher_id": 4,
        "author_id": 8,
        "published_from": "2026-01-01",
        "published_to": "2026-01-31",
    }


def test_read_internal_ready_uses_ready_endpoint(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_request_service(**kwargs) -> httpx.Response:
        seen.update(kwargs)
        return httpx.Response(
            200,
            json={"service": "content-service", "status": "ready"},
            request=httpx.Request("GET", "http://content-service:8000/internal/ready"),
        )

    monkeypatch.setattr(content_service_networking_client, "request_service", fake_request_service)
    client = ContentServiceNetworkingClient(_config())

    response = client.read_internal_ready()

    assert response.status == "ready"
    assert seen["path"] == "/internal/ready"
