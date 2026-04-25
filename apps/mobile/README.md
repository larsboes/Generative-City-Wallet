# Spark — React Native (Expo)

On-device **Gemma 4 / Google AI Edge / LiteRT** belongs in **native Swift & Kotlin** (Expo prebuild + native module). This folder holds **UI + networking** in TypeScript; wire inference there later per `../.cursor/plans/local_llm_preparation_*.plan.md` (or repo planning docs).

## Backend boundary

- Shared wire types: [`../packages/shared/src/contracts.ts`](../packages/shared/src/contracts.ts) (`IntentVector`, etc.).
- `src/api/spark.ts` — `POST /api/context/composite` with an `IntentVector` body.

## Env

Copy `.env.example` to `.env` and set:

- `EXPO_PUBLIC_SPARK_API_BASE` — FastAPI origin (default `http://127.0.0.1:8000`).

## Commands

```bash
cd mobile
npm install
npx expo start
```

Use **EAS / `expo prebuild`** before adding the LiteRT native module; managed workflow alone cannot load Gemma weights.
