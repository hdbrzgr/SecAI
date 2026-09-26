# SecAI web

Next.js front end. It talks to the API only through `/api/*`, which Next.js proxies to
`API_INTERNAL_URL` (default `http://localhost:8000`), so the session cookie stays first-party.

UI comes from the `@secai/ui` workspace (`packages/ui`): components, tokens and fonts. Tailwind is
used for page layout only. From the repository root:

```bash
npm install
npm run dev -w secai-web      # http://localhost:3000 (API must be running on :8000)
npm run lint -w secai-web && npm run typecheck -w secai-web && npm run build -w secai-web
```

Keep the `Attribution` footer visible; it is required by the license (see `/NOTICE`).
