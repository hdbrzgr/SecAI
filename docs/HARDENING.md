# Hardening checklist

Go through this before inviting other people to your instance.

## Server

- [ ] Only ports 80 and 443 are reachable from the internet (plus SSH, ideally restricted to your IP and key-only).
- [ ] Automatic security updates are on for the OS, and Docker is kept current.
- [ ] The web container listens on `127.0.0.1` (the default); only Caddy or your proxy is public.
- [ ] Postgres, Redis, the API and ZAP have no published ports (the default compose file publishes none).

## SecAI settings

- [ ] `SECAI_ENV=production`, `SECAI_WEB_ORIGIN` is `https://…`, and `SECAI_SCAN_ALLOW_PRIVATE` is not set.
- [ ] `SECAI_SECRET_KEY`, `POSTGRES_PASSWORD` and `SECAI_ZAP_API_KEY` are long random values, backed up securely.
- [ ] Every admin account has two-factor authentication turned on.
- [ ] Registration is closed unless you intend to run a public instance.
- [ ] Scan and website limits per workspace match what you're prepared to send from your server's IP.
- [ ] Email (SMTP) is configured so accounts confirm their address and password resets work.

## Scanning responsibly

Scans come from your server's IP address. Anyone receiving unexpected traffic will contact your hosting provider, so:

- [ ] Publish an abuse contact (for example `abuse@your-domain`) and answer it. The terms template in `docs/legal/` has a place for it.
- [ ] Use **Admin → Blocked domains** for sites that ask not to be scanned, and **Admin → Settings → Pause scanning** if something goes wrong.
- [ ] Check the **Admin → Audit log**: every scan records who confirmed they were authorized, when and from which IP.
- [ ] Consider an egress firewall for the worker and ZAP containers that blocks private address ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, and your cloud metadata endpoint). SecAI already refuses these addresses; the firewall is a second line of defense against DNS rebinding inside the external scanners.
- [ ] Tell your hosting provider you run a security scanner if their terms require it.

## Data and AI

- [ ] If AI analysis is on, your terms or privacy notice say that redacted scan findings are sent to Anthropic for analysis.
- [ ] Decide how long to keep scan results and delete old websites/scans accordingly.
- [ ] Database backups are encrypted and stored off the server (see BACKUP.md).
