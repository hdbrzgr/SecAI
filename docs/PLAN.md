# SecAI — Project Plan

## 1. Product vision

A self-serve SaaS where developers and small teams scan **their own** web projects:

1. **Website pentest (DAST)** — enter a URL, prove ownership, get an automated external security assessment.
2. **Code scanning (SAST/SCA/secrets)** — connect GitHub, scan repositories for insecure code, vulnerable dependencies, leaked secrets and misconfigurations.
3. **AI analyst** — deduplicates and triages tool output, removes likely false positives, explains each issue in plain language, rates real-world risk, and gives concrete fixes (code snippets / config changes for the detected stack).

**Distribution model: open source & self-hosted.** Anyone can run SecAI on their own server (Docker Compose first, Kubernetes later) under the AGPL-3.0 license, provided they keep the visible "Powered by SecAI by hdbrzgr" attribution (see [NOTICE](../NOTICE)). Instance admins can optionally turn on a billing module (Stripe) to offer SecAI as a hosted service with trials and subscriptions.

## 2. Non-negotiables (legal & safety)

Scanning a site you don't own is illegal in most jurisdictions. These must exist **before** any public launch:

| Control | Why / how |
|---|---|
| **Ownership verification** | DNS TXT record, `/.well-known/secai-verify.txt` file, or `<meta>` tag. No verified target → no active scan. Re-verify periodically. |
| **SSRF / internal-network protection** | Resolve target, block private/loopback/link-local/cloud-metadata ranges (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, ::1, fc00::/7…), re-check on every request to defeat DNS rebinding. Scanners run in an isolated network with egress firewall. |
| **Scan intensity limits** | Rate limits per target, safe defaults (no DoS, no destructive payloads), max duration, kill switch. |
| **Terms of Service + authorization checkbox** | User attests they are authorized; logged with IP + timestamp. |
| **Abuse handling** | Published scanner IP ranges + abuse contact, ability to block a domain globally. |
| **Data handling** | Encrypt findings at rest, retention policy, redact secrets before sending anything to the LLM, never store full source code longer than the scan needs. |
| **Tool licenses** | Check each tool's license for SaaS use (see STACK.md §Licensing). |

## 3. How a scan works (architecture)

```
┌───────────┐   HTTPS   ┌──────────────┐  enqueue  ┌──────────────┐
│  Web app  │ ────────▶ │   API        │ ────────▶ │ Job queue    │
│ (Next.js) │ ◀──────── │  (FastAPI)   │           │ (Redis/ARQ)  │
└───────────┘  SSE/WS   └──────┬───────┘           └──────┬───────┘
                               │                          │
                        ┌──────▼───────┐        ┌─────────▼──────────┐
                        │ PostgreSQL   │◀───────│ Scan orchestrator  │
                        │ (users, scans│        │  runs each tool in │
                        │  findings)   │        │  a sandboxed       │
                        └──────▲───────┘        │  container         │
                               │                └─────────┬──────────┘
                        ┌──────┴───────┐   raw output     │
                        │ AI enrichment│◀── normalizer ◀──┘
                        │ (Claude API) │   (unified finding schema / SARIF)
                        └──────────────┘
```

Pipeline per scan:

1. **Recon** – httpx (alive, tech detection), subdomain enumeration only on verified root domain (optional), TLS check.
2. **Scan** – tools run in parallel in isolated containers (see tool matrix below).
3. **Normalize** – every tool's output converted into one `Finding` schema: `tool, rule_id, title, severity, cwe, owasp, location (url/param or file/line), evidence, raw`.
4. **Deduplicate** – fingerprint by (cwe, location, parameter) to merge the same issue found by several tools.
5. **AI enrichment** – for each finding group: validate/false-positive likelihood, risk explanation, business impact, fix steps tailored to the detected tech stack, references. Plus an executive summary for the whole scan.
6. **Report** – dashboard, per-finding pages, PDF/Markdown export, diff vs. previous scan ("new / fixed / still open").

## 4. Tool matrix

### Phase A — Website pentest (DAST)

| Area | Tool | Notes |
|---|---|---|
| Crawl + web vuln scan | **OWASP ZAP** (baseline + full/active scan via automation framework) | Core engine; supports authenticated scanning later. |
| Template-based CVE/misconfig checks | **Nuclei** (ProjectDiscovery) | Thousands of community templates; fast. |
| Tech fingerprint / liveness | **httpx** | Feeds stack info to the AI for tailored fixes. |
| TLS / SSL config | **testssl.sh** or **sslyze** | sslyze is Python + MIT, easier to embed. |
| Security headers / cookies / CORS | Custom checks (Python) | Cheap, high-value, great for free tier. |
| Port / service exposure | **naabu** (or nmap, see licensing) | Only on verified hosts, top ports. |
| Directory / file exposure | **ffuf** with curated wordlist | `.git/`, `.env`, backups, admin panels. |
| Subdomains (optional) | **subfinder** | Passive only. |

### Phase B — GitHub code scanning

| Area | Tool | Notes |
|---|---|---|
| SAST (multi-language) | **Opengrep** / Semgrep CE engine | Watch rule licensing (STACK.md). |
| Language-specific SAST | Bandit (Python), gosec (Go), Brakeman (Rails), ESLint security plugins | Optional depth. |
| Dependencies (SCA) | **OSV-Scanner** and/or **Trivy fs** | CVEs in lockfiles. |
| Secrets | **Gitleaks** | Scan working tree + git history. |
| IaC / Docker / K8s misconfig | **Trivy config** or **Checkov** | Terraform, Dockerfile, Helm. |
| Output format | **SARIF** everywhere | Makes normalization easy; can also push to GitHub Code Scanning. |

## 5. AI layer design

- **Model routing:** fast/cheap model for per-finding enrichment at volume, stronger model for executive summary, attack-chain reasoning and false-positive adjudication on high/critical findings. (Current candidates: `claude-haiku-4-5` for bulk, `claude-sonnet-5` default, `claude-opus-5-5` for deep analysis.)
- **Structured output:** force JSON schema (tool use / structured outputs) so every enrichment has `verdict, confidence, severity_adjusted, explanation, impact, fix_steps[], code_patch?, references[]`.
- **Grounding:** send the finding + evidence + detected stack + (for SAST) the surrounding code snippet only — never whole repos. Cite CWE/OWASP.
- **Caching:** cache enrichment by finding fingerprint + tool rule id so repeated issues across users cost nothing; use prompt caching for the big static system prompt.
- **Safety:** redact secrets/tokens/PII before LLM calls; the AI never *executes* anything — it only interprets results. Humans (users) decide.
- **Later:** "Chat with your report", auto-generated fix PRs on GitHub, verification re-scan of a single finding.

## 6. Quotas & optional plans

Self-hosted instances use **admin-configurable quotas** (targets, scans/month, AI budget per workspace). The optional **billing module** (disabled by default) maps Stripe plans onto the same quota system. The table below is the default preset for someone running a public hosted instance:

| | Free trial (14 days) | Starter | Pro | Team |
|---|---|---|---|---|
| Verified domains | 1 | 3 | 10 | 30+ |
| Scan type | Passive/baseline + headers/TLS | + Active ZAP + Nuclei | + Authenticated scans, ports, dir exposure | All |
| Scans / month | 3 | 20 | 100 | Custom |
| GitHub repos | 1 public | 3 | 20 | Unlimited |
| Scheduled scans | – | Weekly | Daily | Daily + CI |
| AI fix guidance | Top 5 findings | All | All + code patches | All + fix PRs |
| Reports | Web | + PDF | + PDF/branding | + SSO, seats |

Enforce limits in the API (quota table). When billing is enabled, Stripe webhooks update the workspace's quota/plan.

## 7. Phased roadmap

| Phase | Goal | Outcome |
|---|---|---|
| **0. Foundation** (1–2 wks) | Repo, CI, Docker Compose, secure self-hosted auth, DB schema, license/attribution | Users can sign up (with optional 2FA) and see an empty dashboard. |
| **1. DAST MVP** (3–4 wks) | Domain verification + headers/TLS/Nuclei/ZAP baseline + normalizer | First real scan report (raw findings). |
| **2. AI reports** (2 wks) | Enrichment pipeline, summary, fix guidance, PDF | "Aha" moment: readable, prioritized report. |
| **3. Self-host release** (1–2 wks) | Quotas, admin panel, emails, install docs, optional Stripe billing module | **v0.1 public release.** |
| **4. GitHub SAST** (3–4 wks) | GitHub App, repo scan with Opengrep/OSV/Gitleaks/Trivy | Code scanning reports. |
| **5. Depth & retention** (ongoing) | Scheduled scans, diffs, authenticated DAST, PR comments/checks, auto-fix PRs, Slack/email alerts, team accounts | Stickiness & upsell. |

Detailed checklist: see [TODO.md](TODO.md).

## 8. Key risks

| Risk | Mitigation |
|---|---|
| Platform abused to attack third parties | Ownership verification, SSRF guard, rate limits, abuse process. |
| Scanner crashes / harms a customer site | Safe default policies, throttling, max request budget, off-peak scheduling option. |
| False positives erode trust | AI adjudication + confidence score + "mark as false positive" feedback loop. |
| LLM cost per scan | Dedup + caching + model routing; cap AI calls per plan. |
| Sandbox escape / compromised worker | Rootless containers, no secrets in worker env, ephemeral workers, network egress allowlist. |
| Leaking customer code/findings | Encryption at rest, per-tenant isolation in queries, short-lived clone dirs, GitHub App least privilege (read-only contents). |
