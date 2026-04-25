import { NativeModules, Platform } from "react-native";

import type { IntentToolArgs } from "./toolSchema";
import { INTENT_TOOL_SCHEMA, OPTIONAL_KG_TOOLS } from "./toolSchema";

type NativeInferenceResult = {
  tool_name: string;
  arguments: IntentToolArgs;
  raw_text?: string;
};

type SparkLocalLLMModule = {
  runIntentInference(payload: {
    user_text: string;
    tool_schema: Record<string, unknown>;
    optional_tools: Record<string, unknown>[];
  }): Promise<NativeInferenceResult>;
};

function getNativeModule(): SparkLocalLLMModule | null {
  const module = NativeModules.SparkLocalLLM as SparkLocalLLMModule | undefined;
  return module ?? null;
}

/**
 * JS entrypoint for native local-LLM inference.
 * Native implementation is added after `expo prebuild`:
 * - iOS: Swift module
 * - Android: Kotlin module
 */
export async function runIntentInference(
  userText: string,
): Promise<NativeInferenceResult> {
  const mod = getNativeModule();
  if (!mod) {
    throw new Error(
      `SparkLocalLLM native module missing on ${Platform.OS}. Run expo prebuild and wire native implementation.`,
    );
  }
  return mod.runIntentInference({
    user_text: userText,
    tool_schema: INTENT_TOOL_SCHEMA.parameters,
    optional_tools: OPTIONAL_KG_TOOLS.map((tool) => tool.parameters),
  });
}

