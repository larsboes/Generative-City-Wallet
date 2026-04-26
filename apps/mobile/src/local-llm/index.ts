export { runIntentInference } from "./inferenceBridge";
export { DEFAULT_INTENT_VECTOR, mapToolArgsToIntent } from "./intentMapper";
export { applyStravaSignalToIntent, deriveSourceSignals } from "./sourceSignals";
export { INTENT_TOOL_SCHEMA, OPTIONAL_KG_TOOLS } from "./toolSchema";
export type { IntentToolArgs } from "./toolSchema";
export type { ActivitySignalInput } from "./sourceSignals";
export {
  buildStravaAuthorizeUrl,
  deriveStravaSignal,
  disconnectStrava,
  exchangeCodeForToken,
  fetchRecentStravaActivities,
  loadStravaTokenSet,
  parseStravaCallbackUrl,
  refreshStravaToken,
  type ParsedStravaCallback,
  type DerivedStravaSignal,
  type StravaActivitySummary,
  type StravaTokenSet,
} from "../api/strava";

