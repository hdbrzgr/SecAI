# SecAI — TODO / Roadmap

Legend: `[ ]` todo · `[x]` done · **(MVP)** = required for private beta

## Phase 0 — Foundation
- [x] **(MVP)** Monorepo scaffold: `apps/web` (Next.js), `apps/api` (FastAPI + ARQ worker); `scanners/` added in Phase 1
- [x] **(MVP)** Docker Compose dev env: Postgres, Redis, API, worker, web
- [x] **(MVP)** GitHub Actions CI: lint (ruff, eslint), typecheck (tsc), tests on Postgres, migration check, image builds
- [ ] Python type checking (mypy or pyright) in CI
- [x] **(MVP)** LICENSE (AGPL-3.0) + NOTICE attribution term + UI footer credit
- [x] **(MVP)** Self-hosted auth: register/login/logout, argon2id, server-side sessions, CSRF/Origin check, login rate limit
- [x] **(MVP)** TOTP two-factor auth (secrets encrypted at rest)
- [x] **(MVP)** Workspace (org) model created on sign-up
- [ ] Email verification + password reset (needs SMTP)
- [ ] MFA recovery codes, passkeys (WebAuthn), GitHub login, generic OIDC
- [ ] Worker cron job that deletes expired sessions
- [x] **(MVP)** DB schema + migrations (Alembic): users, sessions, organizations, memberships, targets, scans, findings
- [ ] Remaining tables as their phases need them: scan_steps, finding_groups, ai_enrichments, usage/quotas
- [ ] **(MVP)** Unified `Finding` schema (Pydantic, exported as JSON Schema → TS types)
- [x] Settings: env config (`SECAI_*`), refuses to start in production with a weak secret or plain-http origin
- [ ] Optional Sentry / OpenTelemetry
- [ ] Trusted-proxy config so per-IP rate limits can't be bypassed with a spoofed `X-Forwarded-For` when the API sits behind extra proxies

## Phase 1 — Website pentest (DAST) MVP
- [x] **(MVP)** Add target (URL) + normalize/validate (domains only; IDN support; one per workspace)
- [x] **(MVP)** Domain ownership verification: DNS TXT / well-known file / meta tag; proof expires after 90 days
- [ ] Background re-check of ownership proofs (currently checked at scan time only by age)
- [x] **(MVP)** SSRF guard: block private/reserved IPs, pin connections to the validated IP, re-check every redirect
- [ ] Egress firewall for the worker container (defense in depth against DNS rebinding inside external tools)
- [x] **(MVP)** Scan orchestrator: ARQ job, per-tool status, progress, one active scan per website, daily limit, attestation per scan
- [ ] Cancel a running scan; per-tool timeouts surfaced in the UI
- [x] **(MVP)** Scanner: security headers / cookies / CORS / HTTPS redirect / version disclosure (custom Python)
- [x] **(MVP)** Scanner: TLS certificate trust, expiry, legacy TLS 1.0/1.1 (Python ssl)
- [ ] **(MVP)** Scanner: httpx tech fingerprint
- [x] **(MVP)** Scanner: Nuclei in the worker image (http templates; dos, fuzz, brute-force and intrusive tags excluded; rate limited)
- [ ] **(MVP)** Scanner: OWASP ZAP baseline (passive), then active scan for paid plans
- [x] Scanner: exposed files (`.git`, `.env`, `.svn`, backups, phpinfo, server-status, AWS credentials) with content checks; secrets never stored
- [ ] Scanner: top-ports check (naabu)
- [x] **(MVP)** Parsers → normalized findings; dedup by fingerprint; score and A–F grade
- [x] **(MVP)** Websites list, verification page, scan history, live progress (polling) and scan report UI
- [ ] Replace polling with Server-Sent Events
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

## Phase 3 — Self-host release
- [ ] **(MVP)** Admin-configurable quotas + enforcement in API
- [ ] **(MVP)** Usage metering (scans, targets, AI tokens)
- [ ] **(MVP)** Admin panel: users, workspaces, domain blocklist, kill switch
- [ ] **(MVP)** Transactional emails via SMTP (verify email, scan finished)
- [ ] **(MVP)** Install guide, upgrade guide, backup guide, hardening checklist
- [ ] **(MVP)** ToS / Acceptable Use templates + authorization attestation
- [ ] Optional billing module: Stripe trial + subscriptions mapped to quotas (off by default)
- [ ] **🚀 v0.1 public release**

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
- [x] Distribution: open source, self-hosted, AGPL-3.0 + attribution
- [x] Auth: self-hosted, built into the API, security-hardened
- [x] Queue: Redis + ARQ
- [x] Name: SecAI
- [ ] Default pricing numbers for the optional billing module
