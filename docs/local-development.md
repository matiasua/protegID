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
- Devices list: `http://localhost:8080/api/devices`
- Device activate: `http://localhost:8080/api/devices/activate`
- Admin device create: `http://localhost:8080/api/admin/devices`
- Private emergency profile: `http://localhost:8080/api/devices/{device_id}/emergency-profile`
- Public emergency profile: `http://localhost:8080/api/public/profiles/{public_id}`
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

No hay refresh token, recuperacion de password ni MFA.

## Device Foundation

La API incluye la base de dispositivos:

- Modelo `Device`.
- Tabla `devices`.
- Relacion nullable `devices.user_id -> users.id`.
- `public_id` con formato `PID-XXXXXXXXXX`.
- Alfabeto seguro para `public_id`: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`.

Estados actuales:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints protegidos:

- `GET /api/devices`: requiere Bearer token y solo lista devices del usuario autenticado.
- `POST /api/devices/activate`: requiere Bearer token y activa un device `pending_activation` por `public_id`.
- `POST /api/admin/devices`: requiere Bearer token y `role=admin`; crea un device `pending_activation`.

`public_id` no es secuencial y no expone el UUID interno completo.

## Public Profile Foundation

La API incluye la base de perfiles publicos de emergencia:

- Modelo `EmergencyProfile`.
- Tabla `emergency_profiles`.
- Relacion unica `emergency_profiles.device_id -> devices.id`.

Endpoints protegidos:

- `GET /api/devices/{device_id}/emergency-profile`: requiere Bearer token, valida ownership del device y devuelve el perfil completo del dueno.
- `PUT /api/devices/{device_id}/emergency-profile`: requiere Bearer token, valida ownership del device y crea o actualiza el perfil.

Endpoint publico:

- `GET /api/public/profiles/{public_id}`: no requiere autenticacion y devuelve solo campos publicos del perfil.

Reglas del endpoint publico:

- Busca por `Device.public_id`.
- Solo responde si `device.status == "active"`.
- Solo responde si `emergency_profile.is_public == true`.
- Solo responde si `emergency_profile.deleted_at is null`.
- No expone `id`, `device_id`, `created_at`, `updated_at` ni `deleted_at`.

Limites actuales: no hay generacion de QR, escritura NFC, frontend `/p/{public_id}`, notificaciones, geolocalizacion, historial de escaneos ni subida de archivos medicos. `device_type="qr_nfc_tag"` existe solo como base del modelo, no como implementacion QR/NFC.
