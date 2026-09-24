# SecAI — Recommended Stack

Guiding principle: **Python on the backend**, because most security tooling and parsers live there. **TypeScript on the frontend.** Every scanner is a Docker image, so no tool gets installed on the API host.

## Recommended (default choice)

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui** | Fast to build a polished dashboard and marketing site in one app. |
| Charts / tables | TanStack Table, Recharts | Findings tables and trend charts. |
| API | **FastAPI (Python 3.12+) + Pydantic v2 + SQLAlchemy 2 + Alembic** | Async, typed, auto OpenAPI docs → typed TS client generated for the frontend. |
| Auth | **Clerk** (fastest) or **Auth.js** (self-hosted); GitHub OAuth login | GitHub login fits the audience and the later GitHub feature. |
| Database | **PostgreSQL** (Neon / Supabase / RDS) | Relational data plus JSONB for raw tool output. |
| Queue / workers | **Redis + ARQ** (simple) → **Temporal** when workflows get complex | Scans are long multi-step jobs that need retries and timeouts. |
| Scanner execution | **Docker containers per tool**, run as rootless, ephemeral jobs; later **Kubernetes Jobs** or **AWS ECS Fargate** tasks | Isolation, per-scan resource limits, horizontal scale. |
| Object storage | **S3 / Cloudflare R2** | Raw outputs, SARIF files, PDF reports. |
| AI | **Claude API** (Anthropic SDK for Python) with tool use / structured JSON output | Triage, dedup, fix guidance, summaries. |
| Real-time progress | Server-Sent Events from FastAPI | Live "scan is 60% done" UI. |
| Payments | **Stripe** (Checkout, Billing, Customer Portal, trials) | Trials and subscriptions work out of the box. |
| Email | Resend or Postmark | Scan finished, weekly digest. |
| PDF reports | WeasyPrint (HTML → PDF) or Playwright print | Reuse the web report templates. |
| GitHub | **GitHub App** (not a plain OAuth app) | Fine-grained, per-repo, read-only permissions; webhooks for push/PR scans; can post Checks and PR comments later. |
| Observability | Sentry + OpenTelemetry + Grafana/Prometheus (or Better Stack) | Scans fail in creative ways, so you need to see why. |
| Infra / deploy | Start: Frontend on **Vercel**, API + workers on **Fly.io / Railway / a Hetzner VM with Docker Compose**. Scale: **AWS (ECS/EKS) + Terraform** | Cheap to start. Scanners need a dedicated egress IP range you control, so don't run them on shared serverless. |
| CI/CD | GitHub Actions | Lint, test, build images; dogfood SecAI's own code scan. |
| Monorepo | `apps/web`, `apps/api`, `workers/`, `scanners/<tool>/Dockerfile`, `packages/schema` | One place for the shared Finding schema. |

## Alternatives

- **All-TypeScript:** NestJS/Hono API + BullMQ. Works, but most scanner parsing and security libraries are Python-first.
- **Go backend:** great for the orchestrator (ProjectDiscovery tools are Go), but slower to iterate on at MVP stage.
- **Supabase** as an all-in-one (Postgres + Auth + Storage): a good speed shortcut if you want less infra.

## Licensing notes for a commercial SaaS (verify before launch)

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
