---
task: project architecture checkup gaps and solidity
slug: 20260426-120000_project-architecture-checkup
effort: deep
phase: complete
progress: 40/40
mode: interactive
started: 2026-04-26T12:00:00Z
updated: 2026-04-26T12:20:00Z
---

## Context

Full architecture audit of Generative-City-Wallet post large merge (250 files, +19k lines). Three parallel exploration agents covered: API internals, infrastructure/docs, and tests/mobile/contracts. The goal is to find what's solid, what's missing, and what needs attention before the project moves forward.

### Risks
- Large surface area: 104 Python files, 98 Pydantic models, 28 services, 13 repos
- DI not yet implemented despite ADR + plan existing
- Hackathon-era shortcuts still in production code path (CORS, Redis ghost)

## Criteria

- [x] ISC-1: Redis in docker-compose but never imported in backend code verified
- [x] ISC-2: CORS wildcard origin confirmed in main.py
- [x] ISC-3: API versioning absence confirmed (no /v1/ prefix anywhere)
- [x] ISC-4: DI coupling confirmed: services pass db_path strings directly
- [x] ISC-5: Duplicate Fluent Bit configs identified (infra/pipeline vs infra/fluentbit)
- [x] ISC-6: Long-horizon identity gap confirmed per PLAN.md
- [x] ISC-7: composite.py god-class confirmed (15+ signal orchestration)
- [x] ISC-8: offer_decision.py bloat confirmed (558 lines, multi-responsibility)
- [x] ISC-9: repositories/redemption.py bloat confirmed (580 lines, 4 concerns)
- [x] ISC-10: Wave rate-limiting in data layer confirmed
- [x] ISC-11: Security scan non-blocking (Trivy exit 0) confirmed
- [x] ISC-12: CVE-2026-3219 ignored in ci.yml confirmed
- [x] ISC-13: Missing anti-corruption layer for Payone confirmed
- [x] ISC-14: Magic numbers scattered in services confirmed
- [x] ISC-15: 98 Pydantic models organized in 13 domain modules verified
- [x] ISC-16: TS/Python contract parity CI guard verified
- [x] ISC-17: Architecture boundary guards (3 CI scripts) verified
- [x] ISC-18: 6-layer model (routers→services→repos→models→db→agents) verified
- [x] ISC-19: Deterministic-first offer pipeline (rules→score→LLM→rails) verified
- [x] ISC-20: Idempotency guards present (graph event log, QR) verified
- [x] ISC-21: 28 unit + 10 integration tests covering critical paths verified
- [x] ISC-22: Explainability trace and attribution logging verified
- [x] ISC-23: Fluent Bit DLQ pipeline operational verified
- [x] ISC-24: DI-PLAN.md + ADR-0001 roadmap exists and is sound verified
- [x] ISC-25: transactions.py model file overcrowded (23 models) confirmed
- [x] ISC-26: infra/pipeline/ orphaned (not mounted in docker-compose) confirmed
- [x] ISC-27: Data source stubs: Luma live, transit API, health APIs confirmed
- [x] ISC-28: services/ directory approaching navigation complexity (28 modules) noted
- [x] ISC-29: graph/store/ and graph/queries/ split assessed (sound design)
- [x] ISC-30: on-device LLM dual-runtime strategy verified (WebGPU + native)
- [x] ISC-31: Strava OAuth integration verified (mobile only, not server-side)
- [x] ISC-32: SQLite for transactional + Neo4j for KG separation is sound
- [x] ISC-33: Error handling thin (2-helper errors.py) — no global exception handler
- [x] ISC-34: No authentication/auth middleware on any endpoint confirmed
- [x] ISC-35: main.py mounts 11 routers with no prefix versioning confirmed
- [x] ISC-36: config.py centralization partial — magic numbers still in services
- [x] ISC-37: Graph maintenance (decay, cleanup) runs on startup + scheduled
- [x] ISC-38: Taskfile.yml covers dev/demo/test workflows adequately
- [x] ISC-39: Mobile inferenceBridge strict tool-call enforcement verified
- [x] ISC-40: Offer pipeline audit trail (offer_audit_log table) comprehensive

## Verification

All criteria verified via parallel agent exploration + direct file reads of main.py, errors.py, docker-compose.yml, ci.yml, PLAN.md, DI-PLAN.md, ADR-0001.
