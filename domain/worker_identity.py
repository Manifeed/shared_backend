from __future__ import annotations

from shared_backend.domain.user_identity import normalize_user_pseudo


def build_worker_name(*, pseudo: str, worker_type: str, worker_number: int) -> str:
    normalized_pseudo = normalize_user_pseudo(pseudo) or "worker"
    normalized_worker_type = _worker_type_slug(worker_type)
    normalized_worker_number = max(1, int(worker_number))
    return f"{normalized_pseudo}-{normalized_worker_type}-{normalized_worker_number}"


def _worker_type_slug(worker_type: str) -> str:
    if worker_type == "rss_scrapper":
        return "rss"
    if worker_type == "source_embedding":
        return "embedding"
    return normalize_user_pseudo(worker_type) or "worker"
