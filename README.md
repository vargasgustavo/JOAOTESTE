# Gestão de Mesas e Filas — V0

Plataforma SaaS que tira do papel (e do grito) a gestão de mesas e filas de restaurantes.
O objetivo do V0 é **um clique**: o garçom toca em "LIBERAR MESA" e o sistema chama
sozinho o próximo grupo compatível da fila, notifica o cliente e atualiza o painel.

```
Mesa OCUPADA ──"LIBERAR MESA"──▶ LIMPEZA ──▶ DISPONÍVEL
                                                │
                     TableAllocationService ────┘  (FIFO compatível, atômico)
                                                │
             fila: João(4) Maria(2) Pedro(5) ───┴──▶ João é CHAMADO
                                                     mesa vira RESERVADA
                                                     eventos + notificação (Celery)
```

---

## Sumário

- [Subindo o projeto](#subindo-o-projeto)
- [Credenciais do seed](#credenciais-do-seed)
- [Telas](#telas)
- [Arquitetura](#arquitetura)
- [Domínio e regras](#domínio-e-regras)
- [API](#api)
- [Decisões de segurança](#decisões-de-segurança)
- [Estimativa de espera](#estimativa-de-espera)
- [Testes](#testes)
- [Desenvolvimento sem Docker](#desenvolvimento-sem-docker)
- [CI](#ci)
- [Escopo do V0](#escopo-do-v0)

---

## Subindo o projeto

Pré-requisitos: Docker + Docker Compose.

```bash
cp .env.example .env          # Windows: copy .env.example .env
# gere segredos reais:  python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up --build
```

Acesse **http://localhost:8080** (porta configurável em `HTTP_PORT`).

O que sobe:

| Serviço    | Papel                                                        | Porta no host |
|------------|--------------------------------------------------------------|---------------|
| `nginx`    | Proxy único (`/` → frontend, `/api/` → backend) + headers    | `8080`        |
| `web`      | Next.js 14 (standalone, usuário non-root)                    | interna       |
| `api`      | Flask + Gunicorn; roda `alembic upgrade head` no start        | interna       |
| `worker`   | Celery consumindo a fila de notificações                     | interna       |
| `postgres` | PostgreSQL 16                                                | interna       |
| `redis`    | Broker do Celery, rate limiting e denylist de JWT            | interna       |

Só o Nginx expõe porta: banco, cache e aplicação ficam na rede interna do compose.
O seed roda automaticamente no primeiro start (`RUN_SEED=true`); coloque `false` para desligar.

> Em produção: `ENV=production`, `COOKIE_SECURE=true`, segredos fortes e TLS terminando
> no Nginx (o HSTS já vai nas respostas). A aplicação **se recusa a subir** em produção
> com `SECRET_KEY`/`JWT_SECRET_KEY` no valor padrão.

## Credenciais do seed

Cenário criado: restaurante **Cantina do Porto**, 10 mesas (a nº 5 já em limpeza,
as demais ocupadas) e 5 clientes na fila — João(4), Maria(2), Pedro(5), Ana(3), Carlos(6).

| Perfil            | E-mail                          | Senha           |
|-------------------|---------------------------------|-----------------|
| RESTAURANT_ADMIN  | `admin@cantinadoporto.com.br`   | `TrocarEsta123` |
| STAFF             | `staff@cantinadoporto.com.br`   | `TrocarEsta123` |

Senhas apenas de desenvolvimento (defina `SEED_ADMIN_PASSWORD` / `SEED_STAFF_PASSWORD`
para sobrescrever; em `ENV=production` elas são obrigatórias).

**Roteiro de aceite (2 minutos):** entre como staff em `/staff`, toque na mesa 5 (amarela,
em limpeza), pressione **LIBERAR MESA** e veja o toast "João Almeida (4 pessoas)".
A mesa fica azul (reservada) e, em `/admin`, o dashboard e a fila refletem a mudança.
Abrindo o ticket do cliente (`/fila/{id}`) a tela mostra "Sua mesa está pronta".

## Telas

| Rota                   | Perfil   | O que faz                                                                 |
|------------------------|----------|---------------------------------------------------------------------------|
| `/`                    | público  | Lista de restaurantes abertos                                             |
| `/restaurantes/{id}`   | público  | Espera estimada, grupos aguardando e formulário de entrada na fila        |
| `/fila/{id}`           | público  | Acompanhamento: "Sua posição: #3", tempo estimado, destaque quando chamado |
| `/login`               | —        | Login (cookies HttpOnly)                                                  |
| `/staff`               | staff    | Grid do salão colorido por status → toca a mesa → botão grande de ação    |
| `/admin`               | admin    | Métricas, mapa do salão, fila e CRUD de mesas                             |

Layout responsivo (celular/tablet/desktop), alvos de toque grandes e polling contínuo
(6s no salão do staff, 7s no ticket do cliente, 8s no painel admin). O cliente nunca vê
dados internos: o ticket expõe apenas posição, estimativa e status do próprio grupo.

## Arquitetura

```
frontend/ (Next.js App Router)
  src/app        rotas e telas
  src/components TableCard, Toast
  src/lib        cliente HTTP (CSRF automático), hooks de polling, formatação

backend/
  app/controllers   HTTP: parse, chamada do service, resposta  ← sem regra de negócio
  app/schemas       pydantic estrito (extra="forbid")
  app/services      REGRA DE NEGÓCIO (Auth, Table, Queue, Allocation, WaitTime, Event, Notification)
  app/repositories  acesso a dados, sempre filtrando por restaurant_id
  app/models        SQLAlchemy 2.x tipado
  app/security      Argon2id, JWT, denylist, RBAC, CSRF, headers
  app/tasks         Celery (notificações assíncronas)
  migrations        Alembic
  tests             pytest
nginx/              proxy + headers de segurança
```

Regra de ouro: **controller não decide nada**. Ele valida o payload com o schema, chama o
service e serializa. Toda transição de estado, evento e notificação nasce em um service, o
que mantém as regras testáveis sem HTTP e reaproveitáveis por outros canais (Celery, CLI).

O `NotificationService` fala com uma abstração `NotificationProvider`
(`send_whatsapp` / `send_sms` / `send_web_notification`). O V0 usa `MockProvider`; plugar
Twilio/Meta é escrever uma classe nova e trocar `NOTIFICATION_PROVIDER` no `.env` — nenhum
outro arquivo muda.

## Domínio e regras

**Entidades:** `User`, `Restaurant`, `Table`, `QueueEntry`, `TableEvent`, `Notification`.
Índices dedicados em `queue_entries(restaurant_id, status, joined_at)` e
`tables(restaurant_id, status)` — as duas leituras quentes do produto.

**Transições de mesa** (qualquer outra → **HTTP 409**):

```
OCCUPIED ──▶ CLEANING ──▶ AVAILABLE ──▶ RESERVED ──▶ OCCUPIED
                              ▲              │
                              └──────────────┘  (cliente não apareceu)
```

`RESERVED → OCCUPIED` marca a `QueueEntry` como `SEATED` (com `seated_at`) e gera
`CUSTOMER_SEATED`. "LIBERAR MESA" é idempotente em relação ao caminho: a partir de
`OCCUPIED` ele passa por `CLEANING` e chega em `AVAILABLE` numa única requisição.

**Alocação automática** (`TableAllocationService`, o cérebro):

1. Dispara quando uma mesa fica `AVAILABLE` **e** quando um cliente entra na fila.
2. Varre os `WAITING` em ordem FIFO (`joined_at`) e escolhe o **primeiro compatível**
   (`party_size <= capacity`) — mesa de 4 com fila João(4)/Maria(2)/Pedro(5) chama **João**.
3. Tudo em uma transação: `SELECT ... FOR UPDATE SKIP LOCKED` na mesa e na entrada da fila,
   então duas liberações simultâneas nunca chamam o mesmo cliente nem alocam a mesma mesa.
4. Entrada vira `CALLED` (`called_at`), mesa vira `RESERVED`, nascem os eventos
   `CUSTOMER_ASSIGNED` e `CUSTOMER_CALLED` e a notificação é enfileirada no Celery.
5. `POST /tables/{id}/allocate` é o fallback manual, com a mesma lógica.

**Eventos** (`TableEvent`, com `metadata` JSONB): `TABLE_OCCUPIED`, `TABLE_CLEANING`,
`TABLE_AVAILABLE`, `CUSTOMER_ASSIGNED`, `CUSTOMER_CALLED`, `CUSTOMER_SEATED`. Toda ação
relevante vira evento — é a trilha de auditoria e a matéria-prima da estimativa de espera.

**Mensagem enviada ao cliente:**
`Olá, João! Sua mesa está pronta no Restaurante X. Dirija-se à recepção.`

## API

Prefixo pelo browser: `/api/*` (Nginx/rewrite do Next removem o prefixo antes do Flask).

| Método | Rota | Acesso |
|---|---|---|
| POST | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` | público |
| GET | `/auth/me`, `/auth/csrf` | autenticado / público |
| GET | `/restaurants`, `/restaurants/{id}` | público |
| POST | `/restaurants` | autenticado (promove a RESTAURANT_ADMIN) |
| PUT | `/restaurants/{id}` | admin do tenant |
| GET/POST | `/restaurants/{id}/tables` | staff / admin |
| PUT | `/tables/{id}` | admin |
| POST | `/tables/{id}/release`, `/occupy`, `/cleaning`, `/allocate` | staff / admin |
| GET/POST | `/restaurants/{id}/queue` | staff+admin / público |
| GET | `/queue/{id}` | público (posição + estimativa do próprio ticket) |
| POST | `/queue/{id}/cancel` | público (dono do ticket) |
| GET | `/restaurants/{id}/dashboard` | staff / admin |
| GET | `/health`, `/health/ready` | público (liveness/readiness) |

O dashboard (total de mesas, ocupadas, em limpeza, disponíveis, clientes na fila e tempo
médio) é resolvido em **uma query agregada** com `FILTER`/`CASE` em vez de seis contagens —
há teste garantindo que o número de SELECTs não cresce.

## Decisões de segurança

| Risco | Como tratamos |
|---|---|
| Vazamento de senhas | **Argon2id** (`argon2-cffi`), parâmetros explícitos, rehash automático quando o custo muda, comparação em tempo constante e hash falso no login inexistente (anti *user enumeration*) |
| Roubo de token | JWT de **15 min** em cookie `HttpOnly` + `Secure` + `SameSite=Lax`; refresh de 14 dias com **rotação** (o antigo é revogado no uso) e **denylist por `jti` no Redis** com TTL igual ao do token — logout revoga de verdade |
| CSRF | Double-submit: cookie legível `csrf_token` + header `X-CSRF-Token`, exigido em **toda** rota mutável por um guard global (nada depende do programador lembrar) |
| Escalada de privilégio | RBAC por decorator (`@require_role`) em todas as rotas protegidas; papéis `CUSTOMER`/`RESTAURANT_ADMIN`/`STAFF` |
| **IDOR / BOLA** | `restaurant_id` vem **sempre do token**, nunca do path/body; os repositories só expõem métodos com filtro de tenant. Acessar mesa de outro restaurante devolve 404, não 403 (não confirma existência) |
| Entrada maliciosa | pydantic com `extra="forbid"` (campo desconhecido = 422), limites de tamanho, telefone/e-mail normalizados; `party_size` e capacidade com faixas explícitas |
| Força bruta / flood | Flask-Limiter com storage Redis: `10/min` em auth e `5/min` na entrada da fila, além do limite global |
| XSS / clickjacking | CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` e HSTS no Nginx **e** no Flask (defesa em profundidade se a API for exposta direto) |
| CORS | Lista fechada de origens (`CORS_ORIGINS`) com credenciais; em produção o tráfego é same-origin via Nginx |
| SQL injection | 100% SQLAlchemy com bind params; zero SQL concatenado |
| Segredos | Só por env (`.env.example` versionado, `.env` no `.gitignore`); nenhum DSN/segredo no repositório; Sentry só liga se `SENTRY_DSN` existir |
| PII em log | Filtro global que mascara telefone e e-mail (`***8888`, `c***@dominio`) em qualquer mensagem, inclusive de terceiros |
| IDs previsíveis | UUIDv4 públicos, sem sequência exposta |
| Race condition | Transação + `SELECT FOR UPDATE SKIP LOCKED` (teste com threads concorrentes em PostgreSQL) |
| Superfície do container | Imagens slim/alpine, **usuário non-root**, dependências pinadas, `.dockerignore` enxuto |
| Broker fora do ar | A publicação da notificação usa timeout curto e `retry=False`: se o Redis cair, a mesa **ainda é liberada** (a notificação fica `PENDING` e é logada) em vez de travar o garçom |

Detalhe que vale o comentário: identidade autenticada vive em `flask.g` e é **limpa a cada
request** por um `before_request`. Sem isso, um app context reaproveitado (cenário comum em
testes e em alguns servidores) faria um token já revogado continuar valendo — foi um bug
real encontrado pelos testes e corrigido.

## Estimativa de espera

`WaitTimeService`, isolado do resto:

```
espera ≈ ceil(posição na fila) × tempo médio de giro
```

O tempo médio de giro sai dos eventos reais: para cada mesa, o intervalo entre
`TABLE_AVAILABLE` e o `TABLE_OCCUPIED` seguinte (janela de `TURNOVER_SAMPLE_HOURS`,
limitado a `TURNOVER_SAMPLE_SIZE` amostras). Sem histórico suficiente, cai no
fallback de **15 minutos** (`DEFAULT_WAIT_MINUTES`). A leitura é uma única query com
window function, então o dashboard continua barato.

## Testes

```bash
cd backend
pytest -q                 # 83 testes (2 pulados fora do PostgreSQL)
ruff check .

cd ../frontend
npm run typecheck && npm run build
npx playwright test       # E2E: staff libera mesa → cliente é chamado
```

Cobertura funcional: alocação FIFO compatível (o caso João/Maria/Pedro do enunciado),
transições inválidas devolvendo 409, corrida entre liberações simultâneas, RBAC,
isolamento de tenant (IDOR), rate limiting, rotação/revogação de token, CSRF, estimativa
de espera, dashboard e resiliência a broker indisponível.

Os testes rodam em SQLite por padrão; defina `TEST_DATABASE_URL` apontando para PostgreSQL
para incluir os dois testes de concorrência real (`FOR UPDATE SKIP LOCKED`), que são
pulados fora do Postgres — é exatamente o que o CI faz.

## Desenvolvimento sem Docker

```bash
# backend
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
export SECRET_KEY=... JWT_SECRET_KEY=... DATABASE_URL=postgresql+psycopg://...
alembic upgrade head && python seed.py
python wsgi.py                                   # http://127.0.0.1:8000
celery -A celery_worker.celery worker -l info    # opcional (notificações)

# frontend
cd frontend && npm install && npm run dev        # http://127.0.0.1:3000
```

Sem Redis o app cai para uma denylist em memória e avisa no log — aceitável em dev,
nunca em produção (é single-process).

## CI

GitHub Actions em quatro jobs: **backend** (ruff + migrations do zero + pytest com
PostgreSQL e Redis reais), **frontend** (typecheck + build), **e2e** (Playwright contra a
stack completa) e **docker** (build das duas imagens).

## Escopo do V0

Dentro: mesas, fila, alocação automática, eventos, notificação mock, estimativa de espera,
dashboard e as três interfaces.
Fora, de propósito: CRM, marketplace, reservas com agendamento, pagamentos, visão
computacional e qualquer IA.
