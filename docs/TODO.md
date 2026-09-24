# SecAI — TODO / Roadmap

Legend: `[ ]` todo · `[x]` done · **(MVP)** = required for private beta

## Phase 0 — Foundation
- [ ] **(MVP)** Monorepo scaffold: `apps/web` (Next.js), `apps/api` (FastAPI), `workers/`, `scanners/`, `packages/schema`
- [ ] **(MVP)** Docker Compose dev env: Postgres, Redis, API, worker, web
- [ ] **(MVP)** GitHub Actions CI: lint (ruff, eslint), typecheck (mypy/pyright, tsc), tests, image builds
- [ ] **(MVP)** Auth (sign up / login, GitHub OAuth) and org/workspace model
- [ ] **(MVP)** DB schema + migrations: `users, orgs, targets, target_verifications, scans, scan_steps, findings, finding_groups, ai_enrichments, subscriptions, usage`
- [ ] **(MVP)** Unified `Finding` schema (Pydantic, exported as JSON Schema → TS types)
- [ ] Settings: env config, secrets management, Sentry

## Phase 1 — Website pentest (DAST) MVP
- [ ] **(MVP)** Add target (URL) + normalize/validate
- [ ] **(MVP)** Domain ownership verification: DNS TXT / well-known file / meta tag + periodic re-check
- [ ] **(MVP)** SSRF guard: block private/reserved IPs, re-resolve per request, isolated scanner network
- [ ] **(MVP)** Scan orchestrator: create scan → steps → run containers → collect output → timeouts/retries/cancel
- [ ] **(MVP)** Scanner: security headers / cookies / CORS / HTTPS redirect (custom Python)
- [ ] **(MVP)** Scanner: TLS config (sslyze or testssl.sh)
- [ ] **(MVP)** Scanner: httpx tech fingerprint
- [ ] **(MVP)** Scanner: Nuclei (curated safe template set, rate limited)
- [ ] **(MVP)** Scanner: OWASP ZAP baseline (passive), then active scan for paid plans
- [ ] Scanner: exposed files / dirs (ffuf + curated list: `.git`, `.env`, backups)
- [ ] Scanner: top-ports check (naabu)
- [ ] **(MVP)** Parsers → normalized findings; dedup by fingerprint
- [ ] **(MVP)** Scan progress via SSE; scan list + scan detail UI
- [ ] Safety: per-target rate limits, global kill switch, domain blocklist, published scanner IPs, abuse email

## Phase 2 — AI analysis & reports
- [ ] **(MVP)** Claude API client with retries, cost tracking, per-plan budget
- [ ] **(MVP)** Secret/PII redaction before LLM calls
- [ ] **(MVP)** Per-finding enrichment (structured JSON): verdict, confidence, adjusted severity, explanation, impact, fix steps, code/config snippet for the detected stack, references (CWE/OWASP)
- [ ] **(MVP)** Scan executive summary + security score/grade
- [ ] Enrichment cache keyed by fingerprint; prompt caching for the system prompt
- [ ] Model routing (cheap model for bulk, strong model for critical / FP adjudication)
- [ ] **(MVP)** Report UI: severity filters, grouped findings, "how to fix" tabs
- [ ] PDF / Markdown export
- [ ] "Mark false positive / accepted risk" and feed it back into future scans
- [ ] Eval set: sample findings with expected verdicts to regression-test prompts

## Phase 3 — Trial & subscriptions
- [ ] **(MVP)** Stripe products/prices, Checkout, Customer Portal, webhooks
- [ ] **(MVP)** 14-day trial logic + plan entitlements + quota enforcement in API
- [ ] **(MVP)** Usage metering (scans, targets, AI tokens)
- [ ] **(MVP)** Transactional emails (verify email, scan finished, trial ending)
- [ ] **(MVP)** Landing page, pricing page, ToS, Privacy Policy, Acceptable Use / authorization attestation
- [ ] **🚀 Private beta launch**

## Phase 4 — GitHub code scanning
- [ ] Register GitHub App (read-only Contents + Metadata; later Checks / PRs write)
- [ ] Install flow → list/select repos → store installation id
- [ ] Ephemeral shallow clone in worker using installation token; delete after scan
- [ ] Scanner: Opengrep/Semgrep engine with a license-compatible ruleset (SARIF)
- [ ] Scanner: OSV-Scanner / Trivy fs (dependencies)
- [ ] Scanner: Gitleaks (tree + history)
- [ ] Scanner: Trivy config / Checkov (IaC, Dockerfile)
- [ ] SARIF parser → unified findings with file/line + code snippet
- [ ] AI enrichment for code: explain the vulnerable flow, propose a patch (diff)
- [ ] Webhooks: scan on push to default branch / on PR
- [ ] Post results as a GitHub Check run + PR review comments
- [ ] Optional: upload SARIF to GitHub Code Scanning

## Phase 5 — Depth & retention
- [ ] Scheduled scans (weekly/daily) + "new / fixed / still open" diff
- [ ] Authenticated DAST (login recorder / session cookie / header auth via ZAP contexts)
- [ ] API scanning from OpenAPI/Swagger spec
- [ ] AI "chat with your report"
- [ ] AI auto-fix PRs on GitHub
- [ ] Slack / Discord / email alerts
- [ ] Team seats, roles, audit log, SSO (Team plan)
- [ ] Public status badge / trust page for customers
- [ ] SOC 2-lite hygiene: backups, access reviews, incident runbook

## Open decisions (need your input)
- [ ] Hosting budget & region (EU vs US data residency?)
- [ ] Auth provider: Clerk (fast) vs self-hosted Auth.js
- [ ] Queue: start with ARQ or go straight to Temporal
- [ ] Final pricing numbers
- [ ] Product name / domain
