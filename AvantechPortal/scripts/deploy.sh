#!/usr/bin/env bash
set -euo pipefail

TARGET_ENV="${1:-}"

if [[ "${TARGET_ENV}" != "deployment" && "${TARGET_ENV}" != "production" ]]; then
  echo "Usage: ./scripts/deploy.sh [deployment|production]"
  exit 1
fi

ENV_FILE=".env.${TARGET_ENV}"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Create it from .env.${TARGET_ENV}.example"
  exit 1
fi

export DJANGO_ENV="${TARGET_ENV}"
export DJANGO_ENV_FILE="${ENV_FILE}"

echo "Running predeploy checks for ${TARGET_ENV}..."
./.venv/bin/python manage.py predeploy_check --target "${TARGET_ENV}"

echo "Applying migrations for ${TARGET_ENV}..."
./.venv/bin/python manage.py migrate --noinput

echo "Deployment steps completed for ${TARGET_ENV}."
