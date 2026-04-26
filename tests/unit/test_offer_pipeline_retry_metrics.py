from __future__ import annotations

from types import SimpleNamespace

import pytest

from spark.services import offer_pipeline as pipeline


@pytest.mark.asyncio
async def test_llm_retry_metrics_record_success_on_retry(monkeypatch):
    attempts = {"count": 0}
    base = pipeline.get_offer_pipeline_metrics()

    async def flaky_llm(_state):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient")
        return SimpleNamespace()

    async def no_sleep(_delay):
        return None

    monkeypatch.setattr("spark.services.offer_pipeline.generate_offer_llm", flaky_llm)
    monkeypatch.setattr("spark.services.offer_pipeline.asyncio.sleep", no_sleep)

    result = await pipeline._generate_offer_llm_with_retry(SimpleNamespace())
    assert result is not None

    after = pipeline.get_offer_pipeline_metrics()
    assert after["llm_calls_total"] >= base["llm_calls_total"] + 2
    assert after["llm_retries_total"] >= base["llm_retries_total"] + 1
    assert (
        after["llm_success_on_retry_total"] >= base["llm_success_on_retry_total"] + 1
    )
    assert after["llm_failures_total"] >= base["llm_failures_total"] + 1
