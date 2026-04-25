## Learned User Preferences

- Treat **Gemma 4 on phones** via **Google AI Edge / LiteRT** as the primary on-device LLM direction; **FunctionGemma** is fine as a small complementary tool-router; **Ollama or server-only “local LLM”** paths are optional dev convenience, not the main mobile story.
- When planning on-device LLM work, use **Google AI Edge Gallery** and the official **function-calling** materials as the default feasibility baseline on hardware.
- Uses **ATC archive** `rules-engine` and `orchestrator` folders as reference patterns when designing Neo4j graph behavior and orchestration-style flows.
- For the user knowledge graph, expects follow-through on **API-safe explainability** on offers, **decay** for stale preference weights, **idempotency keys** on graph event writes, **retention** for category/attribute preference edges (not only offer artifacts), and **simple graph migration/versioning**.

## Learned Workspace Facts

- **Neo4j** local database files live under **`data/neo4j/`**; graph integration code is under **`apps/api/src/spark/graph/`** with HTTP surface in **`apps/api/src/spark/routers/graph.py`**.
- Offer and context composition center on **`apps/api/src/spark/services/offer_generator.py`** and **`apps/api/src/spark/services/composite.py`**, alongside routers in **`apps/api/src/spark/routers/`** (offers, redemption, payone, etc.).
- Graph operations scripting includes **`scripts/run_graph_maintenance.py`** (cleanup, decay, migrations) and **`scripts/benchmark_offer_latency.py`** for comparing offer latency with Neo4j enabled vs disabled.
