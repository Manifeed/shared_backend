# shared_backend

Shared backend package for Manifeed microservices.

## What Belongs Here

This package only contains cross-service building blocks with no service-owned
business orchestration:

- shared application errors and exception handlers;
- Pydantic schemas for APIs and internal service payloads;
- pure domain helpers (`password_policy`, `user_identity`, `current_user`, `worker_identity`);
- security helpers for passwords, sessions, API keys, and secrets;
- inter-service authentication helpers;
- reusable internal HTTP client helpers.
- reusable low-level database/Qdrant clients shared by multiple services.

Each service keeps its own route handlers, service orchestration, and
service-specific integrations.

## Sharing Rule

- If a contract or helper is used by at least two services, it belongs in
  `shared_backend`.
- If code is a low-level reusable boundary client or pure helper used by at
  least two services, it belongs here.
- If code encodes a service-specific workflow or endpoint contract, it stays local.

## Change Workflow

1. Update the shared schema or helper in `shared_backend`.
2. Adapt the affected producers and consumers.
3. Add or update the contract tests.
4. Bump the `shared_backend` version in `pyproject.toml`.

## Build

Backend Docker images now build a local `manifeed-shared-backend` wheel from
the monorepo and install it into each image. No GitHub dependency is required
at build time anymore.
