# Upgrading SecAI

Database migrations run automatically when the `api` container starts, so an upgrade is: back up, pull, rebuild, restart.

```bash
cd SecAI
# 1. Back up first (see BACKUP.md)
docker compose exec -T postgres pg_dump -U secai -Fc secai > backup-$(date +%F).dump

# 2. Get the new version
git fetch --tags
git checkout <new version tag or main>

# 3. Compare your .env with .env.example for new settings
diff <(grep -o '^#\? *SECAI_[A-Z_]*' .env.example | tr -d '# ' | sort -u) \
     <(grep -o '^SECAI_[A-Z_]*' .env | sort -u)

# 4. Rebuild and restart
docker compose --profile https up -d --build

# 5. Check
docker compose --profile https ps
docker compose logs --tail 50 api worker
```

Rebuilding the worker also refreshes the Nuclei templates. Rebuild monthly even without a new SecAI version so new CVE templates are picked up:

```bash
docker compose build --no-cache worker && docker compose up -d worker
```

## Rolling back

Check out the previous version and rebuild. If the new version already migrated the database and the old one can't read it, restore the backup you took in step 1 (see BACKUP.md).
