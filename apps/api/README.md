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
- `GET /api/public/devices/{public_id}/activation-status`
- `GET /api/admin/devices/{device_id}/qr`
- `POST /api/admin/devices/{device_id}/qr`
- `GET /api/admin/devices/{device_id}/qr/download`
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

Campos de first-scan activation en `Device`:

- `claim_code_hash`
- `claimed_at`
- `claim_attempts`
- `claim_locked_until`

Estos campos preparan activacion segura por `claim_code` y no se exponen por API.

Estados de device:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints protegidos:

- `GET /api/devices`: requiere Bearer token y solo lista devices del usuario autenticado.
- `POST /api/devices/activate`: requiere Bearer token y body `{ "public_id": "PID-XXXXXXXXXX" }`; activa/asocia un device `pending_activation` por `public_id`, cambia `status` a `active` y setea `user_id` y `activated_at`.
- `POST /api/admin/devices`: requiere Bearer token y `role=admin`; crea un device `pending_activation`.

`POST /api/devices/activate` solo con `public_id` queda considerado inseguro para el flujo comercial real y debe endurecerse para requerir `public_id + claim_code`.

## First Scan Activation Foundation

Flujo de negocio objetivo:

- ProtegID vendera identificadores fisicos con QR impreso y NFC grabado.
- QR/NFC apuntan a `/p/{public_id}`.
- `public_id` es publico.
- `claim_code` es privado y viene dentro del empaque fisico.
- `claim_code` no va en QR/NFC, no va en URL, no debe loguearse y no debe guardarse en texto plano.

Servicio `app.services.claim_codes`:

- `generate_claim_code()` genera `XXXX-XXXX-XXXX` con caracteres no ambiguos y `secrets`.
- `normalize_claim_code()` acepta codigo con o sin guiones.
- `hash_claim_code()` reutiliza `hash_password()`.
- `verify_claim_code()` reutiliza `verify_password()`.
- No loguea `claim_code` ni persiste el codigo plano.

Endpoint publico:

- `GET /api/public/devices/{public_id}/activation-status`: no requiere autenticacion y responde `200` solo si el device existe y `status == "pending_activation"`.

Respuesta `200`:

```json
{
  "public_id": "PID-XXXXXXXXXX",
  "activation_required": true,
  "status": "pending_activation"
}
```

Para `active`, `disabled`, `lost` o inexistente responde `404` generico. No revela owner, `user_id`, `claim_code_hash`, `claimed_at`, `claim_attempts`, `claim_locked_until`, datos medicos ni perfil.

Validacion esperada:

- `python3 -m py_compile apps/api/app/models/device.py apps/api/app/services/claim_codes.py apps/api/app/api/public_devices.py apps/api/app/main.py apps/api/app/schemas/device.py`
- `docker compose exec -T protegid-api alembic upgrade head`
- `GET /api/public/devices/{public_id}/activation-status` con `pending_activation` -> `200`.
- `GET /api/public/devices/{public_id}/activation-status` con `active`, `disabled`, `lost` o inexistente -> `404`.

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
- `GET /api/admin/devices/{device_id}/qr/download`: requiere Bearer token y `role=admin`; descarga el PNG existente.

La metadata incluye `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`.

La descarga busca el device por `device_id`, calcula `qr/devices/{public_id}.png`, lee el objeto QR desde MinIO y no genera QR automaticamente. Si el QR no existe responde `404`. Si existe responde `Content-Type: image/png` y `Content-Disposition: attachment; filename="{public_id}.png"`. No usa presigned URLs y no expone bucket ni credenciales.

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
- Incluye enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.

## Integracion con frontend privado

El frontend privado existe en `/login` y `/dashboard`; Sprint 12 agrega activacion de identificadores desde el dashboard sin cambiar auth backend.

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- Si el login es correcto, recibe `access_token` y `token_type`.
- `/login` guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token`.
- `/login` muestra el token en `textarea` readonly por transparencia temporal del MVP.
- `/login` detecta sesion temporal existente, muestra `Ya existe una sesión temporal activa.`, permite ir a `/dashboard` y permite cerrar sesion temporal.
- Despues de login exitoso, `/login` muestra `Continuar al dashboard` y no redirige automaticamente.
- `/dashboard` lee automaticamente el token desde `sessionStorage` con `getSessionToken()`.
- `/dashboard` valida sesion contra `GET /api/auth/me`.
- Carga dispositivos con `GET /api/devices`.
- Permite activar/asociar un identificador fisico desde la seccion `Activar identificador` usando `POST /api/devices/activate`.
- Permite seleccionar un dispositivo.
- Carga perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Crea o actualiza perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- Consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- Permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr` cuando el usuario tiene `role=admin`.
- Permite descargar QR con `GET /api/admin/devices/{device_id}/qr/download` mediante `downloadDeviceQr(deviceId, accessToken): Promise<Blob>`.
- Muestra estados QR `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`.
- Durante la descarga muestra `Descargando QR...`.
- Si descarga correctamente muestra `QR descargado correctamente.`.
- Si el QR no existe muestra `Genera el QR antes de descargarlo.`.
- Si el usuario no es admin o QR responde `403`, muestra `La gestión de QR requiere rol admin.` y el dashboard sigue mostrando devices/perfil.
- El cliente frontend de activacion es `activateDevice(publicId, accessToken): Promise<Device>` en `apps/web/lib/devices.ts`, usa `buildApiUrl` y maneja `400`, `401` y `404` con errores controlados.
- `Activar identificador` usa input `public_id`, placeholder `PID-XXXXXXXXXX`, boton `Activar identificador`, estado `Activando...` y exito `Identificador activado correctamente.`.
- El `public_id` puede estar impreso o asociado al QR/NFC fisico, no contiene datos medicos y debe verificarse fisicamente antes de activarlo.
- La lista de dispositivos se refresca o actualiza al activar.
- Estados visibles: `pending_activation` -> `Pendiente de activación`, `active` -> `Activo`, `disabled` -> `Deshabilitado`, `lost` -> `Reportado como perdido`.
- El dashboard muestra descripcion operacional por estado.
- El QR apunta a `/p/{public_id}`, solo contiene la URL publica del perfil y no incluye datos medicos embebidos.
- `object_key` se muestra como detalle tecnico.
- La descarga usa `URL.createObjectURL` y luego `URL.revokeObjectURL`.
- La descarga obtiene el PNG desde el backend autenticado; no expone URL publica de MinIO.
- No hay presigned URLs ni preview de imagen QR.
- `is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.
- Si no hay sesion, `/dashboard` muestra estado no autenticado y boton/link `Ir a login`.
- Mantiene fallback tecnico reducido como `Usar token manual` para pegar token manualmente.
- Tiene boton `Cerrar sesion` que limpia `sessionStorage` con `clearSessionToken()`.
- `/login` y `/dashboard` tienen enlace `Volver al inicio`.
- `/dashboard` organiza estado de sesion, dispositivos, editor de perfil y fallback tecnico.
- Los dispositivos muestran `public_id`, status visual y seleccion.
- El editor agrupa Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica.
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

Download device QR as admin:

```bash
curl -OJ http://localhost:8000/api/admin/devices/<device_id>/qr/download \
  -H 'Authorization: Bearer <admin_access_token>'
```

La descarga responde `401` sin token, `403` con usuario no admin, `404` si el device o el QR no existe y `200 image/png` si el QR existe.

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

Get public device activation status:

```bash
curl http://localhost:8000/api/public/devices/PID-ABCDEFGH23/activation-status
```

## Limites actuales

No hay registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR, presigned URL publica, UI first-scan en `/p/{public_id}`, activacion obligatoria con `claim_code`, registro de usuario final desde primer escaneo, provisionamiento masivo con export de `claim_code`, rate limit completo para claim ni auditoria formal de intentos.

Sprint 13 agrega campos de claim a `devices`, servicio `claim_codes` y endpoint publico minimo de estado, pero no modifica todavia `POST /api/devices/activate` ni frontend.
