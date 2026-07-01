# ProtegID API

Backend FastAPI para ProtegID.

## Endpoints actuales

- `GET /api/health`
- `GET /api/ready`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/verify-email`
- `POST /api/auth/resend-verification`
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

## Auth y Sesiones Server-Side

El backend incluye modelo `User`, tabla `users`, hashing de passwords con Argon2 mediante `pwdlib` y sesiones server-side revocables en `auth_sessions`.

Modelo productivo:

- `POST /api/auth/login` autentica credenciales, crea `auth_session`, setea cookie HttpOnly y devuelve `user`; no devuelve `access_token`, `token_type`, token opaco ni `session_token_hash`.
- La cookie de sesion contiene un token opaco. El token raw no se guarda en DB; se persiste solo `session_token_hash`.
- `GET /api/auth/me` usa cookie de sesion.
- `POST /api/auth/logout` revoca la sesion y borra cookies.
- `CurrentUserDep` autentica solo con cookie de sesion.
- Metodos mutantes con cookie de sesion requieren CSRF double-submit: cookie `protegid_csrf` + header `X-CSRF-Token`.

Variables de sesion y CSRF:

- `SESSION_COOKIE_NAME` (`protegid_session` local; recomendado produccion `__Host-protegid_session`).
- `SESSION_COOKIE_SECURE` (`false` solo local HTTP; `true` en produccion HTTPS).
- `SESSION_COOKIE_SAMESITE` (`lax`).
- `SESSION_COOKIE_PATH` (`/`).
- `SESSION_ABSOLUTE_TTL_SECONDS` (`604800`).
- `SESSION_TOKEN_BYTES` (`32`).
- `SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS` (`300`).
- `CSRF_COOKIE_NAME` (`protegid_csrf`).
- `CSRF_HEADER_NAME` (`X-CSRF-Token`).
- `CSRF_TOKEN_BYTES` (`32`).

Las funciones JWT pueden existir como legado tecnico, pero el producto web no recibe ni envia Bearer tokens.

Variables usadas para construir URLs publicas de QR:

- `PUBLIC_APP_URL`
- `PUBLIC_PROFILE_PATH`

`password_hash` no se expone en respuestas. Passwords, tokens de sesion y CSRF tokens no deben loguearse.

Registro publico y verificacion de email:

- `POST /api/auth/register` recibe `{ "email": "usuario@example.com", "password": "Password123!", "full_name": "Nombre Usuario" }`.
- Devuelve `RegisterResponse` con `user` y `verification_required`; no devuelve token y no inicia sesion automaticamente.
- Fuerza `role=user`; no permite registrar admin desde el endpoint publico.
- El email se normaliza con `strip().lower()` en registro y login/autenticacion.
- La busqueda por email es case-insensitive.
- Registro duplicado con casing distinto responde `409`.
- Se captura `IntegrityError` con rollback.
- `password_hash` no se expone y passwords no deben loguearse.
- El registro crea token one-time-use `email_verification`; el raw token no se guarda, solo `token_hash` en `auth_action_tokens`.
- El link de verificacion apunta a `/verify-email?token=...`.
- `POST /api/auth/verify-email` es publico y no requiere CSRF; marca el token como usado y verifica el email.
- `POST /api/auth/resend-verification` requiere sesion, CSRF y rate limiting.
- Login se permite aunque `email_verified_at` sea `null`.

No hay refresh token, recuperacion de password ni MFA.

Acciones criticas requieren email verificado: `POST /api/devices/activate`, `POST /api/admin/devices`, `PUT /api/devices/{device_id}/emergency-profile` y operaciones admin de QR. Usuarios autenticados no verificados pueden iniciar sesion, consultar `/api/auth/me`, listar sus devices y reenviar verificacion.

Ver detalles operativos en `../../docs/auth-email-verification.md`.

## Device Foundation

El backend incluye modelo `Device`, tabla `devices` y relacion nullable `devices.user_id -> users.id`.

`public_id` usa formato `PID-XXXXXXXXXX` con alfabeto sin caracteres confusos: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`. No es secuencial y no expone el UUID interno completo.

Campos de first-scan activation en `Device`:

- `claim_code_hash`
- `claimed_at`
- `claim_attempts`
- `claim_locked_until`

Estos campos soportan activacion segura por `claim_code`. `claim_code`, `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` no se exponen por API.

Estados de device:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints protegidos:

- `GET /api/devices`: requiere cookie de sesion y solo lista devices del usuario autenticado.
- `POST /api/devices/activate`: requiere cookie de sesion, CSRF y body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`; valida `claim_code` contra `claim_code_hash`, activa/asocia un device `pending_activation` sin `user_id`, cambia `status` a `active`, setea `user_id`, `activated_at` y `claimed_at`, resetea `claim_attempts` y limpia `claim_locked_until`.
- `POST /api/admin/devices`: requiere cookie de sesion, CSRF y `role=admin`; crea un device `pending_activation`.

`POST /api/devices/activate` ya no activa solo con `public_id`. El `claim_code` viene dentro del empaque fisico, no va en QR/NFC, no se guarda en texto plano y se verifica contra `claim_code_hash`.

## First Scan Activation Foundation

Flujo de negocio objetivo:

- ProtegID vendera identificadores fisicos con QR impreso y NFC grabado.
- QR/NFC apuntan a `/p/{public_id}`.
- `public_id` es publico.
- `claim_code` es privado y viene dentro del empaque fisico.
- `claim_code` no va en QR/NFC, no va en URL, no debe loguearse y no debe guardarse en texto plano.
- `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` no se exponen por API.
- `claim_code` y `claim_code_hash` no deben loguearse.

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

Endpoint privado de activacion:

```http
POST /api/devices/activate
Cookie: protegid_session=...
X-CSRF-Token: <protegid_csrf>
Content-Type: application/json

{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }
```

Reglas:

- Requiere cookie de sesion y `X-CSRF-Token` coincidente con `protegid_csrf`.
- Requiere `public_id` valido y `claim_code` valido.
- Solo activa un device con `status == "pending_activation"`.
- El device no debe tener `user_id` asignado.
- Debe existir `claim_code_hash`.
- Si todo es valido, `status` pasa a `active`, `user_id` se asigna al usuario autenticado, `activated_at` y `claimed_at` se setean, `claim_attempts` vuelve a `0` y `claim_locked_until` queda `null`.

Errores esperados:

- Sin sesion -> `401`.
- Sin CSRF valido con sesion -> `403`.
- Body sin `claim_code` -> `422`.
- `public_id` invalido por pattern -> `422`.
- `public_id` inexistente -> `404 Identifier not available`.
- Device no disponible, ya activo o asociado -> `404 Identifier not available`.
- `pending_activation` sin `claim_code_hash` -> `400 Identifier cannot be activated`.
- `claim_code` incorrecto -> `400 Invalid activation data`.
- Bloqueo por intentos -> `429 Too many activation attempts. Try again later.`.

Proteccion contra fuerza bruta:

- `MAX_CLAIM_ATTEMPTS = 5`.
- `CLAIM_LOCK_MINUTES = 15`.
- Cada `claim_code` incorrecto incrementa `claim_attempts`.
- Al quinto intento incorrecto se setea `claim_locked_until`.
- Durante bloqueo responde `429`.
- Activacion correcta limpia `claim_attempts` y `claim_locked_until`.

Validacion esperada:

- `python3 -m py_compile apps/api/app/api/devices.py apps/api/app/schemas/device.py`
- `git diff --check`
- `POST /api/devices/activate` sin sesion -> `401`.
- `POST /api/devices/activate` con sesion y sin CSRF -> `403`.
- `POST /api/devices/activate` sin `claim_code` -> `422`.
- `POST /api/devices/activate` con `public_id` invalido -> `422`.
- `POST /api/devices/activate` con `public_id` inexistente -> `404`.
- `POST /api/devices/activate` con device pendiente sin `claim_code_hash` -> `400`.
- `POST /api/devices/activate` con claim incorrecto -> `400` e incrementa `claim_attempts`.
- Quinto intento incorrecto -> `claim_locked_until` seteado.
- Intento durante bloqueo -> `429`.
- Claim correcto en device no bloqueado -> `200` y device `active` con `user_id`, `activated_at` y `claimed_at`.
- Reactivar device ya activo -> `404`.
- Respuestas no exponen `claim_code`, `claim_code_hash`, `claimed_at`, `claim_attempts` ni `claim_locked_until`.
- `docker compose exec -T protegid-api alembic upgrade head`
- `GET /api/public/devices/{public_id}/activation-status` con `pending_activation` -> `200`.
- `GET /api/public/devices/{public_id}/activation-status` con `active`, `disabled`, `lost` o inexistente -> `404`.

## Public Profile Foundation

El backend incluye modelo `EmergencyProfile`, tabla `emergency_profiles` y relacion unica `emergency_profiles.device_id -> devices.id`.

Endpoints privados:

- `GET /api/devices/{device_id}/emergency-profile`: requiere cookie de sesion, valida que el device pertenezca al usuario autenticado y devuelve el perfil completo.
- `PUT /api/devices/{device_id}/emergency-profile`: requiere cookie de sesion y CSRF, valida que el device pertenezca al usuario autenticado y crea o actualiza el perfil.
- `GET /api/devices/{device_id}/emergency-profile/readiness`: requiere cookie de sesion, valida ownership y devuelve readiness sin valores medicos.

Profile readiness Sprint 17:

- Identificador vinculado no significa ProtegID operativo.
- ProtegID queda operativo solo si el perfil cumple datos minimos, consentimiento vigente y `is_public=true`.
- Servicio: `calculate_profile_readiness(device, profile)`.
- Schema: `EmergencyProfileReadinessRead`.
- Nuevos campos: `medical_conditions_none`, `allergies_none`, `medications_none`, `public_consent_accepted_at`, `public_consent_version`.
- `is_public` tiene default `false` para nuevos perfiles.
- `PUBLIC_PROFILE_CONSENT_VERSION` define la version vigente de consentimiento.
- El backend rechaza `is_public=true` si el perfil no cumple readiness con `422 Emergency profile is not ready for publication.`.

Endpoint publico:

- `GET /api/public/profiles/{public_id}`: no requiere autenticacion y devuelve solo campos publicos del perfil.

Reglas del endpoint publico:

- Busca por `Device.public_id`.
- Solo responde si `readiness.is_public_operational == true`.
- Esto exige device `active`, `device.deleted_at is null`, profile existente, `profile.deleted_at is null`, campos minimos completos, consentimiento vigente e `is_public=true`.
- Si no cumple, responde `404` generico.
- No expone `id`, `device_id`, `user_id`, `is_public`, flags `*_none`, consentimiento, `created_at`, `updated_at` ni `deleted_at`.

## QR Foundation

El backend incluye la base de QR:

- Dependencia `qrcode[pil]`.
- Helper `build_public_profile_url(public_id)`.
- Generacion de QR PNG en memoria.
- Persistencia del QR en MinIO/S3 compatible.
- Object key estable: `qr/devices/{public_id}.png`.

El QR no contiene datos medicos. El QR contiene solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

Endpoints admin:

- `GET /api/admin/devices/{device_id}/qr`: requiere cookie de sesion y `role=admin`; devuelve metadata y `exists`.
- `POST /api/admin/devices/{device_id}/qr`: requiere cookie de sesion, CSRF y `role=admin`; genera/sube el QR y devuelve metadata.
- `GET /api/admin/devices/{device_id}/qr/download`: requiere cookie de sesion y `role=admin`; descarga el PNG existente.

La metadata incluye `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`.

La descarga busca el device por `device_id`, calcula `qr/devices/{public_id}.png`, lee el objeto QR desde MinIO y no genera QR automaticamente. Si el QR no existe responde `404`. Si existe responde `Content-Type: image/png` y `Content-Disposition: attachment; filename="{public_id}.png"`. No usa presigned URLs y no expone bucket ni credenciales.

## Integracion con frontend publico

El frontend publico existe en `/p/{public_id}` y soporta onboarding de primer escaneo. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

- La pagina no requiere login.
- Renderiza server-side.
- Consulta `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si no existe perfil publico, consulta `GET /api/public/devices/{public_id}/activation-status` mediante `getPublicDeviceActivationStatus(publicId)` en `apps/web/lib/public-devices.ts`.
- Si `activation-status` responde `pending_activation`, muestra onboarding `Identificador ProtegID no activado`.
- Si `activation-status` responde `404`, mantiene `404` real o mensaje generico usando `notFound()`.
- No expone IDs internos, `device_id`, timestamps ni `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El 404 no revela si el `public_id` existe o no.
- Incluye enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.
- El onboarding indica que el identificador fisico aun no esta vinculado, que el `claim_code` viene dentro del empaque fisico y que el QR/NFC solo contiene la URL publica permanente.
- Muestra `public_id` como referencia tecnica discreta, CTA `Iniciar sesión` hacia `/login?returnTo=/p/{public_id}` y CTA `Crear cuenta` hacia `/register?returnTo=/p/{public_id}`.
- `apps/web/app/p/[publicId]/activation-form.tsx` valida sesion con `/api/auth/me`; sin sesion muestra CTA login y con sesion permite ingresar `claim_code`.
- El formulario llama `activateDeviceWithClaimCode(publicId, claimCode)` usando cookie y CSRF, y en exito muestra `Identificador vinculado correctamente.` con CTA `Completar perfil de emergencia` hacia `/dashboard?publicId={public_id}`.

## Integracion con frontend privado

El frontend privado existe en `/login` y `/dashboard`; Sprint 12 agrega activacion de identificadores desde el dashboard y Sprint 14 cambia el backend para exigir `public_id + claim_code`.

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- `/register` permite crear cuenta con Nombre, Email y Password, consume `POST /api/auth/register`, envia `full_name`, no guarda token, no usa storage y no inicia sesion automaticamente.
- `/register` muestra `Ya existe una cuenta con este correo.` ante `409` y limpia password tras registro exitoso.
- `/register` y `/login` soportan `returnTo` sanitizado: solo rutas internas seguras.
- Tras login exitoso, `/login` redirige automaticamente con `router.replace()` al `returnTo` seguro o `/dashboard`.
- Si el login es correcto, el backend setea cookies y devuelve `user`; no devuelve tokens.
- `/login` no guarda tokens en storage ni muestra tokens.
- `/login` detecta sesion activa contra `/api/auth/me` y redirige automaticamente al destino seguro.
- `/dashboard` valida sesion contra `GET /api/auth/me` usando cookie.
- Carga dispositivos con `GET /api/devices`.
- Permite activar/asociar un identificador fisico desde la seccion `Activar identificador` usando `public_id + claim_code` y `POST /api/devices/activate`.
- Permite seleccionar un dispositivo.
- Carga perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Crea o actualiza perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- Consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- Permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr` cuando el usuario tiene `role=admin`.
- Permite descargar QR con `GET /api/admin/devices/{device_id}/qr/download` mediante `downloadDeviceQr(deviceId): Promise<Blob>`.
- Muestra estados QR `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`.
- Durante la descarga muestra `Descargando QR...`.
- Si descarga correctamente muestra `QR descargado correctamente.`.
- Si el QR no existe muestra `Genera el QR antes de descargarlo.`.
- Para usuarios no-admin, `/dashboard` oculta Gestion QR, estado QR, generar, regenerar, descargar, `object_key` y mensajes de permisos QR.
- Para admin, `/dashboard` mantiene Gestion QR.
- El cliente frontend de activacion es `activateDeviceWithClaimCode(publicId, claimCode): Promise<Device>` en `apps/web/lib/devices.ts`, usa `buildApiUrl`, cookie y CSRF.
- `Activar identificador` usa inputs `public_id` y `claim_code`, placeholders `PID-XXXXXXXXXX` y `XXXX-XXXX-XXXX`, boton `Activar identificador`, estado `Activando...` y exito `Identificador vinculado correctamente.`.
- El dashboard limpia `claim_code` del estado despues del envio y no lo guarda en storage.
- Errores controlados: `400` datos de activacion invalidos, `401` sesion expirada o no autenticada, `404` identificador no disponible, `422` codigo de activacion invalido o incompleto, `429` demasiados intentos.
- El `public_id` puede estar impreso o asociado al QR/NFC fisico, no contiene datos medicos y debe verificarse fisicamente antes de activarlo.
- La lista de dispositivos se refresca o actualiza al activar.
- Estados visibles: `pending_activation` -> `Pendiente de activación`, `active` -> `Activo`, `disabled` -> `Deshabilitado`, `lost` -> `Reportado como perdido`.
- El dashboard muestra descripcion operacional por estado.
- El QR apunta a `/p/{public_id}`, solo contiene la URL publica del perfil y no incluye datos medicos embebidos.
- `object_key` se muestra solo como detalle tecnico administrativo.
- La descarga usa `URL.createObjectURL` y luego `URL.revokeObjectURL`.
- La descarga obtiene el PNG desde el backend autenticado; no expone URL publica de MinIO.
- No hay presigned URLs ni preview de imagen QR.
- `is_public` expresa intencion de publicacion; el backend solo publica si readiness y consentimiento vigente permiten operacion.
- Si no hay sesion, `/dashboard` muestra estado no autenticado y boton/link `Ir a login`.
- No mantiene fallback de token manual.
- Tiene boton `Cerrar sesion` que llama `POST /api/auth/logout` con CSRF.
- `/login` y `/dashboard` tienen enlace `Volver al inicio`.
- `/dashboard` organiza estado de sesion, dispositivos y editor de perfil.
- Los dispositivos muestran `public_id`, status visual y seleccion.
- El editor agrupa Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica.
- La sesion es server-side con cookie HttpOnly y CSRF double-submit; no usa storage ni Bearer desde frontend.

## Ejemplos curl

Register:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"usuario@example.com","password":"Password123!","full_name":"Nombre Usuario"}'
```

La respuesta es `UserRead`, sin token y sin `password_hash`.

Login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"change-me-123"}'
```

Me:

```bash
curl http://localhost:8000/api/auth/me \
  -H 'Cookie: protegid_session=<cookie>'
```

List devices:

```bash
curl http://localhost:8000/api/devices \
  -H 'Cookie: protegid_session=<cookie>'
```

Activate device:

```bash
curl -X POST http://localhost:8000/api/devices/activate \
  -H 'Cookie: protegid_session=<cookie>; protegid_csrf=<csrf>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  -d '{"public_id":"PID-ABCDEFGH23","claim_code":"XXXX-XXXX-XXXX"}'
```

Create pending device as admin:

```bash
curl -X POST http://localhost:8000/api/admin/devices \
  -H 'Cookie: protegid_session=<admin_cookie>; protegid_csrf=<csrf>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  -d '{"label":"Test device"}'
```

Get device QR metadata as admin:

```bash
curl http://localhost:8000/api/admin/devices/<device_id>/qr \
  -H 'Cookie: protegid_session=<admin_cookie>'
```

Generate device QR as admin:

```bash
curl -X POST http://localhost:8000/api/admin/devices/<device_id>/qr \
  -H 'Cookie: protegid_session=<admin_cookie>; protegid_csrf=<csrf>' \
  -H 'X-CSRF-Token: <csrf>'
```

Download device QR as admin:

```bash
curl -OJ http://localhost:8000/api/admin/devices/<device_id>/qr/download \
  -H 'Cookie: protegid_session=<admin_cookie>'
```

La descarga responde `401` sin sesion, `403` con usuario no admin, `404` si el device o el QR no existe y `200 image/png` si el QR existe.

Get private emergency profile:

```bash
curl http://localhost:8000/api/devices/<device_id>/emergency-profile \
  -H 'Cookie: protegid_session=<cookie>'
```

Create or update private emergency profile:

```bash
curl -X PUT http://localhost:8000/api/devices/<device_id>/emergency-profile \
  -H 'Cookie: protegid_session=<cookie>; protegid_csrf=<csrf>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"Example User","emergency_contact_name":"Contact","emergency_contact_phone":"+56912345678","emergency_contact_relationship":"Family","medical_conditions_none":true,"allergies_none":true,"medications_none":true,"public_consent_accepted_at":"2026-05-24T12:00:00Z","public_consent_version":"2026-05-v1","is_public":true}'
```

Get private emergency profile readiness:

```bash
curl http://localhost:8000/api/devices/<device_id>/emergency-profile/readiness \
  -H 'Cookie: protegid_session=<cookie>'
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

No hay validacion estricta de telefono internacional, wizard profesional multi-vista de onboarding de perfil, email verification, recuperacion de password, refresh token, MFA, captcha, proteccion anti-bot, roles avanzados en frontend, expiracion visual previa de la sesion, auditoria formal de eventos criticos, historial/versionado completo de consentimientos, segundo contacto de emergencia, normalizacion avanzada de datos medicos, hardening de rate limiting publico, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC real desde navegador, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR, presigned URL publica ni provisionamiento masivo con export de `claim_code`. Registro no inicia sesion automaticamente y roles siguen siendo strings.

Sprint 13 agrega campos de claim a `devices`, servicio `claim_codes` y endpoint publico minimo de estado. Sprint 14 actualiza `POST /api/devices/activate` para requerir `public_id + claim_code` y bloqueo temporal por intentos fallidos. Sprint 15 agrega onboarding publico y actualiza dashboard para enviar `claim_code`. Sprint 16 agrega registro de usuario final, hardening de email, `returnTo` seguro, integracion onboarding -> registro/login y UX post-vinculacion hacia perfil. Sprint 17 agrega readiness productivo, consentimiento explicito, bloqueo de publicacion incompleta, endpoint privado de readiness, endpoint publico endurecido y progreso en dashboard. Sprint 18 migra auth a sesiones server-side con cookie HttpOnly y CSRF double-submit.
