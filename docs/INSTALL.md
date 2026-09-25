# Installing SecAI

This guide sets up SecAI on one Linux server with Docker Compose and HTTPS. It takes about 20 minutes.

## What you need

- A Linux server (Ubuntu 24.04 or Debian 12 work well) with **4 GB RAM** or more. OWASP ZAP alone uses up to 2 GB. 2 vCPUs and 20 GB of disk are enough to start.
- A domain name, for example `secai.example.com`, with an `A` (and `AAAA` if you have IPv6) record pointing at the server.
- Ports **80** and **443** open to the internet. Keep everything else closed.
- Docker Engine 24+ with the Compose plugin: https://docs.docker.com/engine/install/
- Optional: an SMTP account for email, and an Anthropic API key for AI analysis.

## 1. Get the code

```bash
git clone https://github.com/hdbrzgr/SecAI.git
cd SecAI
cp .env.example .env
```

## 2. Configure `.env`

Generate three secrets and put them in `.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # run three times
```

| Setting | Value |
|---|---|
| `SECAI_SECRET_KEY` | secret 1 (encrypts 2FA secrets: **back it up**, see BACKUP.md) |
| `POSTGRES_PASSWORD` | secret 2 |
| `SECAI_ZAP_API_KEY` | secret 3 |
| `SECAI_ENV` | `production` |
| `SECAI_WEB_ORIGIN` | `https://secai.example.com` |
| `SECAI_DOMAIN` | `secai.example.com` |

In production the API refuses to start with a weak secret key, a plain `http://` origin, or `SECAI_SCAN_ALLOW_PRIVATE` turned on.

### Email (recommended)

With SMTP configured, SecAI sends email confirmation links, password reset links and "scan finished" notices, and new accounts must confirm their address before adding websites. Without it those features are off and password resets need an admin.

```ini
SECAI_SMTP_HOST=smtp.example.com
SECAI_SMTP_PORT=587
SECAI_SMTP_USERNAME=secai@example.com
SECAI_SMTP_PASSWORD=...
SECAI_SMTP_FROM=SecAI <secai@example.com>
SECAI_SMTP_SECURITY=starttls
```

Any provider with SMTP works (Postmark, Amazon SES, Mailgun, Fastmail, your own server). Set up SPF and DKIM for the sending domain so the mail isn't marked as spam.

### AI analysis (optional)

```ini
SECAI_ANTHROPIC_API_KEY=sk-ant-...
```

Each finished scan makes one request to the Claude API with redacted scanner output. You pay Anthropic directly for usage; the admin overview shows the tokens used in the last 30 days.

## 3. Start SecAI

```bash
docker compose --profile https up -d --build
```

The first build takes several minutes (the worker image downloads the Nuclei templates). Caddy then gets a certificate from Let's Encrypt for `SECAI_DOMAIN`. Check that everything is healthy:

```bash
docker compose --profile https ps
curl https://secai.example.com/api/health/ready     # {"status":"ready"}
```

## 4. Create the admin account

Open `https://secai.example.com/register` and create your account. **The first account on an instance becomes its admin.** Then:

1. Turn on two-factor authentication (Settings).
2. In **Admin → Settings**, decide whether anyone may sign up. For a private instance, turn "Anyone can create an account" off after creating the accounts you need.
3. Set the scan and website limits per workspace.
4. Put your terms and acceptable use policy in place (templates in `docs/legal/`) and publish an abuse contact.

## 5. Check a scan

Add a website you own, prove ownership, run a scan, and open the report. **Admin → Overview** shows whether email, ZAP and AI analysis are configured.

## Trying it locally

For a quick look on your own machine, skip the domain and HTTPS: keep `SECAI_ENV=development` and `SECAI_WEB_ORIGIN=http://localhost:3000`, then run `docker compose up -d --build` and open http://localhost:3000. The scanner still refuses private and local addresses, so scan a public site you own.

## Using your own reverse proxy

If you already run nginx, Traefik or a load balancer, leave out `--profile https` and proxy to `127.0.0.1:3000`. It must:

- terminate TLS and set `SECAI_WEB_ORIGIN` to the public `https://` URL,
- **overwrite** (not append to) `X-Forwarded-For` with the client address, so per-IP rate limits can't be bypassed,
- pass the `Origin` header through unchanged (SecAI rejects cross-origin writes).

Next: [UPGRADE.md](UPGRADE.md), [BACKUP.md](BACKUP.md), [HARDENING.md](HARDENING.md).
