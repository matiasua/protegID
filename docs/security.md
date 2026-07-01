# Seguridad

## Estado Actual Sprint 19: Verificacion de Email y Proteccion de Abuso

ProtegID incluye verificacion de email con tokens one-time-use y rate limiting Redis para el lanzamiento controlado.

Registro y verificacion:

- `POST /api/auth/register` crea usuarios con `email_verified_at=null`, devuelve `RegisterResponse` y no inicia sesion automaticamente.
- El backend genera tokens de accion con proposito `email_verification`.
- El token raw no se guarda en DB; `auth_action_tokens` guarda `token_hash`.
- El link de verificacion apunta a `/verify-email?token=...`.
- `POST /api/auth/verify-email` es publico y no requiere CSRF.
- Al verificar, el token queda marcado con `used_at` y se revocan tokens pendientes cuando corresponde.
- Login se permite aunque `email_verified_at` sea `null`.

Usuarios autenticados no verificados pueden iniciar sesion, consultar `/api/auth/me`, ver dashboard basico, listar devices propios y reenviar verificacion. No pueden activar identificadores, editar/publicar perfiles, crear devices admin ni operar endpoints admin de QR.

Rate limiting:

- Redis es dependencia critica para rate limiting; si Redis falla, endpoints criticos responden `503 Rate limit service unavailable.`.
- Endpoints cubiertos: `POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/resend-verification`, `POST /api/auth/verify-email`, `POST /api/devices/activate`, `GET /api/public/devices/{public_id}/activation-status` y `GET /api/public/profiles/{public_id}`.
- Las keys no guardan email plano; el email se normaliza y se hashea con SHA-256.
- Redis no guarda tokens raw ni `claim_code`.
- La respuesta `429` es generica.

Ver detalle operativo en `docs/auth-email-verification.md`.

## Estado Actual Sprint 18: Sesiones Productivas

ProtegID usa sesiones server-side con cookie HttpOnly para el producto web.

- `POST /api/auth/login` autentica email/password, crea una fila en `auth_sessions`, setea cookies y devuelve `user`; no devuelve `access_token`, `token_type`, token opaco ni `session_token_hash`.
- La cookie de sesion local se llama `protegid_session`, es `HttpOnly`, `SameSite=Lax`, `Path=/` y usa `Secure=false` solo en HTTP local.
- En produccion se recomienda `SESSION_COOKIE_NAME=__Host-protegid_session`, `SESSION_COOKIE_SECURE=true`, `SESSION_COOKIE_SAMESITE=lax`, `SESSION_COOKIE_PATH=/` y no definir `Domain`.
- El token raw de sesion solo viaja en cookie HttpOnly. La base de datos guarda `session_token_hash`; no guarda el token raw.
- `CurrentUserDep` autentica exclusivamente con cookie de sesion. No acepta `Authorization Bearer` ni query params.
- `POST /api/auth/logout` requiere CSRF cuando hay sesion, revoca la sesion y borra `protegid_session` y `protegid_csrf`.
- El frontend no usa `sessionStorage` ni `localStorage` para auth, no muestra tokens y no envia `Authorization Bearer`.

CSRF usa double-submit:

- Cookie `protegid_csrf`: no HttpOnly, `SameSite=Lax`, `Path=/`, `Secure=true` en produccion, sin `Domain`.
- Header requerido: `X-CSRF-Token`.
- Aplica a `POST`, `PUT`, `PATCH` y `DELETE` si existe cookie de sesion.
- No aplica a `GET`, `HEAD`, `OPTIONS`, `POST /api/auth/login` ni `POST /api/auth/verify-email`.
- `POST /api/auth/verify-email` queda excluido porque usa token one-time-use opaco, hasheado en DB, con expiracion, `used_at`, `revoked_at` y proposito `email_verification`.
- `POST /api/auth/resend-verification` y `POST /api/auth/logout` siguen requiriendo CSRF cuando hay sesion.
- Requests privados sin sesion deben responder `401`; requests con sesion y CSRF faltante/incorrecto responden `403 CSRF validation failed`.

Variables de entorno actuales:

- `SESSION_COOKIE_NAME` (`protegid_session` local, `__Host-protegid_session` recomendado en produccion).
- `SESSION_COOKIE_SECURE` (`false` local HTTP, `true` produccion HTTPS).
- `SESSION_COOKIE_SAMESITE` (`lax`).
- `SESSION_COOKIE_PATH` (`/`).
- `SESSION_ABSOLUTE_TTL_SECONDS` (`604800`).
- `SESSION_TOKEN_BYTES` (`32`).
- `SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS` (`300`).
- `CSRF_COOKIE_NAME` (`protegid_csrf`).
- `CSRF_HEADER_NAME` (`X-CSRF-Token`).
- `CSRF_TOKEN_BYTES` (`32`).
- `EMAIL_VERIFICATION_TOKEN_TTL_SECONDS` (`86400`).
- `ACTION_TOKEN_BYTES` (`32`).
- `EMAIL_DELIVERY_MODE` (`smtp` local con Mailpit, `console` permitido solo local/dev/test).
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`.

Validaciones realizadas:

- Login valido setea `protegid_session` y `protegid_csrf`.
- Login no devuelve `access_token` ni `token_type`.
- `/api/auth/me` y `/api/devices` funcionan con cookie.
- Logout revoca sesion y limpia ambas cookies.
- `POST`/`PUT` sin CSRF con sesion retorna `403`; con CSRF correcto funciona.
- Request privado sin sesion retorna `401`.
- Bearer antiguo sin cookie retorna `401`.

Pendientes de hardening posteriores: recuperacion de password, auditoria formal de eventos de sesion, gestion de sesiones activas por usuario, rotacion/renovacion controlada de sesion, headers HTTP en Nginx, CSP y revision CORS productiva.

## Reglas iniciales

- No guardar datos medicos en QR.
- No subir secretos al repositorio.
- No hardcodear credenciales.
- No loguear datos medicos o sensibles.
- No usar IDs secuenciales como identificadores publicos.
- No exponer IDs internos en URLs publicas.
- Mantener configuracion sensible mediante variables de entorno.
- No incluir `claim_code` en QR/NFC, URLs, logs ni respuestas API.
- No guardar `claim_code` en texto plano; guardar solo `claim_code_hash`.
- No exponer token raw de verificacion ni guardarlo en DB.
- No incluir emails planos en Redis keys.
- No publicar perfiles incompletos ni sin consentimiento vigente.
- No inferir consentimiento desde `is_public`.
- No exponer campos internos de readiness, consentimiento ni ids internos en respuestas publicas.

## Variables de entorno

`.env.example` contiene valores de ejemplo para desarrollo local. Cada entorno debe definir sus propios valores reales fuera del control de versiones.

Variables JWT usadas por la API:

- `JWT_SECRET_KEY`: secreto para firmar access tokens. Debe ser unico por entorno y no debe hardcodearse.
- `JWT_ALGORITHM`: algoritmo de firma. Valor local por defecto: `HS256`.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: expiracion del access token en minutos. Valor local por defecto: `30`.

Variables publicas usadas para QR:

- `PUBLIC_APP_URL`: origen publico de la aplicacion. Valor local por defecto: `http://localhost:8080`.
- `PUBLIC_PROFILE_PATH`: path publico de perfil. Valor local por defecto: `/p`.

Estas variables no son secretos. Se usan para construir la URL publica codificada en el QR mediante `build_public_profile_url(public_id)`.

Variable de consentimiento publico:

- `PUBLIC_PROFILE_CONSENT_VERSION`: version vigente del consentimiento de publicacion. Valor local por defecto: `2026-05-v1`.

Si la version aceptada por el perfil no coincide con esta variable, el perfil no queda operativo publicamente.

Variables de verificacion de email:

- `EMAIL_VERIFICATION_TOKEN_TTL_SECONDS`: TTL del token one-time-use de verificacion.
- `ACTION_TOKEN_BYTES`: entropia usada para generar tokens de accion.
- `EMAIL_DELIVERY_MODE`: `smtp` para Mailpit/local SMTP o `console` solo en entornos local/dev/test.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`: transporte SMTP.

Variables de rate limiting:

- `RATE_LIMIT_LOGIN_IP_LIMIT`, `RATE_LIMIT_LOGIN_IP_WINDOW_SECONDS`, `RATE_LIMIT_LOGIN_EMAIL_LIMIT`, `RATE_LIMIT_LOGIN_EMAIL_WINDOW_SECONDS`.
- `RATE_LIMIT_REGISTER_IP_LIMIT`, `RATE_LIMIT_REGISTER_IP_WINDOW_SECONDS`, `RATE_LIMIT_REGISTER_EMAIL_LIMIT`, `RATE_LIMIT_REGISTER_EMAIL_WINDOW_SECONDS`.
- `RATE_LIMIT_RESEND_VERIFICATION_IP_LIMIT`, `RATE_LIMIT_RESEND_VERIFICATION_IP_WINDOW_SECONDS`, `RATE_LIMIT_RESEND_VERIFICATION_USER_LIMIT`, `RATE_LIMIT_RESEND_VERIFICATION_USER_WINDOW_SECONDS`.
- `RATE_LIMIT_VERIFY_EMAIL_IP_LIMIT`, `RATE_LIMIT_VERIFY_EMAIL_IP_WINDOW_SECONDS`.
- `RATE_LIMIT_DEVICE_ACTIVATE_IP_LIMIT`, `RATE_LIMIT_DEVICE_ACTIVATE_IP_WINDOW_SECONDS`, `RATE_LIMIT_DEVICE_ACTIVATE_PUBLIC_ID_LIMIT`, `RATE_LIMIT_DEVICE_ACTIVATE_PUBLIC_ID_WINDOW_SECONDS`.
- `RATE_LIMIT_PUBLIC_LOOKUP_IP_LIMIT`, `RATE_LIMIT_PUBLIC_LOOKUP_IP_WINDOW_SECONDS`, `RATE_LIMIT_PUBLIC_LOOKUP_PUBLIC_ID_LIMIT`, `RATE_LIMIT_PUBLIC_LOOKUP_PUBLIC_ID_WINDOW_SECONDS`.

## Autenticacion

Auth actual combina Auth Foundation con sesiones server-side de Sprint 18:

- Password hashing con Argon2 mediante `pwdlib`.
- Sesiones server-side revocables en `auth_sessions`.
- Cookie HttpOnly de sesion y cookie CSRF double-submit.
- `POST /api/auth/register` crea usuarios.
- `POST /api/auth/login` setea cookies y devuelve `user`; no devuelve tokens.
- `POST /api/auth/verify-email` verifica email con token one-time-use publico sin CSRF.
- `POST /api/auth/resend-verification` reenvia email y requiere sesion + CSRF.
- `GET /api/auth/me` requiere cookie de sesion y devuelve el usuario actual.

`password_hash` nunca debe exponerse en respuestas. Passwords y tokens no deben loguearse.

Registro publico de usuario final en Sprint 16:

- `POST /api/auth/register` recibe `{ "email": "usuario@example.com", "password": "Password123!", "full_name": "Nombre Usuario" }`.
- Devuelve `UserRead`, no devuelve token y no inicia sesion automaticamente.
- El rol se fuerza a `user`; el schema publico de creacion no acepta `role` ni `status`.
- No se permite registrar `admin` desde el endpoint publico.
- El email se normaliza con `strip().lower()` al registrar y al autenticar.
- La busqueda por email es case-insensitive.
- Duplicados con casing distinto responden `409`.
- Se captura `IntegrityError` con rollback para no exponer stacktrace ante carreras del unique email.

## Device Foundation

Sprint 3 implementa la base de dispositivos:

- Modelo `Device`.
- Tabla `devices`.
- Relacion nullable `devices.user_id -> users.id`.
- `public_id` unico con formato `PID-XXXXXXXXXX`.
- Alfabeto de `public_id` sin caracteres confusos: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`.

Estados de device:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Controles de seguridad actuales:

- `GET /api/devices` requiere cookie de sesion.
- `GET /api/devices` solo lista devices del usuario autenticado.
- `POST /api/devices/activate` requiere cookie de sesion, CSRF y body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`.
- `POST /api/devices/activate` valida `claim_code` contra `claim_code_hash`, activa/asocia un device `pending_activation` sin `user_id`, cambia `status` a `active`, setea `user_id`, `activated_at` y `claimed_at`, resetea `claim_attempts` y limpia `claim_locked_until`.
- `POST /api/admin/devices` requiere `role=admin`.
- `public_id` no es secuencial.
- `public_id` no usa el UUID interno completo como identificador publico visible.
- `public_id` no contiene datos medicos.
- El usuario debe verificar fisicamente el identificador antes de activarlo.
- `claim_code`, `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` no se exponen por API.
- `claim_code` y `claim_code_hash` no deben loguearse.
- El backend sigue siendo la fuente de autorizacion.

## First Scan Activation Foundation

Sprint 13 prepara el flujo seguro para primer escaneo de identificadores fisicos:

- ProtegID vendera identificadores con QR impreso y NFC grabado.
- QR/NFC apuntan a `/p/{public_id}`.
- `public_id` es publico y no debe ser secuencial.
- `claim_code` es privado y viene dentro del empaque fisico.
- `claim_code` no va en QR/NFC.
- `claim_code` no debe ir en URL, logs ni respuestas API.
- `claim_code` no debe guardarse en texto plano.
- `claim_code_hash` no debe exponerse.
- `claim_attempts` y `claim_locked_until` no deben exponerse.

Servicio `claim_codes`:

- `generate_claim_code()` usa `secrets` y formato `XXXX-XXXX-XXXX`.
- El alfabeto evita caracteres ambiguos.
- `normalize_claim_code()` acepta codigo con o sin guiones.
- `hash_claim_code()` reutiliza `hash_password()`.
- `verify_claim_code()` reutiliza `verify_password()`.
- El servicio no loguea `claim_code` ni persiste el codigo plano.

Endpoint publico de estado:

- `GET /api/public/devices/{public_id}/activation-status` no requiere autenticacion.
- Responde `200` solo si el device existe y `status == "pending_activation"`.
- Respuesta minima: `{ "public_id": "PID-XXXXXXXXXX", "activation_required": true, "status": "pending_activation" }`.
- Para `active`, `disabled`, `lost` o inexistente responde `404` generico.
- No revela owner, `user_id`, `claim_code_hash`, `claimed_at`, `claim_attempts`, `claim_locked_until`, datos medicos ni perfil.

Reglas de activacion privada:

- Requiere cookie de sesion y CSRF.
- Requiere `public_id` valido y `claim_code` valido.
- Solo permite activar devices `pending_activation`.
- El device no debe tener `user_id` asignado.
- Debe existir `claim_code_hash`.
- Si todo es valido, el device pasa a `active`, se asigna `user_id`, se setean `activated_at` y `claimed_at`, `claim_attempts` vuelve a `0` y `claim_locked_until` queda `null`.

Errores esperados:

- Sin sesion -> `401`.
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

Limites de seguridad actuales:

- Existe registro de usuario final desde primer escaneo mediante `/register?returnTo=/p/{public_id}`.
- El registro no inicia sesion automaticamente; el usuario debe iniciar sesion antes de reclamar.
- `/login?returnTo=/p/{public_id}` permite volver al identificador despues de autenticar y recibir cookies.
- `returnTo` se sanitiza: solo rutas internas seguras; se rechazan URLs externas y rutas internas peligrosas.
- La sesion usa cookie HttpOnly y CSRF double-submit.
- Aun no existe provisionamiento masivo con export de `claim_code`.
- Aun no hay auditoria formal de intentos.

## Public Profile Foundation

Sprint 4 implementa la base de perfiles publicos de emergencia:

- Modelo `EmergencyProfile`.
- Tabla `emergency_profiles`.
- Relacion unica y obligatoria `emergency_profiles.device_id -> devices.id`.
- Endpoints privados `GET /api/devices/{device_id}/emergency-profile` y `PUT /api/devices/{device_id}/emergency-profile`.
- Endpoint publico `GET /api/public/profiles/{public_id}`.

Controles de seguridad y privacidad:

- Los endpoints privados requieren cookie de sesion.
- Los endpoints privados validan ownership mediante `current_user.id` y `device.user_id`.
- El endpoint publico no requiere autenticacion.
- El endpoint publico busca por `Device.public_id`.
- El endpoint publico solo responde si `readiness.is_public_operational == true`.
- Esto exige `device.status == "active"`, `device.deleted_at is null`, profile existente, `profile.deleted_at is null`, campos minimos completos, consentimiento vigente e `is_public == true`.
- El endpoint publico responde `404` generico si el `public_id` no existe, el device no esta activo, el device/profile esta eliminado, el profile no existe, esta incompleto, falta consentimiento vigente o `is_public=false`.
- La respuesta publica no expone `id` interno.
- La respuesta publica no expone `device_id`.
- La respuesta publica no expone `user_id`.
- La respuesta publica no expone `is_public`.
- La respuesta publica no expone flags `*_none`.
- La respuesta publica no expone `public_consent_accepted_at` ni `public_consent_version`.
- La respuesta publica no expone `created_at`, `updated_at` ni `deleted_at`.
- Los datos medicos no deben loguearse.

Readiness y consentimiento:

- Identificador vinculado no significa ProtegID operativo.
- `calculate_profile_readiness(device, profile)` es la fuente backend para determinar readiness.
- `GET /api/devices/{device_id}/emergency-profile/readiness` requiere cookie de sesion, verifica ownership y no expone valores medicos.
- Campos minimos: `display_name`, contacto de emergencia completo, decision explicita para condiciones medicas/alergias/medicamentos, consentimiento aceptado, version vigente e `is_public=true`.
- El consentimiento es explicito, versionado con `PUBLIC_PROFILE_CONSENT_VERSION` y no se infiere desde `is_public`.
- `is_public` tiene default `false` para nuevos perfiles.
- El backend bloquea `is_public=true` si el perfil no cumple readiness con `422 Emergency profile is not ready for publication.`.
- El frontend solo guia la experiencia; el backend decide autorizacion y publicacion.

## QR Foundation

Sprint 5 implementa la base de QR:

- Dependencia `qrcode[pil]`.
- Generacion de QR PNG en memoria.
- Persistencia del QR en MinIO/S3 compatible.
- Object key estable: `qr/devices/{public_id}.png`.
- Endpoints admin `GET /api/admin/devices/{device_id}/qr`, `POST /api/admin/devices/{device_id}/qr` y `GET /api/admin/devices/{device_id}/qr/download`.

Reglas de seguridad y privacidad:

- El QR no contiene datos medicos.
- El QR contiene solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`.
- Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.
- Los endpoints QR requieren cookie de sesion.
- Los endpoints QR requieren `role=admin`; usuario no admin recibe `403`.
- Sin sesion, los endpoints QR responden `401`.
- `GET /api/admin/devices/{device_id}/qr` devuelve metadata: `device_id`, `public_id`, `object_key`, `content_type` y `exists`.
- `POST /api/admin/devices/{device_id}/qr` genera/sube el QR.
- `GET /api/admin/devices/{device_id}/qr/download` busca el device por `device_id`, lee `qr/devices/{public_id}.png` desde MinIO y no genera QR automaticamente.
- Si el QR no existe, la descarga responde `404`.
- Si el QR existe, la descarga responde `Content-Type: image/png` y `Content-Disposition: attachment; filename="{public_id}.png"`.
- No se entrega presigned URL.
- No se expone bucket, credenciales ni URL publica de MinIO.
- El backend sigue siendo la fuente de autorizacion para gestion QR.

## Public Profile Frontend

Sprint 6 implementa la ruta publica frontend `/p/{public_id}` y Sprint 15 agrega onboarding de primer escaneo. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

Reglas de seguridad y privacidad:

- La pagina publica no requiere login.
- La pagina consulta server-side `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si no existe perfil publico, consulta `GET /api/public/devices/{public_id}/activation-status`.
- Si `activation-status` responde `pending_activation`, muestra onboarding publico `Identificador ProtegID no activado`.
- Si `activation-status` responde `404`, mantiene `404` real o mensaje generico usando `notFound()`.
- No expone IDs internos.
- No expone `device_id`.
- No expone timestamps.
- No expone `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El 404 no debe revelar si el `public_id` existe o no.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.
- `/p/{public_id}` solo agrega un enlace discreto `ProtegID` hacia `/`; no expone datos internos.
- Los datos medicos no deben loguearse.

Reglas del onboarding de primer escaneo:

- `apps/web/lib/public-devices.ts` expone `getPublicDeviceActivationStatus(publicId)`.
- El cliente publico retorna estado de activacion en `200`, retorna `null` en `404`, no usa token, no envia `Authorization` y no maneja `claim_code`.
- El onboarding indica que el identificador fisico aun no esta vinculado, que el `claim_code` viene dentro del empaque fisico y que el QR/NFC solo contiene la URL publica permanente.
- Muestra `public_id` como referencia tecnica discreta.
- `apps/web/app/p/[publicId]/activation-form.tsx` valida sesion con `/api/auth/me`.
- Sin sesion, muestra CTA `Iniciar sesión`.
- Con sesion, permite ingresar `claim_code` y llama `activateDeviceWithClaimCode(publicId, claimCode)` usando cookie y CSRF.
- En exito muestra `Identificador vinculado correctamente.` y CTA `Completar perfil de emergencia` hacia `/dashboard?publicId={public_id}`.
- `claim_code` no va en QR/NFC, no va en URL, no se guarda en storage, no se loguea y se limpia despues del envio.
- El frontend no expone `claim_code_hash`, `claim_attempts` ni `claim_locked_until`.

## Private Profile Management Frontend

Sprint 18 migra `/login` y `/dashboard` a sesion server-side con cookie HttpOnly y CSRF double-submit.

Estado de seguridad actual:

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- Si el login es correcto, el backend setea cookies y devuelve `user`; no devuelve tokens.
- `/login` no guarda tokens en storage ni muestra tokens.
- `/login` detecta sesion activa contra `/api/auth/me` y redirige automaticamente al destino seguro.
- Despues de login exitoso, `/login` redirige automaticamente con `router.replace()` al `returnTo` seguro o `/dashboard`.
- `/dashboard` valida sesion contra `GET /api/auth/me` usando cookie.
- `/dashboard` no mantiene fallback de token manual.
- `/dashboard` tiene boton `Cerrar sesion` que llama `POST /api/auth/logout` con CSRF.
- `/login` y `/dashboard` tienen enlace `Volver al inicio`.
- Es una sesion server-side con cookie HttpOnly.
- No se usa `sessionStorage` ni `localStorage` para auth.
- Se usa cookie CSRF legible por JS para double-submit.
- No hay refresh token.
- No hay expiracion/renovacion automatica desde frontend.
- Los endpoints privados estan protegidos por cookie de sesion.
- Produccion debe usar HTTPS, `Secure=true`, prefijo `__Host-`, `Path=/` y sin `Domain`.
- El frontend consume datos del usuario autenticado segun las validaciones del backend.
- Tokens y datos medicos no deben loguearse.

Flujo actual:

- Valida sesion contra `GET /api/auth/me`.
- Carga dispositivos con `GET /api/devices`.
- Permite activar/asociar un identificador fisico desde `Activar identificador` con `POST /api/devices/activate`.
- Carga perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Crea o actualiza perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- Si no hay sesion, `/dashboard` muestra estado no autenticado y boton/link `Ir a login`.
- Si la sesion expiro o es invalida, muestra error controlado y permite volver a login.
- La organizacion visual de `/dashboard` separa estado de sesion, activacion de identificador, dispositivos y editor de perfil.
- Los dispositivos muestran `public_id`, estado legible, descripcion operacional y seleccion; no muestran IDs internos visualmente.
- El editor agrupa Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica.

## Device Activation UX

Sprint 12 expone activacion de identificadores desde `/dashboard`; Sprint 14 cambia el backend para exigir `public_id + claim_code`; Sprint 15 actualiza el frontend para enviar ambos campos.

- La seccion `Activar identificador` usa `public_id` con formato `PID-XXXXXXXXXX` y `claim_code` con formato `XXXX-XXXX-XXXX`.
- El `public_id` puede estar impreso o asociado al QR/NFC fisico.
- El `public_id` no contiene datos medicos.
- La UI recomienda verificar fisicamente el identificador antes de activarlo.
- El cliente `activateDeviceWithClaimCode(publicId, claimCode): Promise<Device>` esta en `apps/web/lib/devices.ts`, usa `buildApiUrl`, cookie de sesion y CSRF.
- Maneja errores controlados: `400` datos de activacion invalidos, `401` sesion expirada o no autenticada, `404` identificador no disponible, `422` codigo de activacion invalido o incompleto y `429` demasiados intentos.
- El dashboard muestra `Activando...` durante la solicitud y `Identificador vinculado correctamente.` al terminar.
- El dashboard refresca o actualiza la lista de dispositivos y muestra descripcion operacional por estado.
- El dashboard limpia `claim_code` del estado despues del envio y no lo guarda en storage.
- Estados visibles: `pending_activation` -> `Pendiente de activación`, `active` -> `Activo`, `disabled` -> `Deshabilitado`, `lost` -> `Reportado como perdido`.
- No se deben loguear tokens, cookies ni datos medicos.
- No hay scanner QR, lectura NFC, camara, geolocalizacion, tracking, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend ni creacion admin de devices desde frontend.
- El backend sigue siendo la fuente de autorizacion.

## QR Management Frontend

Sprint 11 expone gestion QR administrativa desde `/dashboard` con descarga controlada del PNG sin cambiar la autorizacion backend.

- El dashboard consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- El dashboard permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr`.
- El dashboard permite descargar QR con `GET /api/admin/devices/{device_id}/qr/download` usando `downloadDeviceQr(deviceId): Promise<Blob>`.
- Los endpoints QR requieren cookie de sesion y `role=admin`; `POST` requiere CSRF.
- Para usuarios no-admin, `/dashboard` oculta visualmente Gestion QR, generar, regenerar, descargar, estado QR, `object_key` y mensajes de permisos QR.
- Para admin, `/dashboard` mantiene Gestion QR.
- Si no hay sesion o expiro, la descarga muestra `Sesión expirada o no autenticada.`.
- Si el QR no existe, muestra `QR no encontrado. Genera el QR antes de descargarlo.` o la ayuda `Genera el QR antes de descargarlo.`.
- Si descarga correctamente, muestra `QR descargado correctamente.`.
- El dashboard no debe romper si QR responde `403`; devices y editor de perfil siguen disponibles.
- El QR apunta a `/p/{public_id}`.
- El QR solo contiene la URL publica del perfil y no incluye datos medicos embebidos.
- La visualizacion depende de que el perfil este operativo segun readiness.
- `object_key` se muestra solo como detalle tecnico administrativo.
- La descarga obtiene el PNG desde el backend autenticado.
- El navegador crea un objeto temporal con `URL.createObjectURL` y lo revoca con `URL.revokeObjectURL`.
- No se deben loguear tokens, cookies ni datos medicos.
- No hay presigned URLs, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones.

Campos gestionados: `display_name`, `blood_type`, `allergies`, `allergies_none`, `medical_conditions`, `medical_conditions_none`, `medications`, `medications_none`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes`, `public_consent_accepted_at`, `public_consent_version` e `is_public`.

`is_public` expresa intencion de publicacion, pero el backend solo publica si readiness y consentimiento vigente permiten operacion.

## Estado actual

El estado actual no implementa validacion estricta de telefono internacional, wizard profesional multi-vista para perfil, recuperacion de password, refresh token, MFA, captcha, proteccion anti-bot, roles avanzados en frontend, expiracion visual previa de la sesion, auditoria formal de eventos criticos, historial/versionado completo de consentimientos, segundo contacto de emergencia, normalizacion avanzada de datos medicos, hardening de rate limiting publico, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC real desde navegador, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR, presigned URL publica ni provisionamiento masivo con export de `claim_code`. El registro no inicia sesion automaticamente y roles siguen siendo strings.

Sprint 13 agrega campos de claim a `devices`, servicio `claim_codes` y endpoint publico minimo de estado. Sprint 14 actualiza `POST /api/devices/activate` para requerir `public_id + claim_code` y bloqueo temporal por intentos fallidos. Sprint 15 agrega onboarding publico y actualiza dashboard para enviar `claim_code`. Sprint 16 agrega registro de usuario final, `returnTo` seguro y UX post-vinculacion hacia completar perfil. Sprint 17 agrega readiness productivo, consentimiento explicito, bloqueo de publicacion incompleta, endpoint privado de readiness, endpoint publico endurecido y progreso en dashboard. Sprint 18 migra auth a sesiones server-side con cookie HttpOnly y CSRF double-submit.

`device_type="qr_nfc_tag"` existe como base del modelo de dispositivo. QR Foundation ya existe; NFC todavia no esta implementado.
