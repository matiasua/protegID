# ProtegID

ProtegID es una plataforma MVP para identificadores fisicos de emergencia con QR + NFC. Este repositorio contiene el setup base del monorepo, sin logica de negocio implementada todavia.

## Stack

- Frontend: Next.js + TypeScript + Tailwind CSS + shadcn/ui
- Backend: FastAPI + Python
- DB: PostgreSQL
- Queue/cache: Redis
- Worker: Python
- Archivos: MinIO compatible S3
- Reverse proxy: Nginx
- Entorno local: Docker Compose

## Estructura

```text
apps/
  web/        Frontend Next.js.
  api/        API FastAPI y worker Python base.
infra/
  nginx/      Reverse proxy local.
  scripts/    Espacio para scripts de infraestructura.
docs/         Arquitectura, desarrollo local, seguridad y reglas para IA.
```

## Servicios locales

- `protegid-web`
- `protegid-api`
- `protegid-worker`
- `protegid-db`
- `protegid-redis`
- `protegid-minio`
- `protegid-nginx`

## Primer uso

```bash
cp .env.example .env
make up
```

La aplicacion queda disponible en:

- Web via Nginx: `http://localhost:8080`
- API healthcheck via Nginx: `http://localhost:8080/api/health`
- API readiness via Nginx: `http://localhost:8080/api/ready`
- MinIO console: `http://localhost:9001`

## Comandos

```bash
make up       # Levanta el entorno local
make down     # Detiene los servicios
make logs     # Muestra logs de todos los servicios
make ps       # Lista servicios
make build    # Construye imagenes
```

## Estado actual

Este setup inicial no implementa login, generacion de QR, modelos de base de datos, identificadores publicos, logica medica ni funcionalidades de negocio.

La estructura queda preparada para indexarse con Code Graph mas adelante, pero Code Graph no esta activado ni configurado en esta tarea.
