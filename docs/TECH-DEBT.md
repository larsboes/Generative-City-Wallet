# Technical Debt Tracker

## Open items

- **Pyright baseline (API package)**
  - **Scope:** `apps/api/src/spark/`
  - **Current status:** `uv run pyright apps/api/src/spark/` reports **28 errors**.
  - **Hotspots:** `agents/agent.py`, `graph/repository.py`, `graph/{migrations,schema}.py`, `services/{composite,offer_generator}.py`, `routers/vendors.py`.
  - **Tracking note:** keep this debt separate from monorepo structure work; address in a dedicated typing pass.

