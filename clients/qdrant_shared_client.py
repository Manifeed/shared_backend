from __future__ import annotations

import httpx

from shared_backend.clients.qdrant_client_models import (
    QdrantIndexingError,
    QdrantScoredArticleEmbeddingPointRead,
    build_article_embedding_point_id,
    build_qdrant_collection_config,
    build_qdrant_source_search_filter,
    normalize_qdrant_country,
    parse_payload_authors,
    parse_payload_feeds,
    published_at_to_unix_seconds,
    to_embedding_point_read,
    to_embedding_point_summary_read,
    to_scored_point_read,
)
from shared_backend.domain.source_embedding_config import (
    resolve_qdrant_api_key,
    resolve_qdrant_collection_name,
    resolve_qdrant_url,
)


ENSURED_COLLECTIONS: dict[str, int] = {}


class SharedQdrantClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.base_url = resolve_qdrant_url()
        self.collection_name = resolve_qdrant_collection_name()
        self.api_key = resolve_qdrant_api_key()
        self._http_client = http_client

    def upsert_article_embedding(self, **kwargs) -> str:
        vector = kwargs["vector"]
        dimensions = len(vector)
        self._ensure_collection(dimensions=dimensions)
        point_id = build_article_embedding_point_id(
            article_key=kwargs["article_key"],
            worker_version=kwargs["worker_version"],
        )
        payload = {
            "article_id": kwargs["article_id"],
            "article_key": kwargs["article_key"],
            "url": kwargs["url"],
            "title": kwargs["title"],
            "summary": kwargs["summary"],
            "company_id": kwargs["company_id"],
            "company": kwargs["company"],
            "country": normalize_qdrant_country(kwargs["country"]),
            "published_at": published_at_to_unix_seconds(kwargs["published_at"]),
            "feeds": parse_payload_feeds(kwargs["feeds"]),
            "authors": parse_payload_authors(kwargs["authors"]),
            "img_url": kwargs["img_url"],
        }
        response = self._request(
            method="PUT",
            path=f"/collections/{self.collection_name}/points?wait=true",
            json={
                "points": [
                    {
                        "id": point_id,
                        "vector": {"dense": vector},
                        "payload": payload,
                    }
                ],
            },
        )
        self._require_qdrant_success(response, "Unable to upsert embedding point")
        return point_id

    def get_article_embedding_point(self, *, article_key: str, worker_version: str):
        point_id = build_article_embedding_point_id(
            article_key=article_key,
            worker_version=worker_version,
        )
        response = self._request(
            method="POST",
            path=f"/collections/{self.collection_name}/points",
            json={"ids": [point_id], "with_payload": True, "with_vector": True},
        )
        self._require_qdrant_success(response, "Unable to read embedding point")
        points = response.json().get("result") or []
        if not points:
            return None
        return to_embedding_point_read(
            points[0],
            fallback_point_id=point_id,
            fallback_article_key=article_key,
        )

    def delete_point_ids(self, point_ids: list[str]) -> None:
        unique_point_ids = sorted({point_id for point_id in point_ids if point_id})
        if not unique_point_ids:
            return
        response = self._request(
            method="POST",
            path=f"/collections/{self.collection_name}/points/delete?wait=true",
            json={"points": unique_point_ids},
        )
        self._require_qdrant_success(response, "Unable to delete embedding points")

    def scroll_article_embedding_points(
        self,
        *,
        limit: int,
        offset: str | None = None,
    ):
        payload: dict[str, object] = {
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        }
        if offset is not None:
            payload["offset"] = offset
        response = self._request(
            method="POST",
            path=f"/collections/{self.collection_name}/points/scroll",
            json=payload,
        )
        self._require_qdrant_success(response, "Unable to scroll embedding points")
        result = response.json().get("result") or {}
        items = [to_embedding_point_summary_read(point) for point in (result.get("points") or [])]
        next_offset = result.get("next_page_offset")
        return items, (str(next_offset) if next_offset is not None else None)

    def search_similar_article_embeddings(
        self,
        *,
        article_id: int,
        limit: int,
    ) -> list[QdrantScoredArticleEmbeddingPointRead]:
        response = self._request(
            method="POST",
            path=f"/collections/{self.collection_name}/points/recommend",
            json={
                "positive": [article_id],
                "using": "dense",
                "limit": max(1, int(limit)),
                "with_payload": True,
                "with_vector": False,
            },
        )
        self._require_qdrant_success(response, "Unable to search similar embedding points")
        return [to_scored_point_read(point) for point in (response.json().get("result") or [])]

    def search_sparse_article_embeddings(self, *, sparse_indices: list[int], sparse_values: list[float], limit: int, country: str | None = None, company_id: int | None = None, author_id: int | None = None, published_from=None):
        return self._search_named_article_embeddings(
            vector_name="sparse",
            vector={"indices": sparse_indices, "values": sparse_values},
            limit=limit,
            country=country,
            company_id=company_id,
            author_id=author_id,
            published_from=published_from,
        )

    def search_dense_article_embeddings(self, *, dense_vector: list[float], limit: int, article_ids: list[int] | None = None, country: str | None = None, company_id: int | None = None, author_id: int | None = None, published_from=None):
        return self._search_named_article_embeddings(
            vector_name="dense",
            vector=dense_vector,
            limit=limit,
            article_ids=article_ids,
            country=country,
            company_id=company_id,
            author_id=author_id,
            published_from=published_from,
        )

    def check_ready(self) -> None:
        response = self._request(method="GET", path="/collections")
        self._require_qdrant_success(response, "Unable to read Qdrant collections")

    def rebuild_collection(self, *, dimensions: int) -> None:
        delete_response = self._request(method="DELETE", path=f"/collections/{self.collection_name}")
        if delete_response.status_code != 404:
            self._require_qdrant_success(delete_response, "Unable to delete Qdrant collection")
        ENSURED_COLLECTIONS.pop(self.collection_name, None)
        create_response = self._request(
            method="PUT",
            path=f"/collections/{self.collection_name}",
            json=build_qdrant_collection_config(dimensions),
        )
        self._require_qdrant_success(create_response, "Unable to recreate Qdrant collection")
        self._ensure_payload_indexes()
        ENSURED_COLLECTIONS[self.collection_name] = dimensions

    def _search_named_article_embeddings(self, *, vector_name: str, vector, limit: int, article_ids: list[int] | None = None, country: str | None = None, company_id: int | None = None, author_id: int | None = None, published_from=None):
        payload: dict[str, object] = {
            "vector": {"name": vector_name, "vector": vector},
            "limit": max(1, int(limit)),
            "with_payload": True,
            "with_vector": False,
        }
        filter_payload = build_qdrant_source_search_filter(
            article_ids=article_ids,
            country=country,
            company_id=company_id,
            author_id=author_id,
            published_from=published_from,
        )
        if filter_payload is not None:
            payload["filter"] = filter_payload
        response = self._request(
            method="POST",
            path=f"/collections/{self.collection_name}/points/search",
            json=payload,
        )
        self._require_qdrant_success(response, "Unable to search embedding points")
        return [to_scored_point_read(point) for point in (response.json().get("result") or [])]

    def _ensure_collection(self, *, dimensions: int) -> None:
        cached_dimensions = ENSURED_COLLECTIONS.get(self.collection_name)
        if cached_dimensions == dimensions:
            return
        response = self._request(method="GET", path=f"/collections/{self.collection_name}")
        if response.status_code == 404:
            create_response = self._request(
                method="PUT",
                path=f"/collections/{self.collection_name}",
                json=build_qdrant_collection_config(dimensions),
            )
            self._require_qdrant_success(create_response, "Unable to create Qdrant collection")
            self._ensure_payload_indexes()
            ENSURED_COLLECTIONS[self.collection_name] = dimensions
            return
        self._require_qdrant_success(response, "Unable to read Qdrant collection")
        payload = response.json().get("result", {})
        config = payload.get("config", {})
        params = config.get("params", {})
        vectors = params.get("vectors", {})
        dense_config = vectors.get("dense") if isinstance(vectors, dict) else {}
        remote_dimensions = int((dense_config or {}).get("size") or vectors.get("size") or 0)
        if remote_dimensions != dimensions:
            raise QdrantIndexingError(
                "Qdrant collection dimension mismatch: "
                f"expected {dimensions}, found {remote_dimensions}"
            )
        self._ensure_payload_indexes()
        ENSURED_COLLECTIONS[self.collection_name] = dimensions

    def _ensure_payload_indexes(self) -> None:
        for field_name, field_schema in (
            ("country", "keyword"),
            ("published_at", "integer"),
            ("company_id", "integer"),
        ):
            response = self._request(
                method="PUT",
                path=f"/collections/{self.collection_name}/index",
                json={"field_name": field_name, "field_schema": field_schema},
            )
            self._require_qdrant_success(
                response,
                f"Unable to create Qdrant payload index for {field_name}",
            )

    def _request(self, *, method: str, path: str, json: dict | None = None) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                headers=self._build_headers(),
            )
        with httpx.Client(timeout=20.0) as client:
            return client.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=json,
                headers=self._build_headers(),
            )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key is not None:
            headers["api-key"] = self.api_key
        return headers

    def _require_qdrant_success(self, response: httpx.Response, message: str) -> None:
        if response.status_code >= 400:
            raise QdrantIndexingError(f"{message}: HTTP {response.status_code} - {response.text}")
        payload = response.json()
        if payload.get("status") not in (None, "ok"):
            raise QdrantIndexingError(f"{message}: unexpected Qdrant payload {payload}")
