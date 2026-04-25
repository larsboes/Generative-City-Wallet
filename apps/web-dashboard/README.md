# @spark/web-dashboard

Merchant UI scaffold (**Vite + React**). Next.js was deferred for this workspace because npm hoisting produced duplicate React copies during `next build` (styled-jsx / prerender). We can revisit Next when the monorepo install story is stable.

From **repository root**:

```bash
npm install
npm run dev:dashboard
```

Uses `@spark/shared` for API contracts (see `src/App.tsx`). FastAPI base URL: add `VITE_SPARK_API_BASE` (or similar) when wiring fetch.
