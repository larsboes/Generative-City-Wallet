import json
from pathlib import Path

from spark.models.context import CompositeContextState, IntentVector


def _fixture(path: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "tests" / "fixtures" / "local_llm" / path


def test_intent_vector_fixtures_are_valid() -> None:
    payload = json.loads(_fixture("intent_vectors.json").read_text(encoding="utf-8"))
    assert len(payload) >= 2
    for row in payload:
        IntentVector.model_validate(row)


def test_composite_context_fixtures_are_valid() -> None:
    payload = json.loads(
        _fixture("composite_context_states.json").read_text(encoding="utf-8")
    )
    assert len(payload) >= 2
    for row in payload:
        CompositeContextState.model_validate(row)
