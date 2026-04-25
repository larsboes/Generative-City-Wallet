/**
 * Thin HTTP client for the Spark FastAPI backend.
 * IntentVector shape is shared with Python via ../src/shared/contracts.ts
 */
import type { IntentVector } from "../../../src/shared/contracts";

const defaultBase = "http://127.0.0.1:8000";

function apiBase(): string {
  const b = process.env.EXPO_PUBLIC_SPARK_API_BASE ?? defaultBase;
  return b.replace(/\/$/, "");
}

export async function postComposite(intent: IntentVector): Promise<unknown> {
  const r = await fetch(`${apiBase()}/api/context/composite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(intent),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`composite ${r.status}: ${t.slice(0, 500)}`);
  }
  return r.json();
}
