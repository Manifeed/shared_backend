from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from shared_backend.clients.service_http_client import (
    ServiceClientConfig,
    ServiceRequestTrace,
    build_service_config,
    request_service,
    require_service_client,
)
from shared_backend.errors.app_error import AppError, UpstreamServiceError
from shared_backend.schemas.analytics.analysis_schema import AnalysisOverviewRead, SimilarSourcesRead
from shared_backend.schemas.internal.service_schema import InternalServiceHealthRead
from shared_backend.schemas.sources.source_schema import (
    RssSourceDetailRead,
    RssSourcePageRead,
    UserSourceDetailRead,
    UserSourcePageRead,
    UserSourceSearchPageRead,
)


class ContentServiceNetworkingClient:
    def __init__(
        self,
        config: ServiceClientConfig,
        http_client: httpx.Client | None = None,
        trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._trace_callback = trace_callback

    @classmethod
    def from_env(
        cls,
        *,
        http_client: httpx.Client | None = None,
        trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
    ) -> ContentServiceNetworkingClient | None:
        config = build_service_config(
            base_url_env="CONTENT_SERVICE_URL",
            timeout_env="CONTENT_SERVICE_TIMEOUT_SECONDS",
            default_timeout_seconds=10.0,
            service_name="Content",
        )
        if config is None:
            return None
        return cls(config, http_client=http_client, trace_callback=trace_callback)

    def list_admin_sources(
        self,
        *,
        limit: int,
        offset: int,
        author_id: int | None,
    ) -> RssSourcePageRead:
        response = self._get(
            "/internal/content/admin/sources/",
            params={"limit": limit, "offset": offset, "author_id": author_id},
        )
        return RssSourcePageRead.model_validate(response.json())

    def list_admin_sources_by_feed(
        self,
        *,
        feed_id: int,
        limit: int,
        offset: int,
        author_id: int | None,
    ) -> RssSourcePageRead:
        response = self._get(
            f"/internal/content/admin/sources/feeds/{feed_id}",
            params={"limit": limit, "offset": offset, "author_id": author_id},
        )
        return RssSourcePageRead.model_validate(response.json())

    def list_admin_sources_by_company(
        self,
        *,
        company_id: int,
        limit: int,
        offset: int,
        author_id: int | None,
    ) -> RssSourcePageRead:
        response = self._get(
            f"/internal/content/admin/sources/companies/{company_id}",
            params={"limit": limit, "offset": offset, "author_id": author_id},
        )
        return RssSourcePageRead.model_validate(response.json())

    def read_admin_source(self, *, source_id: int) -> RssSourceDetailRead:
        response = self._get(f"/internal/content/admin/sources/{source_id}")
        return RssSourceDetailRead.model_validate(response.json())

    def list_user_sources(self, *, limit: int, offset: int) -> UserSourcePageRead:
        response = self._get(
            "/internal/content/sources/",
            params={"limit": limit, "offset": offset},
        )
        return UserSourcePageRead.model_validate(response.json())

    def search_user_sources(
        self,
        *,
        q: str | None,
        limit: int,
        offset: int,
        language: str | None,
        publisher_id: int | None,
        author_id: int | None,
        published_from: str | None,
        published_to: str | None,
    ) -> UserSourceSearchPageRead:
        response = self._get(
            "/internal/content/sources/search",
            params={
                "q": q,
                "limit": limit,
                "offset": offset,
                "language": language,
                "publisher_id": publisher_id,
                "author_id": author_id,
                "published_from": published_from,
                "published_to": published_to,
            },
        )
        return UserSourceSearchPageRead.model_validate(response.json())

    def read_user_source(self, *, source_id: int) -> UserSourceDetailRead:
        response = self._get(f"/internal/content/sources/{source_id}")
        return UserSourceDetailRead.model_validate(response.json())

    def read_similar_sources(
        self,
        *,
        source_id: int,
        limit: int,
    ) -> SimilarSourcesRead:
        response = self._get(
            f"/internal/content/sources/{source_id}/similar",
            params={"limit": limit},
        )
        return SimilarSourcesRead.model_validate(response.json())

    def read_analysis_overview(self) -> AnalysisOverviewRead:
        response = self._get("/internal/content/analysis/overview")
        return AnalysisOverviewRead.model_validate(response.json())

    def read_internal_health(self) -> InternalServiceHealthRead:
        response = self._get("/internal/health")
        return InternalServiceHealthRead.model_validate(response.json())

    def read_internal_ready(self) -> InternalServiceHealthRead:
        response = self._get("/internal/ready")
        return InternalServiceHealthRead.model_validate(response.json())

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        return request_service(
            config=self._config,
            method="GET",
            path=path,
            params=params,
            http_client=self._http_client,
            app_error_factory=AppError,
            upstream_error_factory=UpstreamServiceError,
            trace_callback=self._trace_callback,
        )


def get_content_service_client(
    *,
    http_client: httpx.Client | None = None,
    trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
) -> ContentServiceNetworkingClient | None:
    return ContentServiceNetworkingClient.from_env(
        http_client=http_client,
        trace_callback=trace_callback,
    )


def get_required_content_service_client(
    *,
    http_client: httpx.Client | None = None,
    trace_callback: Callable[[ServiceRequestTrace], None] | None = None,
) -> ContentServiceNetworkingClient:
    return require_service_client(
        get_content_service_client(http_client=http_client, trace_callback=trace_callback),
        env_name="CONTENT_SERVICE_URL",
        upstream_error_factory=UpstreamServiceError,
    )
