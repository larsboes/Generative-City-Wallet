import type { GenerateOfferRequest, OfferObject } from "@spark/shared";

function apiBase(): string {
  return (import.meta.env.VITE_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");
}

export async function getHealth(): Promise<{ status: string }> {
  const r = await fetch(`${apiBase()}/api/v1/health`);
  if (!r.ok) throw new Error(`health ${r.status}`);
  return r.json();
}

export async function postGenerateOffer(req: GenerateOfferRequest): Promise<OfferObject> {
  const r = await fetch(`${apiBase()}/api/v1/offers/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`generate ${r.status}: ${t.slice(0, 500)}`);
  }
  return r.json();
}
