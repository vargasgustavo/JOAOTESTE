# 🍽️ Restaurant Queue Manager

A full-stack SaaS platform for restaurant table and queue management.

**Stack:** Flask + SQLAlchemy 2.x + Next.js + PostgreSQL + Redis + Celery + Nginx

## Architecture

```
Internet → Nginx (:80) → Next.js Frontend (:3000)
                       → Flask API (:5000) → PostgreSQL
                                           → Redis ← Celery Worker

Backend: Controllers → Schemas → Services → Repositories → Models
```

## Security

| Feature | Implementation |
|---------|---------------|
| Passwords | Argon2id (argon2-cffi) |
| Auth | JWT in HttpOnly+Secure+SameSite=Strict cookies |
| CSRF | Double-Submit Cookie (X-CSRF-Token) |
| RBAC | CUSTOMER / STAFF / RESTAURANT_ADMIN |
| Tenant isolation | restaurant_id from JWT only, never request body |
| Validation | marshmallow unknown=RAISE |
| Rate limiting | Flask-Limiter + Redis |
| Security headers | Nginx: CSP, HSTS, X-Frame-Options, X-Content-Type |
| Race conditions | SELECT FOR UPDATE SKIP LOCKED |
| IDs | UUID v4 (non-sequential) |
| Containers | Non-root users, multi-stage slim images |

## Quick Start

```bash
cp .env.example .env
# Edit .env: SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD

docker-compose up --build -d
docker-compose exec app flask db upgrade
docker-compose exec app python seed.py
open http://localhost
```

## Seed Credentials

| Role | Phone | Password |
|------|-------|----------|
| RESTAURANT_ADMIN | 11111111111 | Admin@123 |
| STAFF | 11222222222 | Staff@123 |
| CUSTOMER | 11333333333 | Customer@123 |

## Table Status Machine

```
OCCUPIED → CLEANING → AVAILABLE → RESERVED → OCCUPIED
         (release)  (cleaning)  (alloc)    (occupy)

Invalid transitions → HTTP 409
```

## TableAllocation (FIFO + race-safe)

1. Table becomes AVAILABLE
2. SELECT FOR UPDATE SKIP LOCKED on WAITING queue entries (FIFO)
3. First entry with party_size ≤ capacity wins → CALLED
4. Table → RESERVED
5. Celery sends async notification

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## CI/CD

GitHub Actions: ruff lint → pytest → docker build (backend + frontend)

## Environment Variables

See `.env.example` — never commit real values.
