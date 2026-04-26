import { useCallback, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { Button, StyleSheet, Text, View } from "react-native";

import { postComposite } from "./src/api/spark";

const SAMPLE_INTENT = {
  grid_cell: "891f8d7a49bffff",
  movement_mode: "browsing" as const,
  time_bucket: "tuesday_lunch",
  weather_need: "warmth_seeking" as const,
  social_preference: "quiet" as const,
  price_tier: "mid" as const,
  recent_categories: ["cafe"],
  dwell_signal: false,
  battery_low: false,
  session_id: "rn-smoke-session",
};

export default function App() {
  const [status, setStatus] = useState<string>("");

  const ping = useCallback(async () => {
    setStatus("…");
    try {
      const data = await postComposite(SAMPLE_INTENT);
      const m = (data as { merchant?: { id?: string } }).merchant;
      setStatus(`OK composite → merchant ${m?.id ?? "?"}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    }
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Spark mobile</Text>
      <Text style={styles.hint}>Uses EXPO_PUBLIC_SPARK_API_BASE → /api/context/composite</Text>
      <Button title="Ping backend" onPress={ping} />
      {status ? <Text style={styles.status}>{status}</Text> : null}
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
  status: { fontSize: 12, color: "#111", textAlign: "center" },
});
