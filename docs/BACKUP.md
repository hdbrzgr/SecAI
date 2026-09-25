# Backing up and restoring SecAI

## What to back up

| What | Why |
|---|---|
| The Postgres database | Accounts, websites, scans, findings, audit log |
| `.env` | Especially `SECAI_SECRET_KEY`: without it, 2FA secrets can't be decrypted and every user with 2FA is locked out |
| The `caddy-data` volume (optional) | Certificates; Caddy can request new ones if it's lost |

Redis only holds job queues and rate-limit counters, and ZAP starts a fresh session per scan: neither needs a backup.

Keep `.env` and database dumps somewhere encrypted and off the server. They contain password hashes, scan results for your users' websites and the key that protects 2FA secrets.

## Back up

```bash
docker compose exec -T postgres pg_dump -U secai -Fc secai > secai-$(date +%F).dump
```

A daily cron job is a sensible default:

```cron
15 3 * * * cd /opt/SecAI && docker compose exec -T postgres pg_dump -U secai -Fc secai > /var/backups/secai/secai-$(date +\%F).dump && find /var/backups/secai -name '*.dump' -mtime +14 -delete
```

## Restore

```bash
docker compose stop api worker web
docker compose exec -T postgres dropdb -U secai secai
docker compose exec -T postgres createdb -U secai secai
docker compose exec -T postgres pg_restore -U secai -d secai < secai-2026-09-25.dump
docker compose start api worker web
```

Restore onto a server whose `.env` has the **same `SECAI_SECRET_KEY`** as when the dump was made.

Test a restore on a spare machine now and then: a backup you've never restored is a guess.
