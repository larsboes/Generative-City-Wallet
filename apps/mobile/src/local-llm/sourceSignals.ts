import type { IntentVector } from "@spark/shared";
import type { DerivedStravaSignal } from "../api/strava";

export interface ActivitySignalInput {
  movementMode: IntentVector["movement_mode"];
  stravaRecentActivity?: boolean;
  stravaConfidence?: number;
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

  let confidence =
    source === "hybrid" ? 0.9 : source === "movement_inferred" ? 0.5 : 0.75;
  if (source === "strava" && typeof input.stravaConfidence === "number") {
    confidence = Math.max(0, Math.min(1, input.stravaConfidence));
  }

  return {
    ...intent,
    activity_signal: activitySignal,
    activity_source: source,
    activity_confidence: confidence,
    location_grid_accuracy_m: input.locationGridAccuracyM,
  };
}

export function applyStravaSignalToIntent(
  intent: IntentVector,
  movementMode: IntentVector["movement_mode"],
  stravaSignal: DerivedStravaSignal,
  locationGridAccuracyM?: number,
): IntentVector {
  return deriveSourceSignals(intent, {
    movementMode,
    stravaRecentActivity: stravaSignal.hasRecentActivity,
    stravaConfidence: stravaSignal.confidence,
    locationGridAccuracyM,
  });
}
