# @spark/shared

TypeScript contracts shared by **mobile** and **web-dashboard**.

Python equivalents live in `apps/api/src/spark/models/contracts.py` — update both when the wire format changes.

CI runs `scripts/dev/check_contract_symbols.py` for a shallow name-level guardrail; extend the symbol list there when you add cross-boundary types (see `docs/MONOREPO-STRUCTURE.md`).
