import * as SecureStore from "expo-secure-store";

const MEM: Record<string, string> = {};

/**
 * Best-effort secure storage wrapper.
 * Falls back to in-memory storage in unsupported runtimes (e.g. some web/dev paths).
 */
export async function getSecureValue(key: string): Promise<string | null> {
  try {
    if (!SecureStore.isAvailableAsync) {
      return MEM[key] ?? null;
    }
    const available = await SecureStore.isAvailableAsync();
    if (!available) {
      return MEM[key] ?? null;
    }
    return await SecureStore.getItemAsync(key);
  } catch {
    return MEM[key] ?? null;
  }
}

export async function setSecureValue(key: string, value: string): Promise<void> {
  try {
    const available = await SecureStore.isAvailableAsync();
    if (!available) {
      MEM[key] = value;
      return;
    }
    await SecureStore.setItemAsync(key, value);
  } catch {
    MEM[key] = value;
  }
}

export async function deleteSecureValue(key: string): Promise<void> {
  try {
    const available = await SecureStore.isAvailableAsync();
    if (!available) {
      delete MEM[key];
      return;
    }
    await SecureStore.deleteItemAsync(key);
  } catch {
    delete MEM[key];
  }
}
