# Security Policy

## Supported Versions
The `main` branch is actively maintained. Security fixes are released on demand.

## Reporting a Vulnerability
Please **do not** open public issues for security problems. Instead email:
- Gajewa2014@gmail.com (or create a private discussion)
Include steps to reproduce and any logs. We aim to respond within 72 hours.

## Best Practices (Deployment)
- Set strong `AUTH_TOKEN` or use JWT (`JWT_SECRET`, `JWT_ALG`).
- Restrict `CORS_ORIGINS` to trusted domains.
- Keep `.env` out of version control; use secrets manager.
- Run behind a reverse proxy (nginx/traefik) with HTTPS.
- Rotate secrets regularly; enable rate limiting and audit logging.
