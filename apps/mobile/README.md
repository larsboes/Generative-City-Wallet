# Spark — React PWA Frontend

On-device **Gemma 4 / Google AI Edge** operates within the browser context (e.g., via WebAssembly/Transformers.js). This folder holds **UI + networking** in TypeScript.

---

## Environment setup

Create `.env` mirroring `.env.example`:

- `EXPO_PUBLIC_SPARK_API_BASE` — FastAPI origin (default `http://127.0.0.1:8000`).

---

## Running locally

```bash
npm install
npm run start
```

## Local LLM spike scaffolding

- TS bridge + tool schema: `src/local-llm/`
- Native implementation runbook: `LOCAL_LLM_SPIKE.md`
