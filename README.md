# JOAOTESTE — Gestão de Mesas e Filas (V0)

Plataforma SaaS para reduzir o trabalho manual de restaurantes na gestão de mesas e filas.

## Stack
- Backend: Python + Flask, SQLAlchemy 2.x, Alembic, PostgreSQL
- Frontend: Next.js/React
- Auth: JWT (cookies HttpOnly Secure), Argon2id, RBAC, tenant isolation
- Infra: Docker, Nginx, Redis
- Background: Celery + Redis
- Testes: pytest, Playwright
- CI/CD: GitHub Actions
- Observabilidade: Sentry
