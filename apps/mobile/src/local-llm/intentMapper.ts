import type { IntentVector } from "@spark/shared";

import type { IntentToolArgs } from "./toolSchema";

export const DEFAULT_INTENT_VECTOR: IntentVector = {
  grid_cell: "STR-MITTE-047",
  movement_mode: "browsing",
  time_bucket: "unknown",
  weather_need: "neutral",
  social_preference: "neutral",
  price_tier: "mid",
  recent_categories: [],
  dwell_signal: false,
  battery_low: false,
  session_id: "local-llm-session",
  activity_signal: "none",
  activity_source: "movement_inferred",
  activity_confidence: 0.0,
};

/**
 * Deterministic mapper from tool-call arguments to `IntentVector`.
 * This allows testing parser + mapping without loading native model runtime.
 */
export function mapToolArgsToIntent(
  args: IntentToolArgs,
  previous: IntentVector = DEFAULT_INTENT_VECTOR,
): IntentVector {
  return {
    ...previous,
    ...args,
    recent_categories: args.recent_categories ?? previous.recent_categories,
    session_id: args.session_id ?? previous.session_id,
  };
}

