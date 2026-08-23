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
- No loguear tokens raw de verificacion.
- No loguear `claim_code` ni `claim_code_hash`.
- No incluir `claim_code` en QR/NFC, URLs ni respuestas API.
- No guardar `claim_code` en texto plano.
- No guardar tokens raw de verificacion en DB ni storage.
- No incluir emails planos en Redis keys.
- No publicar perfiles incompletos ni sin consentimiento vigente.
- No inferir consentimiento desde `is_public`.
- No exponer campos internos de readiness, consentimiento ni ids internos en endpoints publicos.
- Toda futura tabla debe tener migracion.
- Todo futuro endpoint debe usar schemas/validaciones.
- No modificar el modelo de sesiones seguras sin justificacion explicita de producto o seguridad.

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

Auth productivo ya existe e incluye modelo `User`, tabla `users`, hashing de passwords, tabla `auth_sessions`, sesion server-side revocable y cookies seguras. `POST /api/auth/login` crea `auth_session`, setea `protegid_session` HttpOnly y `protegid_csrf`, y devuelve `user`; no devuelve `access_token`, `token_type`, token opaco ni `session_token_hash`. `CurrentUserDep` autentica solo por cookie de sesion. `POST /api/auth/logout` requiere CSRF, revoca la sesion y borra cookies. El token raw de sesion nunca debe guardarse en DB; solo `session_token_hash`. `password_hash`, tokens de sesion y CSRF tokens no deben exponerse ni loguearse.

CSRF usa double-submit: cookie `protegid_csrf` legible por JS + header `X-CSRF-Token`. Aplica a `POST`, `PUT`, `PATCH` y `DELETE` cuando hay cookie de sesion. Login y `POST /api/auth/verify-email` no requieren CSRF. `POST /api/auth/resend-verification`, logout y mutaciones privadas siguen requiriendo CSRF. Requests privados sin sesion deben responder `401`; requests con sesion y CSRF faltante/incorrecto deben responder `403`.

Email Verification ya existe. `POST /api/auth/register` crea usuario no verificado, no inicia sesion y envia correo. El token raw de verificacion no se guarda; DB guarda `token_hash` en `auth_action_tokens`. `POST /api/auth/verify-email` es publico y usa token one-time-use con expiracion, `used_at`, `revoked_at` y proposito `email_verification`. Login se permite sin email verificado, pero acciones criticas requieren verificacion backend.

Rate limiting ya existe con Redis. Endpoints criticos deben fallar cerrado con `503` si Redis no esta disponible. No guardar tokens, `claim_code` ni emails planos en Redis; email se hashea con SHA-256 para keys.

Device Foundation ya existe e incluye modelo `Device`, tabla `devices`, relacion nullable `devices.user_id -> users.id`, generacion de `public_id` con formato `PID-XXXXXXXXXX`, campos `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until`, y endpoints protegidos basicos de devices. Los campos de claim no deben exponerse por API.

First Scan Activation Foundation ya existe como base tecnica de Sprint 13 y Claim Code Activation Backend ya existe desde Sprint 14. ProtegID vendera identificadores fisicos con QR impreso y NFC grabado. QR/NFC apuntan a `/p/{public_id}`. `public_id` es publico. `claim_code` es privado, viene dentro del empaque fisico, no va en QR/NFC, no va en URL, no debe loguearse y no debe guardarse en texto plano.

El servicio `apps/api/app/services/claim_codes.py` incluye `generate_claim_code()`, `normalize_claim_code()`, `hash_claim_code()` y `verify_claim_code()`. Genera formato `XXXX-XXXX-XXXX` con caracteres no ambiguos y `secrets`, acepta codigo con o sin guiones y reutiliza `hash_password()` / `verify_password()`.

El endpoint publico `GET /api/public/devices/{public_id}/activation-status` no requiere autenticacion y responde `200` solo si el device existe y esta `pending_activation`. Para `active`, `disabled`, `lost` o inexistente responde `404` generico. No debe revelar owner, `user_id`, `claim_code_hash`, `claimed_at`, `claim_attempts`, `claim_locked_until`, datos medicos ni perfil.

`POST /api/devices/activate` requiere cookie de sesion, CSRF y body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`. Solo debe activar devices `pending_activation`, sin `user_id`, con `claim_code_hash` existente y `claim_code` valido. Si activa correctamente, debe setear `user_id`, `status=active`, `activated_at`, `claimed_at`, `claim_attempts=0` y `claim_locked_until=null`. Debe rechazar reactivacion, devices `active`, `disabled` o `lost`, y no debe exponer `claim_code`, `claim_code_hash`, `claimed_at`, `claim_attempts` ni `claim_locked_until`.

Proteccion anti fuerza bruta de claim: `MAX_CLAIM_ATTEMPTS = 5`, `CLAIM_LOCK_MINUTES = 15`; cada `claim_code` incorrecto incrementa `claim_attempts`, el quinto intento setea `claim_locked_until`, durante bloqueo responde `429 Too many activation attempts. Try again later.` y una activacion correcta limpia `claim_attempts` y `claim_locked_until`.

Public Profile Foundation ya existe e incluye modelo `EmergencyProfile`, tabla `emergency_profiles`, relacion unica `emergency_profiles.device_id -> devices.id`, endpoints privados para ver/crear/editar el perfil de un device, endpoint privado de readiness y endpoint publico de lectura por `public_id`.

Profile Readiness & Public Profile Completion ya existe. Identificador vinculado no significa ProtegID operativo. El identificador queda vinculado con `public_id + claim_code`; ProtegID queda operativo solo si el perfil cumple datos minimos, consentimiento vigente e `is_public=true`. Campos minimos: `display_name`, `emergency_contact_name`, `emergency_contact_relationship`, `emergency_contact_phone`, decision explicita para condiciones medicas/alergias/medicamentos, `public_consent_accepted_at`, `public_consent_version` vigente e `is_public=true`. Campos nuevos: `medical_conditions_none`, `allergies_none`, `medications_none`, `public_consent_accepted_at`, `public_consent_version`; `is_public` default `false` para nuevos perfiles.

El consentimiento publico es explicito, usa `PUBLIC_PROFILE_CONSENT_VERSION`, no se infiere desde `is_public` y no se expone publicamente. La fuente de verdad productiva para readiness/publicacion/acceso publico es `apps/api/app/services/emergency_profile_status.py`, que separa tres dominios: `ProfileReadiness` (solo `EmergencyProfile`), `PublicationEligibility` (agrega consentimiento) y `PublicAccessStatus` (agrega Device + ProtectedPerson, especifico de un device/public_id). `apps/api/app/services/profile_readiness.py` (motor legacy `calculate_profile_readiness(device, profile)` que mezclaba Device+EmergencyProfile) ya no tiene callers productivos; se mantiene solo porque su eliminacion pertenece a Bloque 8.5, no a este retiro de API.

EmergencyProfile API productiva (CONTRACT, vigente desde Bloque 8.3):

- `GET /api/emergency-profile`
- `PUT /api/emergency-profile`
- `GET /api/emergency-profile/status`

Device PublicAccessStatus (productivo, device-scoped, no forma parte del retiro):

- `GET /api/devices/{device_id}/public-access-status`

Los antiguos endpoints EmergencyProfile device-scoped — `GET /api/devices/{device_id}/emergency-profile`, `PUT /api/devices/{device_id}/emergency-profile` y `GET /api/devices/{device_id}/emergency-profile/readiness` — fueron marcados `deprecated=True` en Bloque 8.1 y retirados por completo en Bloque 8.3 (dejaron de existir en el router; ya no aparecen en OpenAPI y responden `404` por ausencia de ruta, no por logica de negocio). Bloque 8.2 confirmo, con evidencia operacional externa al repo, que ese contrato nunca fue desplegado a produccion/staging ni tuvo consumidores externos al frontend, que ya usaba unicamente el contrato account-scoped; por eso el retiro se aprobo sin ventana de observacion ni fase `410 Gone`. `EmergencyProfileReadinessRead` sigue existiendo como schema (usado por `profile_readiness.py`, Bloque 8.5), pero ya no tiene un endpoint HTTP que lo sirva.

El backend bloquea `is_public=true` si el perfil no cumple readiness y responde `422 Emergency profile is not ready for publication.`. `GET /api/public/profiles/{public_id}` solo devuelve datos si `readiness.is_public_operational == true`; si no, responde `404` generico sin revelar si falta perfil, consentimiento, readiness o publicacion. No exponer `medical_conditions_none`, `allergies_none`, `medications_none`, `public_consent_accepted_at`, `public_consent_version`, `is_public`, `user_id` ni `device_id` en el schema publico.

QR Foundation ya existe e incluye configuracion `PUBLIC_APP_URL` y `PUBLIC_PROFILE_PATH`, helper `build_public_profile_url(public_id)`, generacion de QR PNG en memoria con `qrcode[pil]`, persistencia en MinIO/S3 compatible y object key estable `qr/devices/{public_id}.png`.

El QR no debe contener datos medicos. El QR debe contener solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

Public Profile Frontend ya existe en `/p/{public_id}`. La pagina no requiere login, consulta server-side `GET /api/public/profiles/{public_id}`, responde `200 OK` solo si el perfil esta operativo y, si no existe perfil publico operativo, consulta `GET /api/public/devices/{public_id}/activation-status`. Si el estado es `pending_activation`, muestra onboarding `Identificador ProtegID no activado`; si `activation-status` responde `404`, mantiene `404` real o mensaje generico con `notFound()`. No expone IDs internos, `device_id`, timestamps ni `deleted_at`; solo muestra datos de `EmergencyProfilePublicRead`. El 404 no debe revelar si el `public_id` existe o no.

La vista publica debe mantenerse como ficha de emergencia mobile-first: tipo de sangre destacado, contacto y telefono de emergencia destacados, secciones claras y campos vacios como `No informado`.

Sprint 9 agrega UX Hardening & Navigation. `/` funciona como landing inicial del MVP, incluye accesos a `/login` y `/dashboard`, explica el flujo activar identificador, completar perfil de emergencia y compartir acceso publico mediante QR/NFC, muestra el estado actual del MVP e incluye la nota `Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.`.

Auth Frontend productivo ya existe. `/login` permite ingresar email y password, consume `POST /api/auth/login`, recibe cookies HttpOnly/CSRF y redirige automaticamente con `router.replace()` a un `returnTo` sanitizado o `/dashboard`. No recibe, guarda ni muestra tokens. No usa `sessionStorage`, `localStorage`, `Authorization Bearer` ni token manual.

Private Profile Management Frontend ya existe en `/dashboard`. Valida sesion con `GET /api/auth/me` usando cookie, carga dispositivos con `GET /api/devices`, permite activar/asociar un identificador fisico desde `Activar identificador` con `public_id + claim_code`, permite seleccionar un dispositivo, carga perfil privado con `GET /api/emergency-profile`, consulta status con `GET /api/emergency-profile/status` y crea/actualiza con `PUT /api/emergency-profile` (contrato account-scoped; los endpoints device-scoped equivalentes fueron retirados en Bloque 8.3). Si no hay sesion muestra estado no autenticado y boton/link `Ir a login`. El boton `Cerrar sesion` llama `POST /api/auth/logout` con CSRF.

La sesion frontend actual es productiva para lanzamiento controlado. Usa cookie HttpOnly de sesion, cookie CSRF legible por JS y `credentials: "include"`. No guardar tokens en `sessionStorage` ni `localStorage`. No enviar `Authorization Bearer` desde frontend.

Campos del perfil privado actual: `display_name`, `blood_type`, `allergies`, `allergies_none`, `medical_conditions`, `medical_conditions_none`, `medications`, `medications_none`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes`, `public_consent_accepted_at`, `public_consent_version` e `is_public`. `is_public` expresa intencion de publicacion, pero el backend solo publica si readiness y consentimiento vigente permiten operacion.

La UX actual incluye `/login` con estados de carga, exito y error, deteccion de sesion activa y redireccion automatica segura. `/dashboard` esta organizado en estado de sesion, activacion de identificador, dispositivos y editor de perfil. Los dispositivos muestran `public_id`, estado legible, descripcion operacional y seleccion. El editor muestra progreso, estados `Perfil incompleto`, `Perfil listo para publicar` y `ProtegID operativo`, campos obligatorios faltantes/completados, controles `Sin ... declaradas`, consentimiento explicito, Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica. El dashboard no debe guardar datos medicos en `sessionStorage` ni `localStorage`.

First Scan Onboarding Frontend ya existe en `/p/{public_id}`. `apps/web/lib/public-devices.ts` expone `getPublicDeviceActivationStatus(publicId)`, que retorna estado en `200`, retorna `null` en `404`, no usa token, no envia `Authorization` y no maneja `claim_code`. El onboarding indica que el identificador fisico aun no esta vinculado, que el `claim_code` viene dentro del empaque fisico y que el QR/NFC solo contiene la URL publica permanente. Muestra `public_id` como referencia tecnica discreta. Sin sesion, CTA login apunta a `/login?returnTo=/p/{public_id}` y CTA crear cuenta apunta a `/register?returnTo=/p/{public_id}`. `apps/web/app/p/[publicId]/activation-form.tsx` valida sesion con `/api/auth/me`; con sesion permite ingresar `claim_code`, llama `activateDeviceWithClaimCode(publicId, claimCode)` con cookie y CSRF, muestra `Identificador vinculado correctamente.` y CTA `Completar perfil de emergencia` hacia `/dashboard?publicId={public_id}`.

Device Activation UX ya existe en `/dashboard`. Usa el formulario `Activar identificador` con inputs `public_id` y `claim_code`, placeholders `PID-XXXXXXXXXX` y `XXXX-XXXX-XXXX`, boton `Activar identificador`, estado `Activando...` y exito `Identificador vinculado correctamente.`. El cliente frontend actual es `activateDeviceWithClaimCode(publicId, claimCode): Promise<Device>` en `apps/web/lib/devices.ts`, usa cookie de sesion y CSRF, y envia `public_id + claim_code`. El dashboard refresca la lista de dispositivos despues de activar, limpia `claim_code` del estado y no lo guarda en storage. `/dashboard?publicId={public_id}` selecciona automaticamente el dispositivo si pertenece al usuario y carga el editor de perfil.

User Registration Flow ya existe en `/register`. El formulario pide Nombre, Email y Password, usa `register(payload)`, envia `full_name`, no guarda token, no inicia sesion automaticamente, no usa `localStorage` ni `sessionStorage`, limpia password tras registro exitoso y muestra `Ya existe una cuenta con este correo.` ante `409`. `/register` y `/login` soportan `returnTo` sanitizado: solo rutas internas seguras. Tras login exitoso, `/login` redirige automaticamente al destino seguro.

Errores controlados de activacion frontend: `400` -> `Datos de activación inválidos.`, `401` -> `Sesión expirada o no autenticada.`, `404` -> `Identificador no disponible.`, `422` -> `Código de activación inválido o incompleto.`, `429` -> `Demasiados intentos. Intenta nuevamente más tarde.`, generico -> `No se pudo activar el identificador.`.

El dashboard muestra estados de device como `pending_activation` -> `Pendiente de activación`, `active` -> `Activo`, `disabled` -> `Deshabilitado` y `lost` -> `Reportado como perdido`, con descripcion operacional por estado. No implementar cambio de estado desde frontend, reporte de perdido desde frontend ni creacion admin de devices desde frontend salvo solicitud explicita.

QR Management Frontend ya existe en `/dashboard`. Consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`, muestra `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`, permite generar/regenerar QR con `POST /api/admin/devices/{device_id}/qr` para usuarios admin usando CSRF y permite descargar el PNG con `GET /api/admin/devices/{device_id}/qr/download` mediante `downloadDeviceQr(deviceId): Promise<Blob>`.

Para usuario no-admin, `/dashboard` no debe mostrar Gestion QR, estado QR, generar, regenerar, descargar QR, `object_key` ni mensaje `La gestión de QR requiere rol admin.`. Para admin, `/dashboard` mantiene Gestion QR. El backend sigue siendo la fuente de autorizacion.

El QR apunta a `/p/{public_id}` y solo contiene la URL publica del perfil. No incluye datos medicos embebidos. La visualizacion depende de que el perfil este operativo segun readiness. `object_key` puede mostrarse como detalle tecnico solo para admin. La descarga QR debe obtener el PNG desde el backend autenticado, no debe exponer URL publica de MinIO, bucket ni credenciales, y debe usar `URL.createObjectURL` con `URL.revokeObjectURL` en el navegador. No se debe implementar presigned URLs, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones salvo solicitud explicita.

La navegacion actual incluye `Volver al inicio` en `/login` y `/dashboard`, enlace discreto `ProtegID` hacia `/` en `/p/{public_id}` y not-found publico con `404` real, vuelta al inicio y sin revelar si el `public_id` existe.

Next dev usa `.next-dev`; `next build` usa `.next`. Para validar build frontend sin ensuciar el contenedor dev, usar:

```bash
docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"
```

Validacion esperada de auth frontend:

- `GET /` responde `200 OK`.
- `GET /dashboard` responde `200 OK`.
- `GET /login` responde `200 OK`.
- `GET /p/PID-G2NYZP87KA` responde `200 OK`.
- `GET /p/PID-AAAAAAAAAA` responde `404 Not Found`.
- Prueba GUI: login con usuario de prueba, confirmar cookies `protegid_session` HttpOnly y `protegid_csrf`, abrir/refrescar `/dashboard`, confirmar carga automatica de usuario/devices y cerrar sesion real.
- Prueba GUI de onboarding: `/p/{public_id_pending}` muestra onboarding; sin sesion muestra CTA login; con sesion muestra formulario `claim_code`; claim correcto activa device; claim incorrecto muestra error controlado.
- Prueba GUI de activacion: crear cuenta desde primer escaneo, login con `returnTo`, volver a `/p/{public_id}`, ingresar `claim_code`, ver `Identificador vinculado correctamente.`, ir a `/dashboard?publicId={public_id}`, confirmar que queda seleccionado y confirmar que usuario final no ve Gestion QR. Confirmar que `claim_code` no queda en storage.
- Usuario admin: ve estado QR y puede generar/regenerar QR.
- Usuario admin: puede descargar `PID-XXXXXXXXXX.png` desde Gestion QR.
- QR inexistente: muestra ayuda para generarlo antes de descargarlo.
- Usuario no admin: no ve Gestion QR, generar, regenerar, descargar QR, `object_key` ni mensaje de permisos QR.

Estados de device existentes:

- `pending_activation` -> `Pendiente de activación`
- `active` -> `Activo`
- `disabled` -> `Deshabilitado`
- `lost` -> `Reportado como perdido`

Endpoints de devices existentes:

- `GET /api/devices`
- `POST /api/devices/activate`
- `POST /api/admin/devices`
- `GET /api/public/devices/{public_id}/activation-status`

Endpoints de perfiles de emergencia existentes:

- `GET /api/emergency-profile`
- `PUT /api/emergency-profile`
- `GET /api/emergency-profile/status`
- `GET /api/devices/{device_id}/public-access-status`
- `GET /api/public/profiles/{public_id}`

Los endpoints device-scoped `GET/PUT /api/devices/{device_id}/emergency-profile` y `GET /api/devices/{device_id}/emergency-profile/readiness` existieron como contrato legacy y fueron retirados en Bloque 8.3 (CONTRACT).

Endpoints admin de QR existentes:

- `GET /api/admin/devices/{device_id}/qr`
- `POST /api/admin/devices/{device_id}/qr`
- `GET /api/admin/devices/{device_id}/qr/download`

El endpoint publico no requiere autenticacion, busca por `Device.public_id`, solo responde si `readiness.is_public_operational == true`, y no expone `id`, `device_id`, `user_id`, `is_public`, flags `*_none`, consentimiento, `created_at`, `updated_at` ni `deleted_at`. Si no cumple readiness responde `404` generico.

Los endpoints QR requieren cookie de sesion y `role=admin`; `POST /qr` requiere CSRF. `GET /qr` devuelve metadata: `device_id`, `public_id`, `object_key`, `content_type` y `exists`. `POST /qr` genera/sube el QR. `GET /qr/download` lee `qr/devices/{public_id}.png` desde MinIO, no genera QR automaticamente, responde `404` si no existe y, si existe, responde PNG con `Content-Type: image/png` y `Content-Disposition: attachment; filename="{public_id}.png"`. No entrega presigned URL ni expone bucket o credenciales.

No implementar validacion estricta de telefono internacional, wizard profesional multi-vista para perfil, recuperacion de password, MFA, captcha, proteccion anti-bot adicional, roles avanzados en frontend, auditoria formal de eventos criticos, historial/versionado completo de consentimientos, segundo contacto de emergencia, normalizacion avanzada de datos medicos, subida de archivos medicos, presigned URLs, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC real desde navegador, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR ni provisionamiento masivo con export de `claim_code` salvo solicitud explicita. Registro no inicia sesion automaticamente.

No crear nuevas tablas ni migraciones salvo solicitud explicita.

`device_type="qr_nfc_tag"` existe como base del modelo. QR Foundation ya existe; NFC todavia no esta implementado.
