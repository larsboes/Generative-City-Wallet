import type { IntentVector } from "@spark/shared";

export type IntentToolArgs = Partial<
  Omit<IntentVector, "session_id" | "recent_categories">
> & {
  session_id?: string;
  recent_categories?: string[];
};

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

/**
 * Tool schema mirrored into the native local-LLM bridge prompt.
 * Keep argument names 1:1 with `IntentVector` keys where possible.
 */
export const INTENT_TOOL_SCHEMA: ToolDefinition = {
  name: "set_intent_vector_fields",
  description:
    "Fill Spark IntentVector fields from user utterance/context. Return only changed keys.",
  parameters: {
    type: "object",
    additionalProperties: false,
    properties: {
      grid_cell: { type: "string" },
      movement_mode: {
        type: "string",
        enum: [
          "browsing",
          "commuting",
          "stationary",
          "transit_waiting",
          "exercising",
          "post_workout",
          "cycling",
        ],
      },
      time_bucket: { type: "string" },
      weather_need: {
        type: "string",
        enum: [
          "warmth_seeking",
          "refreshment_seeking",
          "shelter_seeking",
          "neutral",
        ],
      },
      social_preference: {
        type: "string",
        enum: ["social", "quiet", "neutral"],
      },
      price_tier: {
        type: "string",
        enum: ["low", "mid", "high"],
      },
      recent_categories: {
        type: "array",
        items: { type: "string" },
      },
      dwell_signal: { type: "boolean" },
      battery_low: { type: "boolean" },
      activity_signal: {
        type: "string",
        enum: ["none", "active_recently", "post_workout", "resting"],
      },
      activity_source: {
        type: "string",
        enum: ["none", "strava", "native_health", "hybrid", "movement_inferred"],
      },
      activity_confidence: { type: "number", minimum: 0, maximum: 1 },
      location_grid_accuracy_m: {
        type: "integer",
        minimum: 10,
        maximum: 500,
      },
      session_id: { type: "string" },
    },
  },
};

export const OPTIONAL_KG_TOOLS: ToolDefinition[] = [
  {
    name: "query_preference_graph",
    description:
      "Optional future tool for client-side ranking hints. Stub only for now.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        top_k: { type: "integer", minimum: 1, maximum: 10 },
      },
    },
  },
];

