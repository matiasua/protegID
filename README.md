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
- Dashboard privado temporal: `http://localhost:8080/dashboard`
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

## Dashboard Privado Inicial

La primera version del frontend privado de gestion de perfiles de emergencia existe en `/dashboard`.

- Es una pantalla temporal de validacion manual por access token.
- Permite pegar manualmente un JWT y validarlo contra `GET /api/auth/me`.
- Si la sesion es valida, carga dispositivos con `GET /api/devices`.
- Permite seleccionar un dispositivo y cargar su perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Permite crear o actualizar el perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- El token se guarda solo en state React; no se guarda en `localStorage` ni cookies.
- No hay login frontend completo, refresh token ni sesion persistente.

Campos editables del perfil: `display_name`, `blood_type`, `allergies`, `medical_conditions`, `medications`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes` e `is_public`.

`is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.

UX actual de `/dashboard`: `Panel privado ProtegID`, `Estado de sesion`, `Mis dispositivos`, `Editar perfil`, `Guardar perfil` y estados de carga, error y exito.

Validacion esperada:

- `docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"`
- `GET /dashboard` responde `200 OK`.
- Validacion funcional manual con JWT vigente.

## Estado actual

Existen Auth Foundation, Device Foundation, Public Profile Foundation, QR Foundation, Public Profile Frontend y Private Profile Management Frontend inicial.

Limites actuales: no hay login frontend completo, registro frontend completo, recuperacion de password, refresh token, control de sesion persistente, subida de archivos medicos, gestion de QR desde frontend, NFC funcional, tracking de escaneos, geolocalizacion ni notificaciones.
