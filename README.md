# ProtegID

ProtegID es una plataforma MVP para identificadores fisicos de emergencia con QR + NFC. Este repositorio contiene el monorepo con frontend Next.js, backend FastAPI y servicios locales base.

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
- Perfil publico frontend: `http://localhost:8080/p/PID-XXXXXXXXXX`
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

Para validar el build del frontend sin reutilizar los artefactos `.next` del contenedor de desarrollo:

```bash
docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"
```

Evitar ejecutar `npm run build` dentro del contenedor dev vivo si puede mezclar artefactos. En desarrollo, Next usa `.next-dev`; en build, usa `.next`.

## Perfil Publico Frontend

La ruta publica frontend `/p/{public_id}` ya existe. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

- La pagina no requiere login.
- Consulta server-side `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK` y renderiza una ficha de emergencia.
- Si no existe o no esta disponible, responde `404` real usando `notFound()`.
- No expone IDs internos, `device_id`, timestamps ni `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El estado 404 no revela si el `public_id` existe o no.
- La vista es mobile-first, destaca tipo de sangre, contacto y telefono de emergencia.
- Los campos vacios se muestran como `No informado`.

## Estado actual

Existen Auth Foundation, Device Foundation, Public Profile Foundation, QR Foundation y Public Profile Frontend.

Limites actuales: no hay tracking de escaneos, geolocalizacion, notificaciones, NFC funcional, edicion frontend del perfil, descarga publica de QR ni presigned URL publica.
