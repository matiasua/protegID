# Arquitectura

ProtegID usa un monorepo con un frontend Next.js, un backend FastAPI, un worker Python y servicios de soporte locales mediante Docker Compose.

## Componentes

- `apps/web`: interfaz web en Next.js, TypeScript, Tailwind CSS y shadcn/ui.
- `apps/api`: API FastAPI, worker Python base y migraciones Alembic.
- `infra/nginx`: Nginx como reverse proxy local.
- `infra/scripts`: scripts futuros de infraestructura.
- `docs`: documentacion tecnica del proyecto.

## Flujo local

Nginx recibe trafico HTTP en `localhost:8080`.

- `/` se enruta hacia `protegid-web:3000`.
- `/api/*` se enruta hacia `protegid-api:8000`.

PostgreSQL, Redis y MinIO quedan disponibles para funcionalidades actuales y futuras. Alembic esta configurado y el backend ya incluye las tablas de negocio `users`, `devices` y `emergency_profiles`.

## Auth Foundation

El backend incluye la base de autenticacion de Sprint 2:

- Modelo SQLAlchemy `User`.
- Tabla `users` gestionada por Alembic.
- Hashing de passwords con Argon2 mediante `pwdlib`.
- JWT access token para autenticacion Bearer.
- Endpoints actuales:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`

`GET /api/auth/me` requiere un token Bearer valido. No existe refresh token, recuperacion de password ni MFA en el estado actual.

## Device Foundation

El backend incluye la base de dispositivos de Sprint 3:

- Modelo SQLAlchemy `Device`.
- Tabla `devices` gestionada por Alembic.
- Relacion nullable `devices.user_id -> users.id` para permitir dispositivos pendientes antes de ser activados por un usuario.
- `public_id` unico y visible con formato `PID-XXXXXXXXXX`.
- El alfabeto de `public_id` evita caracteres confusos: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`.
- `public_id` no es secuencial y no usa el UUID interno completo como identificador publico.

Estados actuales de `Device`:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints actuales de devices:

- `GET /api/devices`
- `POST /api/devices/activate`
- `POST /api/admin/devices`

`GET /api/devices` requiere token Bearer y solo lista dispositivos del usuario autenticado. `POST /api/devices/activate` requiere token Bearer y activa un dispositivo `pending_activation` para el usuario autenticado. `POST /api/admin/devices` requiere token Bearer y `role=admin`.

## Public Profile Foundation

El backend incluye la base de perfiles publicos de emergencia de Sprint 4:

- Modelo SQLAlchemy `EmergencyProfile`.
- Tabla `emergency_profiles` gestionada por Alembic.
- Relacion unica y obligatoria `emergency_profiles.device_id -> devices.id`.
- Un perfil de emergencia queda asociado a un unico device.
- Los endpoints privados requieren token Bearer y validan ownership con `current_user.id == device.user_id`.

Endpoints privados de perfiles de emergencia:

- `GET /api/devices/{device_id}/emergency-profile`
- `PUT /api/devices/{device_id}/emergency-profile`

Endpoint publico de perfil de emergencia:

- `GET /api/public/profiles/{public_id}`

El endpoint publico no requiere autenticacion. Busca por `Device.public_id` y solo responde si el device esta `active`, el perfil tiene `is_public == true` y `deleted_at is null`. La respuesta publica no expone `id`, `device_id`, `created_at`, `updated_at` ni `deleted_at`.

## Limites de esta etapa

No hay generacion de QR, escritura NFC, frontend `/p/{public_id}`, notificaciones, geolocalizacion, historial de escaneos, subida de archivos medicos, refresh token, recuperacion de password ni MFA.

`device_type="qr_nfc_tag"` existe solo como base del modelo de dispositivo. No representa una implementacion actual de QR ni NFC.

## CodeGraph

CodeGraph esta inicializado y operativo para este proyecto. OpenCode tiene integracion MCP con herramientas `codegraph_*`, que deben usarse para busquedas estructurales del proyecto antes de cambios relevantes.

La carpeta `.codegraph/` no debe modificarse manualmente ni subirse como indice del proyecto.
