import { useCallback, useMemo, useState } from "react";
import { Linking } from "react-native";

import {
  buildStravaAuthorizeUrl,
  deriveStravaSignal,
  disconnectStrava,
  exchangeCodeForToken,
  fetchRecentStravaActivities,
  loadStravaTokenSet,
  parseStravaCallbackUrl,
  type DerivedStravaSignal,
} from "./strava";

type StravaConnectionState = {
  connected: boolean;
  athleteId?: number;
  hasToken: boolean;
};

export function useStravaIntegration() {
  const [status, setStatus] = useState<string>("");
  const [connection, setConnection] = useState<StravaConnectionState>({
    connected: false,
    hasToken: false,
  });
  const [signal, setSignal] = useState<DerivedStravaSignal>({
    hasRecentActivity: false,
    activityCount24h: 0,
    confidence: 0.0,
  });

  const refreshConnection = useCallback(async () => {
    const token = await loadStravaTokenSet();
    const connected = Boolean(token?.accessToken);
    setConnection({
      connected,
      hasToken: connected,
      athleteId: token?.athleteId,
    });
    return connected;
  }, []);

  const connect = useCallback(async () => {
    const state = `spark-${Date.now()}`;
    const url = buildStravaAuthorizeUrl(state);
    setStatus("Opening Strava consent screen…");
    const canOpen = await Linking.canOpenURL(url);
    if (!canOpen) {
      throw new Error("Cannot open Strava OAuth URL on this device.");
    }
    await Linking.openURL(url);
  }, []);

  const handleCallbackUrl = useCallback(
    async (url: string) => {
      const parsed = parseStravaCallbackUrl(url);
      if (!parsed.ok) {
        const msg = `Strava callback error: ${parsed.error}`;
        setStatus(msg);
        throw new Error(msg);
      }
      setStatus("Exchanging Strava authorization code…");
      const tokenSet = await exchangeCodeForToken(parsed.code);
      setConnection({
        connected: true,
        hasToken: true,
        athleteId: tokenSet.athleteId,
      });
      setStatus("Strava connected.");
      return tokenSet;
    },
    [],
  );

  const refreshSignal = useCallback(async () => {
    setStatus("Refreshing Strava activity signal…");
    const activities = await fetchRecentStravaActivities();
    const s = deriveStravaSignal(activities);
    setSignal(s);
    setStatus(
      s.hasRecentActivity
        ? `Strava active (${s.activityCount24h} activities / 24h)`
        : "No recent Strava activity detected.",
    );
    return s;
  }, []);

  const disconnect = useCallback(async () => {
    setStatus("Disconnecting Strava…");
    await disconnectStrava();
    setConnection({ connected: false, hasToken: false });
    setSignal({
      hasRecentActivity: false,
      activityCount24h: 0,
      confidence: 0.0,
    });
    setStatus("Strava disconnected.");
  }, []);

  const canUseStrava = useMemo(
    () => connection.connected && connection.hasToken,
    [connection],
  );

  return {
    status,
    connection,
    signal,
    canUseStrava,
    connect,
    disconnect,
    refreshConnection,
    handleCallbackUrl,
    refreshSignal,
  };
}
