import type { IntentVector } from "@spark/shared";

export interface ActivitySignalInput {
  movementMode: IntentVector["movement_mode"];
  stravaRecentActivity?: boolean;
  nativeHealthRecentActivity?: boolean;
  locationGridAccuracyM?: number;
}

export function deriveSourceSignals(
  intent: IntentVector,
  input: ActivitySignalInput,
): IntentVector {
  const strava = Boolean(input.stravaRecentActivity);
  const health = Boolean(input.nativeHealthRecentActivity);
  const source = strava && health ? "hybrid" : strava ? "strava" : health ? "native_health" : "movement_inferred";

  let activitySignal: IntentVector["activity_signal"] = "none";
  if (input.movementMode === "post_workout" || strava || health) {
    activitySignal = "post_workout";
  } else if (input.movementMode === "cycling" || input.movementMode === "exercising") {
    activitySignal = "active_recently";
  } else if (input.movementMode === "stationary") {
    activitySignal = "resting";
  }

  const confidence = source === "hybrid" ? 0.9 : source === "movement_inferred" ? 0.5 : 0.75;

  return {
    ...intent,
    activity_signal: activitySignal,
    activity_source: source,
    activity_confidence: confidence,
    location_grid_accuracy_m: input.locationGridAccuracyM,
  };
}
