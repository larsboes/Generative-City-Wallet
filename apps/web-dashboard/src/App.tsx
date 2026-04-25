import type { IntentVector } from "@spark/shared";

const _exampleIntent: IntentVector = {
  grid_cell: "demo",
  movement_mode: "browsing",
  time_bucket: "lunch",
  weather_need: "neutral",
  social_preference: "neutral",
  price_tier: "mid",
  recent_categories: [],
  dwell_signal: false,
  battery_low: false,
  session_id: "dashboard-scaffold",
};

void _exampleIntent;

export function App() {
  return (
    <main className="shell">
      <h1>Spark merchant dashboard</h1>
      <p>
        Vite + React scaffold. Shared contracts load from{" "}
        <code>@spark/shared</code> (see <code>App.tsx</code>).
      </p>
      <p className="muted">
        API base URL and auth will follow the same env pattern as mobile once
        wired.
      </p>
    </main>
  );
}
