# Reglas Para Futuras Tareas Con IA

- No cambiar el stack definido.
- No crear microservicios.
- No implementar logica de negocio sin solicitud explicita.
- No guardar datos medicos en QR.
- No usar IDs publicos secuenciales.
- No exponer IDs internos.
- No hardcodear secretos.
- No loguear datos medicos o sensibles.
- No loguear passwords ni tokens.
- Toda futura tabla debe tener migracion.
- Todo futuro endpoint debe usar schemas/validaciones.
- No modificar Auth Foundation sin justificacion explicita de producto o seguridad.

## Stack definido

- Frontend: Next.js + TypeScript + Tailwind CSS + shadcn/ui.
- Backend: FastAPI + Python.
- DB: PostgreSQL.
- Queue/cache: Redis.
- Worker: Python.
- Archivos: MinIO compatible S3.
- Reverse proxy: Nginx.
- Entorno local: Docker Compose.

## Restricciones de esta etapa

Auth Foundation ya existe e incluye modelo `User`, tabla `users`, hashing de passwords, JWT access token y endpoints `register`, `login` y `me`.

Device Foundation ya existe e incluye modelo `Device`, tabla `devices`, relacion nullable `devices.user_id -> users.id`, generacion de `public_id` con formato `PID-XXXXXXXXXX` y endpoints protegidos basicos de devices.

Public Profile Foundation ya existe e incluye modelo `EmergencyProfile`, tabla `emergency_profiles`, relacion unica `emergency_profiles.device_id -> devices.id`, endpoints privados para ver/crear/editar el perfil de un device y endpoint publico de lectura por `public_id`.

QR Foundation ya existe e incluye configuracion `PUBLIC_APP_URL` y `PUBLIC_PROFILE_PATH`, helper `build_public_profile_url(public_id)`, generacion de QR PNG en memoria con `qrcode[pil]`, persistencia en MinIO/S3 compatible y object key estable `qr/devices/{public_id}.png`.

El QR no debe contener datos medicos. El QR debe contener solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

Estados de device existentes:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints de devices existentes:

- `GET /api/devices`
- `POST /api/devices/activate`
- `POST /api/admin/devices`

Endpoints de perfiles de emergencia existentes:

- `GET /api/devices/{device_id}/emergency-profile`
- `PUT /api/devices/{device_id}/emergency-profile`
- `GET /api/public/profiles/{public_id}`

Endpoints admin de QR existentes:

- `GET /api/admin/devices/{device_id}/qr`
- `POST /api/admin/devices/{device_id}/qr`

El endpoint publico no requiere autenticacion, busca por `Device.public_id`, solo responde si el device esta `active`, el perfil tiene `is_public == true` y `deleted_at is null`, y no expone `id`, `device_id`, `created_at`, `updated_at` ni `deleted_at`.

Los endpoints QR requieren Bearer token y `role=admin`. No devuelven el archivo PNG ni entregan presigned URL. Solo devuelven metadata: `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`.

No implementar NFC, frontend publico `/p/{public_id}`, descarga directa de QR, presigned URLs, tracking de escaneos, notificaciones, geolocalizacion, subida de archivos medicos, refresh token, recuperacion de password ni MFA salvo solicitud explicita.

No crear nuevas tablas ni migraciones salvo solicitud explicita.

`device_type="qr_nfc_tag"` existe como base del modelo. QR Foundation ya existe; NFC todavia no esta implementado.
