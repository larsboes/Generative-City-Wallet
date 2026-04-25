# Spark — Documentation

This folder holds **current, implementation-aligned** documentation for the repo.  
Long-form product, pitch, and hackathon planning material lives under **[`planning/`](planning/README.md)**.

---

## Start here

| Doc | Audience | What it covers |
|-----|----------|----------------|
| **[`MONOREPO-STRUCTURE.md`](MONOREPO-STRUCTURE.md)** | Engineers + agents | **Workspaces, folders, npm/turbo commands**, scripts layout, contract guardrails |
| **[`REPOSITORY-OVERVIEW.md`](REPOSITORY-OVERVIEW.md)** | Engineers new to the repo | **Whole backend layout** — routers, services, SQLite vs Neo4j, hybrid offer pipeline, CI, Docker, tests |
| **[`USER-KNOWLEDGE-GRAPH-NEO4J.md`](USER-KNOWLEDGE-GRAPH-NEO4J.md)** | Backend, mobile, ops | **Server-side user knowledge graph (Neo4j)** — what it does today, APIs, model, env vars, limits |
| **[`TECH-DEBT.md`](TECH-DEBT.md)** | Maintainers | Active technical debt backlog (currently Pyright typing debt baseline) |
| **[`../README.md`](../README.md)** | Everyone | Product one-pager, **Graph Ops** (`curl` + cron for maintenance scripts) |

**Diagrams:** Mermaid + ASCII (architecture, fail-soft, graph topology, rule gate, startup/maintenance) live in [`USER-KNOWLEDGE-GRAPH-NEO4J.md`](USER-KNOWLEDGE-GRAPH-NEO4J.md).

---

## Planning archive

Design specs, build plans, and stakeholder docs were moved to:

**[`planning/README.md`](planning/README.md)** — navigation by role and topic (merchant dashboard, consumer app, architecture, pitch).

For the **original** on-device KG + SQLite narrative (still useful for product context), see **`planning/13-ON-DEVICE-AI-AND-KNOWLEDGE-GRAPH.md`**. The **server-primary Neo4j graph** is the source of truth for runtime behavior described in `USER-KNOWLEDGE-GRAPH-NEO4J.md`.
