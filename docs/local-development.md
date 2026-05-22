# Desarrollo Local

## Requisitos

- Docker
- Docker Compose
- Make

## Configuracion

```bash
cp .env.example .env
```

Los valores de `.env.example` son ejemplos locales. No deben usarse como secretos reales fuera del entorno local.

## Levantar servicios

```bash
make up
```

Servicios principales:

- Web via Nginx: `http://localhost:8080`
- API healthcheck: `http://localhost:8080/api/health`
- API readiness: `http://localhost:8080/api/ready`
- Auth register: `http://localhost:8080/api/auth/register`
- Auth login: `http://localhost:8080/api/auth/login`
- Auth me: `http://localhost:8080/api/auth/me`
- Web directa en desarrollo: `http://localhost:3000`
- API directa en desarrollo: `http://localhost:8000/api/health`
- MinIO console: `http://localhost:9001`

## Variables JWT

La API requiere estas variables para emitir y validar access tokens:

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Los valores de `.env.example` son solo para desarrollo local.

## Comandos utiles

```bash
make ps
make logs
make down
make build
```

Validaciones basicas del backend:

```bash
docker compose exec protegid-api python -m compileall app alembic
git diff --check
```

## Migraciones de base de datos

Alembic vive dentro de `apps/api` y lee `DATABASE_URL` desde la configuracion de la API.

```bash
docker compose exec protegid-api alembic current
docker compose exec protegid-api alembic upgrade head
docker compose exec protegid-api alembic history
```

## Auth Foundation

Endpoints actuales:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

`GET /api/auth/me` requiere header `Authorization: Bearer <access_token>`.

No hay refresh token, recuperacion de password ni MFA. Tampoco hay devices, QR, perfil medico, contactos de emergencia ni notificaciones.
