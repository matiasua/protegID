# ProtegID API

Backend FastAPI para ProtegID.

## Endpoints actuales

- `GET /api/health`
- `GET /api/ready`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/devices`
- `POST /api/devices/activate`
- `POST /api/admin/devices`
- `GET /api/devices/{device_id}/emergency-profile`
- `PUT /api/devices/{device_id}/emergency-profile`
- `GET /api/public/profiles/{public_id}`

## Auth Foundation

El backend incluye modelo `User`, tabla `users`, hashing de passwords con Argon2 mediante `pwdlib` y JWT access token.

Variables requeridas para JWT:

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

`password_hash` no se expone en respuestas. Passwords y tokens no deben loguearse.

No hay refresh token, recuperacion de password ni MFA.

## Device Foundation

El backend incluye modelo `Device`, tabla `devices` y relacion nullable `devices.user_id -> users.id`.

`public_id` usa formato `PID-XXXXXXXXXX` con alfabeto sin caracteres confusos: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`. No es secuencial y no expone el UUID interno completo.

Estados de device:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints protegidos:

- `GET /api/devices`: requiere Bearer token y solo lista devices del usuario autenticado.
- `POST /api/devices/activate`: requiere Bearer token y activa un device `pending_activation` por `public_id`.
- `POST /api/admin/devices`: requiere Bearer token y `role=admin`; crea un device `pending_activation`.

## Public Profile Foundation

El backend incluye modelo `EmergencyProfile`, tabla `emergency_profiles` y relacion unica `emergency_profiles.device_id -> devices.id`.

Endpoints privados:

- `GET /api/devices/{device_id}/emergency-profile`: requiere Bearer token, valida que el device pertenezca al usuario autenticado y devuelve el perfil completo.
- `PUT /api/devices/{device_id}/emergency-profile`: requiere Bearer token, valida que el device pertenezca al usuario autenticado y crea o actualiza el perfil.

Endpoint publico:

- `GET /api/public/profiles/{public_id}`: no requiere autenticacion y devuelve solo campos publicos del perfil.

Reglas del endpoint publico:

- Busca por `Device.public_id`.
- Solo responde si `device.status == "active"`.
- Solo responde si `emergency_profile.is_public == true`.
- Solo responde si `emergency_profile.deleted_at is null`.
- No expone `id`, `device_id`, `created_at`, `updated_at` ni `deleted_at`.

Limites actuales: no hay generacion de QR, escritura NFC, frontend `/p/{public_id}`, notificaciones, geolocalizacion, historial de escaneos ni subida de archivos medicos. `device_type="qr_nfc_tag"` existe solo como base del modelo, no como implementacion QR/NFC.

## Ejemplos curl

Register:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"change-me-123","full_name":"Example User"}'
```

Login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"change-me-123"}'
```

Me:

```bash
curl http://localhost:8000/api/auth/me \
  -H 'Authorization: Bearer <access_token>'
```

List devices:

```bash
curl http://localhost:8000/api/devices \
  -H 'Authorization: Bearer <access_token>'
```

Activate device:

```bash
curl -X POST http://localhost:8000/api/devices/activate \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"public_id":"PID-ABCDEFGH23"}'
```

Create pending device as admin:

```bash
curl -X POST http://localhost:8000/api/admin/devices \
  -H 'Authorization: Bearer <admin_access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"label":"Test device"}'
```

Get private emergency profile:

```bash
curl http://localhost:8000/api/devices/<device_id>/emergency-profile \
  -H 'Authorization: Bearer <access_token>'
```

Create or update private emergency profile:

```bash
curl -X PUT http://localhost:8000/api/devices/<device_id>/emergency-profile \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"Example User","blood_type":"O+","is_public":true}'
```

Get public emergency profile:

```bash
curl http://localhost:8000/api/public/profiles/PID-ABCDEFGH23
```

## Limites actuales

No hay generacion de QR, escritura NFC, frontend `/p/{public_id}`, notificaciones, geolocalizacion, historial de escaneos ni subida de archivos medicos.
