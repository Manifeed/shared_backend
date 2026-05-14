# shared_backend

Shared backend package for Manifeed microservices.

## What Belongs Here

This package only contains cross-service building blocks with no database
access and no business logic tied to a specific service:

- shared application errors and exception handlers;
- Pydantic schemas for APIs and internal service payloads;
- pure domain helpers (`password_policy`, `user_identity`, `current_user`, `worker_identity`);
- security helpers for passwords, sessions, API keys, and secrets;
- inter-service authentication helpers;
- reusable internal HTTP client helpers.

Each service keeps its own database clients, repositories, and local business
orchestration.

## Sharing Rule

- If a contract or helper is used by at least two services, it belongs in
  `shared_backend`.
- If code depends on a database, a service-specific endpoint, a business
  workflow, or an external integration owned by a single service, it stays
  local.

## Change Workflow

1. Update the shared schema or helper in `shared_backend`.
2. Adapt the affected producers and consumers.
3. Add or update the contract tests.
4. Bump the `shared_backend` version in `pyproject.toml`.

## Build

Backend Docker images now build a local `manifeed-shared-backend` wheel from
the monorepo and install it into each image. No GitHub dependency is required
at build time anymore.
