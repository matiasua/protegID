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

Limites actuales: no hay generacion de QR, escritura NFC, vista publica `/p/{public_id}`, perfil medico, contactos de emergencia, notificaciones ni logica de escaneo. `device_type="qr_nfc_tag"` existe solo como base del modelo, no como implementacion QR/NFC.

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

## Limites actuales

No hay generacion de QR, escritura NFC, vista publica `/p/{public_id}`, perfil medico, contactos de emergencia, notificaciones ni logica de escaneo.
