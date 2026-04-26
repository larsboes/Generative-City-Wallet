# ADR 0001: Clean Architecture and DDD-Inspired Direction

- Status: accepted
- Date: 2026-04-26

## Context

The codebase evolved quickly through planning and implementation iterations. Recent refactors improved structure (`agents`, `repositories`, `models`, `services`), but without explicit architectural constraints the system can drift back toward mixed responsibilities.

We need:
- predictable code placement,
- stable domain boundaries,
- enforceable import directions,
- and lightweight documentation that can be maintained during rapid delivery.

## Decision

Adopt a clean, DDD-inspired structure with explicit layer ownership:

- `routers` for transport concerns,
- `services` for deterministic business policy/orchestration,
- `repositories` for persistence adapters,
- `models` for boundary/domain types,
- `db` for connection/schema/bootstrap helpers,
- `agents` for LLM orchestration adapters.

Enforce selected boundaries in CI using:
- `scripts/dev/check_architecture_boundaries.py`

Document rules and placement in:
- `docs/architecture/ARCHITECTURE-GUARDRAILS.md`
- `docs/architecture/CODE-MAP.md`

## Consequences

Positive:
- faster onboarding and clearer ownership by folder,
- lower chance of transport/persistence leakage into policy code,
- easier refactors and safer feature expansion (OCR, wallet seeding, Spark Wave).

Trade-offs:
- some changes will require touching docs + guard script together,
- strict boundaries may occasionally require explicit adapter/wrapper code.

## Non-goals

- No full tactical DDD rewrite (aggregates/entities/value objects across all modules).
- No immediate module/package split beyond current repository layout.
- No introduction of heavy architecture tooling; keep checks lightweight.
