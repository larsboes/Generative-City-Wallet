import { useCallback, useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { Button, Linking, StyleSheet, Text, TextInput, View } from "react-native";
import type { IntentVector } from "@spark/shared";

import { postComposite } from "./src/api/spark";
import { runIntentInference, mapToolArgsToIntent, DEFAULT_INTENT_VECTOR } from "./src/local-llm";
import { applyStravaSignalToIntent } from "./src/local-llm/sourceSignals";
import { useStravaIntegration } from "./src/api/useStravaIntegration";

const SAMPLE_INTENT: IntentVector = {
  grid_cell: "891f8d7a49bffff",
  movement_mode: "browsing",
  time_bucket: "tuesday_lunch",
  weather_need: "warmth_seeking",
  social_preference: "quiet",
  price_tier: "mid",
  recent_categories: ["cafe"],
  dwell_signal: false,
  battery_low: false,
  session_id: "rn-smoke-session",
};

export default function App() {
  const [status, setStatus] = useState<string>("");
  const [userText, setUserText] = useState<string>("I'm walking downtown feeling sluggish and need a quick pick-me-up.");
  const [activeIntent, setActiveIntent] = useState<IntentVector>(DEFAULT_INTENT_VECTOR);
  const {
    status: stravaStatus,
    connection,
    signal,
    canUseStrava,
    connect,
    disconnect,
    refreshConnection,
    handleCallbackUrl,
    refreshSignal,
  } = useStravaIntegration();

  useEffect(() => {
    refreshConnection().catch((e) =>
      setStatus(e instanceof Error ? e.message : String(e)),
    );
  }, [refreshConnection]);

  useEffect(() => {
    const sub = Linking.addEventListener("url", ({ url }) => {
      handleCallbackUrl(url).catch((e) =>
        setStatus(e instanceof Error ? e.message : String(e)),
      );
    });
    Linking.getInitialURL().then((url) => {
      if (url && url.includes("oauth/strava")) {
        handleCallbackUrl(url).catch((e) =>
          setStatus(e instanceof Error ? e.message : String(e)),
        );
      }
    });
    return () => sub.remove();
  }, [handleCallbackUrl]);

  const extractContext = useCallback(async () => {
    setStatus("Initializing WebGPU... (This may take a minute if downloading Gemma 4 Nano for the first time)");
    try {
      const res = await runIntentInference(userText);
      const mapped = mapToolArgsToIntent(res.arguments, activeIntent);
      setActiveIntent(mapped);
      setStatus(`Local intent derived: ${res.arguments.movement_mode} / ${res.arguments.weather_need}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    }
  }, [userText, activeIntent]);

  const ping = useCallback(async () => {
    setStatus("Pinging cloud...");
    try {
      let intent = activeIntent;
      if (canUseStrava) {
        const refreshed = await refreshSignal();
        intent = applyStravaSignalToIntent(activeIntent, activeIntent.movement_mode, refreshed);
      }
      const data = await postComposite(intent);
      const m = (data as { merchant?: { id?: string } }).merchant;
      setStatus(`OK composite → merchant ${m?.id ?? "?"}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    }
  }, [activeIntent, canUseStrava, refreshSignal]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Spark mobile</Text>
      <Text style={styles.hint}>Uses EXPO_PUBLIC_SPARK_API_BASE → /api/context/composite</Text>
      <Text style={styles.hint}>
        Strava: {connection.connected ? "connected" : "not connected"} | recent activity:{" "}
        {signal.hasRecentActivity ? "yes" : "no"}
      </Text>
      <View style={styles.row}>
        <Button title="Connect Strava" onPress={() => connect().catch((e) => setStatus(String(e)))} />
        <Button
          title="Disconnect Strava"
          onPress={() => disconnect().catch((e) => setStatus(String(e)))}
        />
      </View>

      <TextInput
        style={styles.input}
        value={userText}
        onChangeText={setUserText}
        placeholder="How are you feeling right now?"
      />
      <View style={styles.row}>
        <Button title="1. Extract Intent (Local LLM)" onPress={extractContext} />
        <Button title="2. Ping Backend (Cloud)" onPress={ping} />
      </View>

      {status ? <Text style={styles.status}>{status}</Text> : null}
      {stravaStatus ? <Text style={styles.status}>{stravaStatus}</Text> : null}
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    gap: 12,
  },
  title: { fontSize: 20, fontWeight: "600" },
  hint: { fontSize: 12, color: "#666", textAlign: "center" },
  status: { fontSize: 12, color: "#111", textAlign: "center", marginTop: 16 },
  row: { flexDirection: "row", gap: 8 },
  input: { borderWidth: 1, borderColor: "#ccc", width: "100%", padding: 12, borderRadius: 8, marginTop: 12 },
});
