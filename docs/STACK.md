# SecAI — Recommended Stack

Guiding principle: **Python on the backend**, because most security tooling and parsers live there. **TypeScript on the frontend.** Every scanner is a Docker image, so no tool gets installed on the API host.

## Recommended (default choice)

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui** | Fast to build a polished dashboard and marketing site in one app. |
| Charts / tables | TanStack Table, Recharts | Findings tables and trend charts. |
| API | **FastAPI (Python 3.12+) + Pydantic v2 + SQLAlchemy 2 + Alembic** | Async, typed, auto OpenAPI docs → typed TS client generated for the frontend. |
| Auth | **Built into the FastAPI backend (self-hosted, no third-party service):** argon2id password hashing, server-side sessions (hashed tokens in Postgres, HttpOnly/Secure/SameSite cookies, idle + absolute expiry), Origin-checked CSRF protection, login rate limiting, TOTP two-factor auth with secrets encrypted at rest. Later: recovery codes, passkeys (WebAuthn), GitHub login, and generic OIDC so admins can plug in Keycloak/Authentik. | Nothing leaves the instance; uses audited libraries (argon2-cffi, cryptography, pyotp) instead of custom crypto. |
| Database | **PostgreSQL** (Neon / Supabase / RDS) | Relational data plus JSONB for raw tool output. |
| Queue / workers | **Redis + ARQ** (chosen); revisit Temporal only if workflows outgrow it | Scans are long multi-step jobs that need retries and timeouts. |
| Scanner execution | **Docker containers per tool**, run as rootless, ephemeral jobs; later **Kubernetes Jobs** or **AWS ECS Fargate** tasks | Isolation, per-scan resource limits, horizontal scale. |
| Object storage | **S3 / Cloudflare R2** | Raw outputs, SARIF files, PDF reports. |
| AI | **Claude API** (Anthropic SDK for Python) with tool use / structured JSON output | Triage, dedup, fix guidance, summaries. |
| Real-time progress | Server-Sent Events from FastAPI | Live "scan is 60% done" UI. |
| Payments (optional module) | **Stripe**, disabled by default | Only for admins who run a paid hosted instance. |
| Email | Resend or Postmark | Scan finished, weekly digest. |
| PDF reports | WeasyPrint (HTML → PDF) or Playwright print | Reuse the web report templates. |
| GitHub | **GitHub App** (not a plain OAuth app) | Fine-grained, per-repo, read-only permissions; webhooks for push/PR scans; can post Checks and PR comments later. |
| Observability | Sentry + OpenTelemetry + Grafana/Prometheus (or Better Stack) | Scans fail in creative ways, so you need to see why. |
| Deploy | **Docker Compose** (one command on any VPS) is the primary install; Helm chart later for Kubernetes | Self-hosters need a simple install. Scanners need an egress IP you control, so don't run them on shared serverless. |
| CI/CD | GitHub Actions | Lint, test, build images; dogfood SecAI's own code scan. |
| Monorepo | `apps/web`, `apps/api`, `workers/`, `scanners/<tool>/Dockerfile`, `packages/schema` | One place for the shared Finding schema. |

## Alternatives

- **All-TypeScript:** NestJS/Hono API + BullMQ. Works, but most scanner parsing and security libraries are Python-first.
- **Go backend:** great for the orchestrator (ProjectDiscovery tools are Go), but slower to iterate on at MVP stage.

## SecAI's own license

**AGPL-3.0-only** with an additional attribution term (AGPL §7(b)): anyone may use, modify and host SecAI, but must keep the visible "Powered by SecAI by hdbrzgr" credit in the UI, and must publish their changes if they host a modified version. See [LICENSE](../LICENSE) and [NOTICE](../NOTICE).

## Licensing notes for bundled scanners (verify before release)

| Tool | License | Note |
|---|---|---|
| OWASP ZAP | Apache-2.0 | ✅ |
| Nuclei, httpx, subfinder, naabu | MIT | ✅ Check the nuclei-templates repo license too (MIT). |
| sslyze | AGPL-3.0 | ⚠️ Fine to run as a separate process. Get legal advice if you modify it. |
| testssl.sh | GPL-2.0 | ✅ Run as a separate process. |
| Nmap | NPSL (custom) | ⚠️ Restrictive for commercial products. Prefer naabu, or buy an OEM license. |
| Semgrep CE engine | LGPL-2.1 | ✅ Engine. ⚠️ **Semgrep Registry rules restrict use in competing SaaS.** Use **Opengrep** with rules whose license allows it, or write your own. |
| Gitleaks | MIT | ✅ |
| TruffleHog | AGPL-3.0 | ⚠️ Same caveat as sslyze. |
| Trivy, OSV-Scanner | Apache-2.0 | ✅ |
| Checkov | Apache-2.0 | ✅ |

> This table is a starting point, not legal advice. Confirm the licenses when you pin versions.
