#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="$ROOT_DIR/.certs"
CERT_FILE="$CERT_DIR/local.crt"
KEY_FILE="$CERT_DIR/local.key"
VENV_PY="$ROOT_DIR/../.venv/bin/python"
HOST="${1:-0.0.0.0}"
PORT="${2:-8443}"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Error: Python venv not found at $VENV_PY"
  exit 1
fi

mkdir -p "$CERT_DIR"

if [[ ! -f "$CERT_FILE" || ! -f "$KEY_FILE" ]]; then
  echo "Generating local self-signed certificate..."
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 825 \
    -subj "/C=PH/ST=NCR/L=Muntinlupa/O=AvanTech/OU=IT/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:192.168.1.123"
fi

cd "$ROOT_DIR"

if ! "$VENV_PY" -c "import uvicorn" >/dev/null 2>&1; then
  echo "Installing uvicorn into .venv..."
  "$VENV_PY" -m pip install uvicorn
fi

echo "Starting HTTPS server at https://${HOST}:${PORT}"
"$VENV_PY" -m uvicorn AvantechPortal.asgi:application \
  --host "$HOST" \
  --port "$PORT" \
  --ssl-keyfile "$KEY_FILE" \
  --ssl-certfile "$CERT_FILE"
