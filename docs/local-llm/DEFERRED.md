# Deferred local-LLM item

## Free-text -> social_preference classifier

Status: **deferred by plan** until the UI flow exists.

When resumed:

1. Add mobile UX surface for free-text or voice intent capture.
2. Add on-device classification prompt/tool that returns one of:
   - `social`
   - `quiet`
   - `neutral`
3. Keep fallback deterministic (`neutral`) on parse failure.
4. Add regression fixtures under `tests/fixtures/local_llm/`.

