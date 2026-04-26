import { NativeModules, Platform } from "react-native";
import { CreateMLCEngine, MLCEngine } from "@mlc-ai/web-llm";

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

// Global engine instance for the web path
let webEngineInstance: MLCEngine | null = null;
const SELECTED_MODEL = "gemma-4-nano-it-q4f16_1-MLC";

async function runWebGPUInference(userText: string): Promise<NativeInferenceResult> {
    if (!webEngineInstance) {
        console.log(`[Spark WebLLM] Initializing WebGPU engine with ${SELECTED_MODEL}...`);
        webEngineInstance = await CreateMLCEngine(SELECTED_MODEL, {
            initProgressCallback: (progress) => {
                console.log(`[Spark WebLLM] Loading: ${progress.text}`);
            },
        });
    }

    const engine = webEngineInstance;
    const tools = [
        {
            type: "function",
            function: {
                name: INTENT_TOOL_SCHEMA.name,
                description: INTENT_TOOL_SCHEMA.description,
                parameters: INTENT_TOOL_SCHEMA.parameters,
            },
        },
        ...OPTIONAL_KG_TOOLS.map((t) => ({
            type: "function",
            function: { name: t.name, description: t.description, parameters: t.parameters },
        })),
    ];

    console.log(`[Spark WebLLM] Instructing model with explicit tool call constraint...`);

    const reply = await engine.chat.completions.create({
        messages: [
            {
                role: "system",
                content:
                    "You are a local context intent extractor. You MUST call the `set_intent_vector_fields` function. Do not write normal text. Only call the tool. Do not hallucinate.",
            },
            { role: "user", content: userText },
        ],
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        tools: tools as any,
        tool_choice: { type: "function", function: { name: INTENT_TOOL_SCHEMA.name } },
    });

    const message = reply.choices[0].message;

    if (message.tool_calls && message.tool_calls.length > 0) {
        const call = message.tool_calls[0];
        return {
            tool_name: call.function.name,
            arguments: JSON.parse(call.function.arguments) as IntentToolArgs,
            raw_text: message.content || undefined,
        };
    }

    throw new Error("Local WebLLM did not return a structured tool call.");
}

/**
 * JS entrypoint for on-device local-LLM inference.
 * - Web (PWA): Uses WebGPU via @mlc-ai/web-llm
 * - iOS/Android: Uses native modules from `expo prebuild`
 */
export async function runIntentInference(userText: string): Promise<NativeInferenceResult> {
    if (Platform.OS === "web") {
        return runWebGPUInference(userText);
    }

    const mod = getNativeModule();
    if (!mod) {
        throw new Error(
            `SparkLocalLLM native module missing on ${Platform.OS}. Run expo prebuild and wire native implementation.`
        );
    }

    return mod.runIntentInference({
        user_text: userText,
        tool_schema: INTENT_TOOL_SCHEMA.parameters,
        optional_tools: OPTIONAL_KG_TOOLS.map((tool) => tool.parameters),
    });
}
