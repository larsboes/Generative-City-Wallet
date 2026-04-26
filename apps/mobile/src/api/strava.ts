import { deleteSecureValue, getSecureValue, setSecureValue } from "./secureStore";

const STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize";
const STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token";
const STRAVA_REVOKE_URL = "https://www.strava.com/oauth/deauthorize";
const STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities";
const TOKEN_KEY = "spark:strava:token";

export type StravaTokenSet = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // unix seconds
  athleteId?: number;
  scope?: string;
};

export type StravaActivitySummary = {
  id: number;
  sportType: string;
  movingTimeSec: number;
  startDate: string;
  distanceM: number;
};

export type DerivedStravaSignal = {
  hasRecentActivity: boolean;
  activityCount24h: number;
  confidence: number;
  latestSportType?: string;
};

function stravaClientId(): string {
  return process.env.EXPO_PUBLIC_STRAVA_CLIENT_ID ?? "";
}

function stravaClientSecret(): string {
  return process.env.EXPO_PUBLIC_STRAVA_CLIENT_SECRET ?? "";
}

function stravaRedirectUri(): string {
  return process.env.EXPO_PUBLIC_STRAVA_REDIRECT_URI ?? "spark://oauth/strava";
}

export function buildStravaAuthorizeUrl(state: string): string {
  const clientId = stravaClientId();
  if (!clientId) {
    throw new Error("Missing EXPO_PUBLIC_STRAVA_CLIENT_ID.");
  }
  const url = new URL(STRAVA_AUTHORIZE_URL);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", stravaRedirectUri());
  url.searchParams.set("response_type", "code");
  url.searchParams.set("approval_prompt", "auto");
  url.searchParams.set("scope", "read,activity:read_all");
  url.searchParams.set("state", state);
  return url.toString();
}

export async function exchangeCodeForToken(code: string): Promise<StravaTokenSet> {
  const clientId = stravaClientId();
  const clientSecret = stravaClientSecret();
  if (!clientId || !clientSecret) {
    throw new Error(
      "Missing Strava OAuth env vars EXPO_PUBLIC_STRAVA_CLIENT_ID/SECRET.",
    );
  }
  const r = await fetch(STRAVA_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      grant_type: "authorization_code",
    }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`Strava token exchange failed ${r.status}: ${t.slice(0, 300)}`);
  }
  const payload = (await r.json()) as {
    access_token: string;
    refresh_token: string;
    expires_at: number;
    athlete?: { id?: number };
    scope?: string;
  };

  const tokenSet: StravaTokenSet = {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    expiresAt: payload.expires_at,
    athleteId: payload.athlete?.id,
    scope: payload.scope,
  };
  await saveStravaTokenSet(tokenSet);
  return tokenSet;
}

export async function refreshStravaToken(
  currentRefreshToken?: string,
): Promise<StravaTokenSet> {
  const existing = await loadStravaTokenSet();
  const refreshToken = currentRefreshToken ?? existing?.refreshToken;
  if (!refreshToken) {
    throw new Error("No Strava refresh token available.");
  }

  const r = await fetch(STRAVA_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_id: stravaClientId(),
      client_secret: stravaClientSecret(),
      grant_type: "refresh_token",
      refresh_token: refreshToken,
    }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`Strava token refresh failed ${r.status}: ${t.slice(0, 300)}`);
  }
  const payload = (await r.json()) as {
    access_token: string;
    refresh_token: string;
    expires_at: number;
    athlete?: { id?: number };
    scope?: string;
  };
  const tokenSet: StravaTokenSet = {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    expiresAt: payload.expires_at,
    athleteId: payload.athlete?.id,
    scope: payload.scope,
  };
  await saveStravaTokenSet(tokenSet);
  return tokenSet;
}

export async function saveStravaTokenSet(token: StravaTokenSet): Promise<void> {
  await setSecureValue(TOKEN_KEY, JSON.stringify(token));
}

export async function loadStravaTokenSet(): Promise<StravaTokenSet | null> {
  const raw = await getSecureValue(TOKEN_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StravaTokenSet;
  } catch {
    return null;
  }
}

export async function disconnectStrava(): Promise<void> {
  const token = await loadStravaTokenSet();
  if (token?.accessToken) {
    try {
      await fetch(STRAVA_REVOKE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: token.accessToken }),
      });
    } catch {
      // Best effort revoke; local deletion still proceeds.
    }
  }
  await deleteSecureValue(TOKEN_KEY);
}

async function getValidAccessToken(): Promise<string | null> {
  const token = await loadStravaTokenSet();
  if (!token) return null;
  const now = Math.floor(Date.now() / 1000);
  if (token.expiresAt <= now + 60) {
    const refreshed = await refreshStravaToken(token.refreshToken);
    return refreshed.accessToken;
  }
  return token.accessToken;
}

export async function fetchRecentStravaActivities(): Promise<StravaActivitySummary[]> {
  const accessToken = await getValidAccessToken();
  if (!accessToken) return [];
  const after = Math.floor(Date.now() / 1000) - 24 * 60 * 60;
  const url = new URL(STRAVA_ACTIVITIES_URL);
  url.searchParams.set("after", String(after));
  url.searchParams.set("per_page", "25");
  const r = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`Strava activity fetch failed ${r.status}: ${t.slice(0, 300)}`);
  }
  const payload = (await r.json()) as Array<{
    id: number;
    sport_type: string;
    moving_time: number;
    start_date: string;
    distance: number;
  }>;
  return payload.map((item) => ({
    id: item.id,
    sportType: item.sport_type,
    movingTimeSec: item.moving_time,
    startDate: item.start_date,
    distanceM: item.distance,
  }));
}

export function deriveStravaSignal(
  activities: StravaActivitySummary[],
): DerivedStravaSignal {
  if (!activities.length) {
    return { hasRecentActivity: false, activityCount24h: 0, confidence: 0.0 };
  }
  const sorted = [...activities].sort((a, b) =>
    a.startDate < b.startDate ? 1 : -1,
  );
  const latest = sorted[0];
  const totalMovingSec = activities.reduce((acc, item) => acc + item.movingTimeSec, 0);
  const confidence = Math.max(0.55, Math.min(0.95, totalMovingSec / 7200));
  return {
    hasRecentActivity: true,
    activityCount24h: activities.length,
    confidence: Number(confidence.toFixed(2)),
    latestSportType: latest.sportType,
  };
}
