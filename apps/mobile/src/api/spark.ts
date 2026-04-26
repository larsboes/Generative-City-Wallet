/**
 * Thin HTTP client for the Spark FastAPI backend.
 */
import type { IntentVector } from "@spark/shared";
import {
  deriveStravaSignal,
  fetchRecentStravaActivities,
  loadStravaTokenSet,
  type DerivedStravaSignal,
} from "./strava";
import { getOrCreateContinuityHint } from "./continuity";

const defaultBase = "http://127.0.0.1:8000";

function apiBase(): string {
  const b = process.env.EXPO_PUBLIC_SPARK_API_BASE ?? defaultBase;
  return b.replace(/\/$/, "");
}

export async function postComposite(intent: IntentVector): Promise<unknown> {
  const continuityHint = intent.continuity_hint ?? (await getOrCreateContinuityHint());
  const payload: IntentVector = {
    ...intent,
    continuity_hint: continuityHint,
  };

  const r = await fetch(`${apiBase()}/api/v1/context/composite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`composite ${r.status}: ${t.slice(0, 500)}`);
  }
  return r.json();
}

export async function getStravaSignalState(): Promise<{
  connected: boolean;
  signal: DerivedStravaSignal;
}> {
  const token = await loadStravaTokenSet();
  if (!token) {
    return {
      connected: false,
      signal: { hasRecentActivity: false, activityCount24h: 0, confidence: 0.0 },
    };
  }
  const activities = await fetchRecentStravaActivities();
  return {
    connected: true,
    signal: deriveStravaSignal(activities),
  };
}
