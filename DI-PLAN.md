# DI-PLAN — Moving to Strict Clean Architecture

This plan outlines the refactoring strategy to introduce **Dependency Injection (DI)** and **Domain Events**. 

**Primary Goal:** Enable high-speed parallel evaluation harnesses ( RLHF / Prompt Tuning) by swapping IO-bound infrastructure for in-memory mocks.

---

## 1. Architectural Vision

Currently, services like `offer_decision.py` instantiate repositories or use `db_path` directly. This creates "Impure Logic."

**Target State:**
- **Domain Layer:** Pure business logic. Receives Interfaces (ABCs), not concrete classes.
- **Infrastructure Layer:** Implements those Interfaces (SQLite, Neo4j, Redis).
- **Application Layer:** Orchestrates the two using FastAPI `Depends` or a Container.

---

## 2. Refactoring Steps

### Phase 1: Interface Definition (The Contract)
Define Abstract Base Classes in a new `spark/domain/` directory.

```python
# apps/api/src/spark/domain/interfaces.py
from abc import ABC, abstractmethod

class IOfferRepository(ABC):
    @abstractmethod
    def get_session_state(self, session_id: str): ...
    
    @abstractmethod
    def list_candidates(self, grid_cell: str): ...
```

### Phase 2: Service Refactoring (Constructor Injection)
Modify services to accept the interface.

```python
# Before
def decide_offer(db_path: str):
    repo = OfferDecisionRepository(db_path)
    ...

# After (Pure Domain)
def decide_offer(repo: IOfferRepository):
    state = repo.get_session_state(...)
    ...
```

### Phase 3: The Evaluation Harness (The Career Win)
With DI, you can now run 10,000 simulations in seconds without touching a disk.

```python
# tests/evals/test_parallel_prompt_tuning.py
class MockRepo(IOfferRepository):
    def get_session_state(self, id): return FakeState()

# Now run decide_offer() in a massive loop with different AI temperatures
results = [decide_offer(MockRepo()) for _ in range(10000)]
```

---

## 3. Domain Events (Async Resilience)

Move "Side Effects" (Graph updates, Audit logging) out of the main request path.

**Pattern:**
1. `OfferService` generates an offer.
2. `OfferService` publishes an `OfferGenerated` event to an `EventBus`.
3. `GraphWorker` (Subscribed to the bus) updates Neo4j asynchronously.

**Benefit:** If Neo4j has 500ms latency, the user doesn't feel it. The API response time stays under 50ms.

---

## 4. Implementation Roadmap (Branch: `feat/strict-clean-architecture`)

1. **Sprint A: Dependency Inversion**
   - Define `IGraphRepository`, `IVenueRepository`, `IDensityRepository`.
   - Update `offer_decision.py` and `composite.py` to use injected repos.
   - Use FastAPI `Depends()` in routers to inject the concrete SQLite/Neo4j versions.

2. **Sprint B: In-Memory Eval Harness**
   - Create a `MockRepository` implementation.
   - Build a `scripts/evals/` benchmark that runs the decision engine against 1,000 scenarios in memory.

3. **Sprint C: Event-Driven Learning**
   - Introduce a simple internal `EventBus`.
   - Move Neo4j learning writes from `redemption.py` to an async event handler.

---

## Why this matters for Anthropic/DeepMind:
Senior AI Engineers don't just write prompts; they build **Infrastructure for Certainty**. By implementing this, you prove you can build a system that is **Measurable** (via the Eval Harness) and **Resilient** (via Domain Events).
