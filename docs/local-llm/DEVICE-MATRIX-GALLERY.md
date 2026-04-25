# AI Edge Gallery Device Matrix (Flagship-only)

This file tracks the **Phase 1** benchmark pass for local LLM readiness on phones.

Scope constraints for this pass:

- Only **flagship/high-tier** iOS + Android devices.
- Primary model: **Gemma 4 E4B**.
- Optional comparison: **FunctionGemma** for tiny tool-routing workloads.
- Explicitly out of scope: mid-tier devices, E2B support matrix.

## Baseline runbook

1. Install Google AI Edge Gallery on each reference device.
2. Use equivalent prompt/tool scenarios per model run.
3. Record:
   - First token latency / prefill
   - Decode throughput
   - End-to-end tool-call completion time
   - Thermal behavior (steady state + throttling onset)
4. Repeat at least 5 runs per scenario and store p50/p95.

## Acceptance threshold (initial)

- E4B p95 end-to-end should remain within demo budget on both iOS and Android reference devices.
- No sustained throttling that breaks interactive UX in a 5-minute repeated run.

> Update thresholds once product UX budget is finalized.

## Results table

| Platform | Device | OS | Model | Scenario | p50 latency (ms) | p95 latency (ms) | Thermal note | Status |
|----------|--------|----|-------|----------|------------------|------------------|--------------|--------|
| Android | TBD flagship | TBD | Gemma 4 E4B | Tool call: intent extraction | TBD | TBD | TBD | Pending |
| iOS | TBD flagship | TBD | Gemma 4 E4B | Tool call: intent extraction | TBD | TBD | TBD | Pending |
| Android | TBD flagship | TBD | FunctionGemma (optional) | Tool call: intent extraction | TBD | TBD | TBD | Optional |
| iOS | TBD flagship | TBD | FunctionGemma (optional) | Tool call: intent extraction | TBD | TBD | TBD | Optional |

## Decision log

- [ ] E4B accepted on Android flagship baseline.
- [ ] E4B accepted on iOS flagship baseline.
- [ ] FunctionGemma included as optional tiny router.
- [ ] Mid-tier support intentionally deferred.

