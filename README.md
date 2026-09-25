# SecAI

Open-source, self-hostable, AI-powered security scanning. Users verify they own a website (and later connect GitHub repos), SecAI runs proven open-source security tools against it, and an AI layer turns the raw output into a prioritized list of vulnerabilities with clear, stack-specific fix guidance.

- **Plan & architecture:** [docs/PLAN.md](docs/PLAN.md)
- **Roadmap / TODO:** [docs/TODO.md](docs/TODO.md)
- **Design system:** [packages/ui](packages/ui) · [in Claude Design](https://claude.ai/artifact/Eu7M6wukvHRi69oLHyuLSE)
- **Stack decisions:** [docs/STACK.md](docs/STACK.md)

## Quick start (self-hosted)

Requirements: Docker with Compose.

```bash
git clone https://github.com/hdbrzgr/SecAI.git && cd SecAI
cp .env.example .env
# Set SECAI_SECRET_KEY and POSTGRES_PASSWORD in .env
# (python3 -c "import secrets; print(secrets.token_urlsafe(48))")
docker compose up -d --build
```

Open http://localhost:3000 and create an account. **The first account becomes the instance admin.** Then set `SECAI_ALLOW_REGISTRATION=false` if you don't want public sign-ups.

For a real deployment, put a TLS reverse proxy (Caddy, Traefik, nginx) in front of port 3000, set `SECAI_WEB_ORIGIN=https://your-domain` and `SECAI_ENV=production`.

## Development

| Part | Location | Commands |
|---|---|---|
| API (FastAPI) | `apps/api` | `uv sync` · `uv run uvicorn app.main:app --reload` · `uv run pytest` · `uv run ruff check .` · `uv run alembic upgrade head` |
| Worker (ARQ) | `apps/api/app/worker.py` | `uv run arq app.worker.WorkerSettings` |
| Web (Next.js) | `apps/web` | from the repo root: `npm install` · `npm run dev -w secai-web` · `npm run lint -w secai-web` |
| Design system | `packages/ui` | `npm run build -w @secai/ui` (regenerates `src/tokens.css`, fonts, the Claude Design files) · `npm run check -w @secai/ui` |

The API needs Postgres and Redis. The simplest way to get them locally is `docker compose up -d postgres redis`, then publish their ports or use local installs. See `apps/api/app/core/config.py` for every `SECAI_*` setting.

## What a website scan checks

Add a website, prove you own it (DNS TXT record, a file at `/.well-known/secai-verify.txt`, or a `<meta name="secai-verify">` tag), confirm you're authorized, then run a scan. The worker runs:

| Scanner | Checks |
|---|---|
| Headers | HTTPS and HTTP→HTTPS redirect, HSTS, CSP, clickjacking protection, nosniff, Referrer-Policy, version disclosure, CORS, cookie flags |
| TLS | Certificate trust and hostname, expiry, TLS 1.0/1.1 support |
| Exposed files | `.git`, `.env`, `.svn`, `.DS_Store`, phpinfo, server-status, config backups, AWS credentials (confirmed by content, contents of secrets never stored) |
| Nuclei | ProjectDiscovery's HTTP templates; `dos`, `fuzz`, `bruteforce` and `intrusive` templates are excluded; rate limited |
| OWASP ZAP | Spiders the site (5 minutes max) and runs ZAP's passive rules: CSRF tokens, SRI, mixed content, cross-domain scripts, information leaks and more. Baseline only: no attack payloads |

Findings are normalized, deduplicated and graded A–F. ZAP runs on its own Docker network with the worker, so it can't reach the database or Redis. AI-written explanations are next on the roadmap.

**Scanner safety.** Every connection to a user's site goes through a guard that resolves the hostname, refuses private, loopback, link-local and cloud-metadata addresses, pins the connection to the checked address and re-checks every redirect. `SECAI_SCAN_ALLOW_PRIVATE=true` lifts this for local development only; the API refuses to start with it in production.

## Security design (so far)

- Passwords hashed with **argon2id**. Login timing is the same whether or not the account exists.
- **Server-side sessions:** random tokens stored only as SHA-256 hashes. Cookies are HttpOnly, SameSite=Lax, and Secure + `__Host-` prefixed on HTTPS. Sessions have idle and absolute expiry.
- **CSRF protection:** every state-changing request must come from the web app's origin.
- **Rate limiting** on login (per IP and per email), registration and 2FA attempts.
- **TOTP two-factor auth:** secrets are encrypted at rest, codes can't be replayed, and the session token is rotated after the second factor.
- Security headers on the API and web app (CSP, frame blocking, nosniff, HSTS on HTTPS). Containers run as non-root, and the API isn't exposed outside the Docker network.

## License

SecAI is free software under the **GNU AGPL-3.0** with one extra term (AGPL §7(b)): anyone running, hosting or distributing SecAI must keep the visible **"Powered by SecAI by hdbrzgr"** credit in the UI. If you host a modified version, you must publish your changes. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Only scan systems you own or have written permission to test.
