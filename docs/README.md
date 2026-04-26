# Spark — Documentation

This folder holds **current, implementation-aligned** documentation for the repo.  
Long-form product, pitch, and hackathon planning material lives under **[`planning/`](planning/README.md)**.

---

## Core documentation

| Doc | What it covers |
|-----|----------------|
| **[`ARCHITECTURE.md`](ARCHITECTURE.md)** | **How it works:** Main architecture overview and navigation. |
| **[`DEVELOPMENT.md`](DEVELOPMENT.md)** | **How to run it:** Workspaces, npm/turbo/uv commands, Docker, CI, import rules, and active tech debt. |
| **[`architecture/neo4j-graph.md`](architecture/neo4j-graph.md)** | **Graph deep dive:** Server-side user knowledge graph rules and runtime behavior. |
| **[`CONCEPT.md`](CONCEPT.md)** | **Why it exists:** Stable product concept and long-lived principles. |
| **[`architecture/context-signals.md`](architecture/context-signals.md)** | **Context model:** signal categories, composite usage, and runtime boundaries. |
| **[`architecture/offer-decision-engine.md`](architecture/offer-decision-engine.md)** | **Decision engine:** deterministic ranking, thresholding, and trace. |
| **[`architecture/llm-and-hard-rails.md`](architecture/llm-and-hard-rails.md)** | **LLM safety boundary:** deterministic recommendation vs generative framing and rails. |
| **[`architecture/ingress-and-canonicalization.md`](architecture/ingress-and-canonicalization.md)** | **Mapping boundary:** Fluent Bit ingress normalization vs Python canonical contracts. |
| **[`DATA-MODEL.md`](DATA-MODEL.md)** | **Data model:** contracts, SQLite tables, graph projection relationships, and ownership. |
| **[`architecture/consumer-app-surfaces.md`](architecture/consumer-app-surfaces.md)** | **Consumer surfaces:** in-app, push, lock-screen/widget behavior and flow. |
| **[`architecture/merchant-dashboard.md`](architecture/merchant-dashboard.md)** | **Business surfaces:** overview, rules, analytics, validation flow. |
| **[`architecture/data-simulation.md`](architecture/data-simulation.md)** | **Synthetic data layer:** transaction simulation, density signal, occupancy proxy. |

---

## Planning & Research archive


**[`planning/README.md`](planning/README.md)** — navigation by role and topic (merchant dashboard, consumer app, architecture, pitch, research).

---

## Current status vs planning

The planning docs are broader than what is currently implemented. Use this as a quick reality check:

- **Implemented now**
  - Deterministic offer selection path (`offer_decision`) with decision trace.
  - Pre-LLM graph guardrails (`GraphValidationService`).
  - Hard-rails LLM boundary (LLM for framing/content, not offer entitlement).
  - Offer lifecycle projection into Neo4j + idempotent projection guard.

- **Partially implemented**
  - Composite context and conflict resolution logic (core paths in place; still evolving).
  - On-device local LLM spike scaffolding and fixtures (not full production path yet).

- **Still planning-stage / missing from runtime**
  - OCR transit delay enrichment end-to-end.
  - Wallet pass cold-start seeding end-to-end.
  - Spark Wave/social coordination mechanics.
  - Full “advanced signals” rollout from `docs/planning/16-ADVANCED-SIGNALS.md`.

If you need the most accurate current behavior, start with `ARCHITECTURE.md` + `architecture/neo4j-graph.md`, then use planning docs for roadmap intent.
