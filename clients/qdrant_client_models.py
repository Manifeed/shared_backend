from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5


class QdrantIndexingError(RuntimeError):
    """Raised when a Qdrant operation fails."""


@dataclass(frozen=True)
class QdrantArticleEmbeddingPointRead:
    point_id: str
    article_id: int | None
    article_key: str
    company_id: int | None
    company: str | None
    country: str
    published_at: datetime | None
    url: str | None
    title: str | None
    summary: str | None
    feeds: list[dict[str, object]]
    authors: list[dict[str, object]]
    img_url: str | None
    vector: list[float]


@dataclass(frozen=True)
class QdrantArticleEmbeddingPointSummaryRead:
    point_id: str
    article_id: int | None
    article_key: str | None


@dataclass(frozen=True)
class QdrantScoredArticleEmbeddingPointRead:
    point_id: str
    score: float
    article_id: int | None
    article_key: str | None
    published_at: datetime | None = None


def build_article_embedding_point_id(
    *,
    article_key: str,
    worker_version: str,
) -> str:
    return str(uuid5(NAMESPACE_URL, f"{article_key}:{worker_version}"))


def build_qdrant_source_search_filter(
    *,
    article_ids: list[int] | None = None,
    country: str | None,
    company_id: int | None,
    author_id: int | None,
    published_from: datetime | None,
) -> dict[str, list[dict[str, object]]] | None:
    must_conditions: list[dict[str, object]] = []
    if article_ids:
        must_conditions.append({"has_id": sorted({int(article_id) for article_id in article_ids})})
    if country:
        must_conditions.append({"key": "country", "match": {"value": country}})
    if company_id is not None:
        must_conditions.append({"key": "company_id", "match": {"value": company_id}})
    if author_id is not None:
        must_conditions.append(
            {
                "nested": {
                    "key": "authors",
                    "filter": {
                        "must": [{"key": "id", "match": {"value": author_id}}],
                    },
                },
            }
        )
    range_filter: dict[str, int] = {}
    if published_from is not None:
        published_from_utc = (
            published_from.astimezone(UTC)
            if published_from.tzinfo is not None
            else published_from.replace(tzinfo=UTC)
        )
        range_filter["gte"] = int(published_from_utc.timestamp())
    if range_filter:
        must_conditions.append({"key": "published_at", "range": range_filter})
    if not must_conditions:
        return None
    return {"must": must_conditions}


def build_qdrant_collection_config(dimensions: int) -> dict[str, object]:
    return {
        "vectors": {
            "dense": {
                "size": dimensions,
                "distance": "Cosine",
            },
        },
        "sparse_vectors": {
            "sparse": {},
        },
    }


def published_at_to_unix_seconds(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        normalized = value.replace(tzinfo=UTC)
    else:
        normalized = value.astimezone(UTC)
    return int(normalized.timestamp())


def parse_qdrant_published_at(value: object) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


def parse_payload_feeds(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    feeds: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        feed_id = item.get("id")
        if not isinstance(feed_id, int):
            continue
        feeds.append(
            {
                "id": feed_id,
                "section": str(item.get("section")) if item.get("section") is not None else None,
            }
        )
    return feeds


def parse_payload_authors(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    authors: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        author_id = item.get("id")
        if not isinstance(author_id, int):
            continue
        authors.append(
            {
                "id": author_id,
                "name": str(item.get("name")) if item.get("name") is not None else "",
            }
        )
    return authors


def payload_article_id(payload: dict[str, object]) -> int | None:
    article_id = payload.get("article_id")
    return int(article_id) if isinstance(article_id, int) else None


def payload_article_key(payload: dict[str, object], fallback: str | None = None) -> str | None:
    article_key = payload.get("article_key")
    if article_key is None:
        return fallback
    return str(article_key)


def to_embedding_point_summary_read(point: dict[str, object]) -> QdrantArticleEmbeddingPointSummaryRead:
    payload = point.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    return QdrantArticleEmbeddingPointSummaryRead(
        point_id=str(point.get("id")),
        article_id=payload_article_id(payload),
        article_key=payload_article_key(payload),
    )


def to_scored_point_read(point: dict[str, object]) -> QdrantScoredArticleEmbeddingPointRead:
    payload = point.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    return QdrantScoredArticleEmbeddingPointRead(
        point_id=str(point.get("id")),
        score=float(point.get("score") or 0.0),
        article_id=payload_article_id(payload),
        article_key=payload_article_key(payload),
        published_at=parse_qdrant_published_at(payload.get("published_at")),
    )


def to_embedding_point_read(
    point: dict[str, object],
    *,
    fallback_point_id: str,
    fallback_article_key: str,
) -> QdrantArticleEmbeddingPointRead:
    payload = point.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    raw_vector = point.get("vector")
    dense_vector = raw_vector.get("dense") if isinstance(raw_vector, dict) else raw_vector
    if not isinstance(dense_vector, list):
        raise QdrantIndexingError(
            f"Unable to read embedding point {fallback_point_id}: vector missing from payload"
        )
    return QdrantArticleEmbeddingPointRead(
        point_id=str(point.get("id") or fallback_point_id),
        article_id=payload_article_id(payload),
        article_key=payload_article_key(payload, fallback_article_key) or fallback_article_key,
        company_id=int(payload["company_id"]) if payload.get("company_id") is not None else None,
        company=str(payload["company"]) if payload.get("company") is not None else None,
        country=normalize_qdrant_country(payload.get("country")),
        published_at=parse_qdrant_published_at(payload.get("published_at")),
        url=str(payload["url"]) if payload.get("url") is not None else None,
        title=str(payload["title"]) if payload.get("title") is not None else None,
        summary=str(payload["summary"]) if payload.get("summary") is not None else None,
        feeds=parse_payload_feeds(payload.get("feeds")),
        authors=parse_payload_authors(payload.get("authors")),
        img_url=str(payload["img_url"]) if payload.get("img_url") is not None else None,
        vector=[float(value) for value in dense_vector],
    )


def normalize_qdrant_country(value: object) -> str:
    if value is None:
        return "xx"
    normalized = str(value).strip().casefold()[:2]
    return normalized or "xx"
