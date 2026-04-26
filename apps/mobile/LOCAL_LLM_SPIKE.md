# Local LLM integration spike (Expo + native module)

This spike prepares the React Native app for on-device Gemma inference while
keeping current backend integration unchanged.

## What is implemented in JS/TS

- `src/local-llm/toolSchema.ts`
  - `set_intent_vector_fields` schema with `IntentVector`-aligned keys.
  - optional `query_preference_graph` stub (not executed yet).
- `src/local-llm/intentMapper.ts`
  - deterministic map from tool arguments to `IntentVector`.
- `src/local-llm/inferenceBridge.ts`
  - Fully implements pure PWA/WebGPU local inference via `@mlc-ai/web-llm`.
  - Maintains bridge fallback for `NativeModules.SparkLocalLLM.runIntentInference` on iOS/Android.

## Native work expected after `expo prebuild`

- iOS Swift module implementing `SparkLocalLLM`.
- Android Kotlin module implementing `SparkLocalLLM`.
- Both should accept:
  - `user_text`
  - tool schema payload
  - optional tools list
- Both should return:
  - `tool_name`
  - `arguments` (JSON)
  - optional `raw_text`

## References

- [Function Calling Guide](https://github.com/google-ai-edge/gallery/blob/main/Function_Calling_Guide.md)
- [Gemma Mobile Actions](https://ai.google.dev/gemma/docs/mobile-actions)
- [AI Edge Gallery repo](https://github.com/google-ai-edge/gallery)

