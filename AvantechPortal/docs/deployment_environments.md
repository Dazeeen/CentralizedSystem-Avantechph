# Deployment Environments

This project now supports explicit environment files for safer deployment:

- `development`: local work (`.env`)
- `deployment`: pre-production validation (`.env.deployment`)
- `production`: live environment (`.env.production`)

Settings loading order:

1. `DJANGO_ENV_FILE` (if set)
2. `.env.<DJANGO_ENV>` (if file exists)
3. `.env` fallback

## Setup

1. Copy template files and fill real secrets:
   - `.env.deployment.example` -> `.env.deployment`
   - `.env.production.example` -> `.env.production`
2. Keep secrets only in actual `.env.*` files on each server.

## Safe deployment flow

Use deployment environment first:

```bash
cd AvantechPortal
chmod +x scripts/deploy.sh
./scripts/deploy.sh deployment
```

Then production:

```bash
cd AvantechPortal
./scripts/deploy.sh production
```

## Built-in guardrails

- `predeploy_check` blocks when:
  - `DJANGO_ENV` does not match target
  - production has `DEBUG=True`
  - production is configured with sqlite3
  - pending migrations exist
- Production settings block startup when:
  - `DJANGO_DEBUG=True`
  - default development secret key is used
  - `localhost` or `127.0.0.1` are in allowed hosts
  - secure cookies are disabled
