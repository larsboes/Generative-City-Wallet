#!/usr/bin/env python3
"""
Local-LLM smoke runner for frozen fixtures.

Default mode validates fixture schemas and parser robustness.
Optional mode runs a Hugging Face local model (laptop-only sandbox).

Usage:
  uv run python scripts/dev/smoke_local_llm.py
  uv run python scripts/dev/smoke_local_llm.py --hf --model-id google/gemma-4-E4B-it
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api" / "src"))

from spark.models.contracts import (  # noqa: E402
    CompositeContextState,
    IntentVector,
    LLMOfferOutput,
)
from spark.services.offer_generator import _parse_llm_json_blob, build_user_prompt  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "local_llm"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_fixtures() -> list[CompositeContextState]:
    intent_raw = _load_json(FIXTURE_DIR / "intent_vectors.json")
    composite_raw = _load_json(FIXTURE_DIR / "composite_context_states.json")

    for idx, row in enumerate(intent_raw, start=1):
        IntentVector.model_validate(row)
        print(f"Intent fixture #{idx} valid")

    states: list[CompositeContextState] = []
    for idx, row in enumerate(composite_raw, start=1):
        state = CompositeContextState.model_validate(row)
        states.append(state)
        print(f"Composite fixture #{idx} valid")
    return states


def _parser_regression(states: list[CompositeContextState]) -> tuple[int, int]:
    samples: list[str] = []
    for state in states:
        prompt = build_user_prompt(state)
        base = {
            "content": {
                "headline": "Kurz bei [MERCHANT_NAME]",
                "subtext": "Jetzt [DISCOUNT]% sichern",
                "cta_text": "Jetzt holen",
                "emotional_hook": "Passt genau in deinen Moment.",
            },
            "genui": {
                "color_palette": "warm_amber",
                "typography_weight": "medium",
                "background_style": "gradient",
                "imagery_prompt": "warm cafe mood",
                "urgency_style": "gentle_pulse",
                "card_mood": "cozy",
            },
            "framing_band_used": state.conflict_resolution.framing_band
            or "quiet_intentional",
        }
        plain = json.dumps(base)
        fenced = f"```json\n{plain}\n```"
        samples.extend([plain, fenced, plain + "\n"])
        print(
            f"Prepared parser samples for session {state.session_id} ({len(prompt)} chars)"
        )

    ok = 0
    for sample in samples:
        parsed = _parse_llm_json_blob(sample)
        LLMOfferOutput.model_validate(parsed)
        ok += 1
    return ok, len(samples)


def _run_hf(
    states: list[CompositeContextState], model_id: str, max_new_tokens: int
) -> None:
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - env-dependent
        raise SystemExit(
            "Transformers not installed. Install optional deps first, then retry with --hf."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id)

    parsed_ok = 0
    for state in states:
        prompt = build_user_prompt(state)
        messages = [
            {
                "role": "user",
                "content": (
                    "Return strict JSON matching Spark schema. No markdown.\n\n"
                    + prompt
                ),
            }
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(text, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
        generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1] :])
        try:
            raw = _parse_llm_json_blob(generated)
            LLMOfferOutput.model_validate(raw)
            parsed_ok += 1
            print(f"HF parsed OK: {state.session_id}")
        except Exception as exc:
            print(f"HF parse failed: {state.session_id} ({exc})")
    print(f"HF parse rate: {parsed_ok}/{len(states)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test local-LLM fixture flow")
    parser.add_argument(
        "--hf", action="store_true", help="Run optional HF sandbox mode"
    )
    parser.add_argument("--model-id", default="google/gemma-4-E4B-it")
    parser.add_argument("--max-new-tokens", type=int, default=180)
    args = parser.parse_args()

    states = _validate_fixtures()
    ok, total = _parser_regression(states)
    print(f"Parser regression rate: {ok}/{total}")

    if args.hf:
        _run_hf(states, model_id=args.model_id, max_new_tokens=args.max_new_tokens)

    print("Local-LLM smoke complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
