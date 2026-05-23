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
- `GET /api/admin/devices/{device_id}/qr`
- `POST /api/admin/devices/{device_id}/qr`
- `GET /api/devices/{device_id}/emergency-profile`
- `PUT /api/devices/{device_id}/emergency-profile`
- `GET /api/public/profiles/{public_id}`

## Auth Foundation

El backend incluye modelo `User`, tabla `users`, hashing de passwords con Argon2 mediante `pwdlib` y JWT access token.

Variables requeridas para JWT:

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Variables usadas para construir URLs publicas de QR:

- `PUBLIC_APP_URL`
- `PUBLIC_PROFILE_PATH`

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

## QR Foundation

El backend incluye la base de QR:

- Dependencia `qrcode[pil]`.
- Helper `build_public_profile_url(public_id)`.
- Generacion de QR PNG en memoria.
- Persistencia del QR en MinIO/S3 compatible.
- Object key estable: `qr/devices/{public_id}.png`.

El QR no contiene datos medicos. El QR contiene solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

Endpoints admin:

- `GET /api/admin/devices/{device_id}/qr`: requiere Bearer token y `role=admin`; devuelve metadata y `exists`.
- `POST /api/admin/devices/{device_id}/qr`: requiere Bearer token y `role=admin`; genera/sube el QR y devuelve metadata.

La metadata incluye `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`. No se devuelve el archivo PNG ni se entrega presigned URL.

## Integracion con frontend publico

El frontend publico existe en `/p/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

- La pagina no requiere login.
- Renderiza server-side.
- Consulta `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si no existe o no esta disponible, responde `404` real usando `notFound()`.
- No expone IDs internos, `device_id`, timestamps ni `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El 404 no revela si el `public_id` existe o no.

## Integracion con frontend privado

El frontend privado inicial existe en `/login` y `/dashboard`.

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- Si el login es correcto, recibe `access_token` y `token_type`.
- `/login` guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token`.
- `/login` muestra el token en `textarea` readonly por transparencia temporal del MVP.
- `/dashboard` lee automaticamente el token desde `sessionStorage` con `getSessionToken()`.
- `/dashboard` valida sesion contra `GET /api/auth/me`.
- Carga dispositivos con `GET /api/devices`.
- Permite seleccionar un dispositivo.
- Carga perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Crea o actualiza perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- `is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.
- Si no hay sesion, `/dashboard` muestra estado no autenticado y boton/link `Ir a login`.
- Mantiene fallback tecnico para pegar token manualmente.
- Tiene boton `Cerrar sesion` que limpia `sessionStorage` con `clearSessionToken()`.
- La sesion es temporal para MVP: usa `sessionStorage`, no `localStorage`, no cookies, no refresh token y no middleware de proteccion.

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

Get device QR metadata as admin:

```bash
curl http://localhost:8000/api/admin/devices/<device_id>/qr \
  -H 'Authorization: Bearer <admin_access_token>'
```

Generate device QR as admin:

```bash
curl -X POST http://localhost:8000/api/admin/devices/<device_id>/qr \
  -H 'Authorization: Bearer <admin_access_token>'
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

No hay registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, subida de archivos medicos, gestion de QR desde frontend, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, descarga publica de QR ni presigned URL publica.

Sprint 8 no agrega nuevas tablas ni nuevas migraciones.
