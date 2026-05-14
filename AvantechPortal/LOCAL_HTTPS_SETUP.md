# Local HTTPS Setup (LAN)

## Quick start
Run from project root (`AvantechPortal` folder):

```bash
./scripts_run_local_https.sh 0.0.0.0 8443
```

Open:
- `https://localhost:8443`
- `https://192.168.1.123:8443`

## Important note about trust (no install on end devices)
For browsers to show **fully trusted HTTPS with no warnings** on all end devices, you need a certificate signed by a public CA (for example Let's Encrypt) on a real DNS hostname.

Self-signed certificates (local-only) encrypt traffic but may still show browser warning on end devices unless that certificate/CA is trusted there.

## True no-warning option
Use:
1. Real domain/subdomain (example: `portal.yourdomain.com`)
2. Public CA certificate (Let's Encrypt)
3. Reverse proxy (Nginx/Caddy) terminating TLS
4. LAN DNS/router mapping to your local server

This gives HTTPS without manual certificate installation per device.
