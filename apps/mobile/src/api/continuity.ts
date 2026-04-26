import { deleteSecureValue, getSecureValue, setSecureValue } from "./secureStore";

const CONTINUITY_HINT_KEY = "spark.continuity_hint.v1";

function createContinuityHint(): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 14);
  return `hint_${ts}${rand}`;
}

export async function getOrCreateContinuityHint(): Promise<string> {
  const existing = await getSecureValue(CONTINUITY_HINT_KEY);
  if (existing) {
    return existing;
  }
  const created = createContinuityHint();
  await setSecureValue(CONTINUITY_HINT_KEY, created);
  return created;
}

export async function rotateContinuityHint(): Promise<string> {
  const next = createContinuityHint();
  await setSecureValue(CONTINUITY_HINT_KEY, next);
  return next;
}

export async function clearContinuityHint(): Promise<void> {
  await deleteSecureValue(CONTINUITY_HINT_KEY);
}
