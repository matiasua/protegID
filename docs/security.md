# Seguridad

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

## Autenticacion

Sprint 2 implementa Auth Foundation:

- Password hashing con Argon2 mediante `pwdlib`.
- JWT access token.
- `POST /api/auth/register` crea usuarios.
- `POST /api/auth/login` devuelve `access_token` y `token_type`.
- `GET /api/auth/me` requiere Bearer token y devuelve el usuario actual.

`password_hash` nunca debe exponerse en respuestas. Passwords y tokens no deben loguearse.

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

- `GET /api/devices` requiere Bearer token.
- `GET /api/devices` solo lista devices del usuario autenticado.
- `POST /api/devices/activate` requiere Bearer token y body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`.
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

- Requiere Bearer token.
- Requiere `public_id` valido y `claim_code` valido.
- Solo permite activar devices `pending_activation`.
- El device no debe tener `user_id` asignado.
- Debe existir `claim_code_hash`.
- Si todo es valido, el device pasa a `active`, se asigna `user_id`, se setean `activated_at` y `claimed_at`, `claim_attempts` vuelve a `0` y `claim_locked_until` queda `null`.

Errores esperados:

- Sin token -> `401`.
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

- El frontend todavia debe actualizarse para enviar `claim_code`.
- El dashboard actual puede quedar temporalmente incompatible con la nueva activacion.
- Aun no existe UI first-scan en `/p/{public_id}`.
- Aun no existe registro de usuario final desde primer escaneo.
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

- Los endpoints privados requieren Bearer token.
- Los endpoints privados validan ownership mediante `current_user.id` y `device.user_id`.
- El endpoint publico no requiere autenticacion.
- El endpoint publico busca por `Device.public_id`.
- El endpoint publico solo responde si `device.status == "active"`.
- El endpoint publico solo responde si `emergency_profile.is_public == true`.
- El endpoint publico solo responde si `emergency_profile.deleted_at is null`.
- La respuesta publica no expone `id` interno.
- La respuesta publica no expone `device_id`.
- La respuesta publica no expone `created_at`, `updated_at` ni `deleted_at`.
- Los datos medicos no deben loguearse.

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
- Los endpoints QR requieren Bearer token.
- Los endpoints QR requieren `role=admin`; usuario no admin recibe `403`.
- Sin token, los endpoints QR responden `401`.
- `GET /api/admin/devices/{device_id}/qr` devuelve metadata: `device_id`, `public_id`, `object_key`, `content_type` y `exists`.
- `POST /api/admin/devices/{device_id}/qr` genera/sube el QR.
- `GET /api/admin/devices/{device_id}/qr/download` busca el device por `device_id`, lee `qr/devices/{public_id}.png` desde MinIO y no genera QR automaticamente.
- Si el QR no existe, la descarga responde `404`.
- Si el QR existe, la descarga responde `Content-Type: image/png` y `Content-Disposition: attachment; filename="{public_id}.png"`.
- No se entrega presigned URL.
- No se expone bucket, credenciales ni URL publica de MinIO.
- El backend sigue siendo la fuente de autorizacion para gestion QR.

## Public Profile Frontend

Sprint 6 implementa la ruta publica frontend `/p/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

Reglas de seguridad y privacidad:

- La pagina publica no requiere login.
- La pagina consulta server-side `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si no existe o no esta disponible, responde `404` real usando `notFound()`.
- No expone IDs internos.
- No expone `device_id`.
- No expone timestamps.
- No expone `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El 404 no debe revelar si el `public_id` existe o no.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.
- `/p/{public_id}` solo agrega un enlace discreto `ProtegID` hacia `/`; no expone datos internos.
- Los datos medicos no deben loguearse.

## Private Profile Management Frontend

Sprint 9 mantiene la sesion temporal de `/login` y `/dashboard`, y mejora UX/navegacion sin cambiar la estrategia de auth.

Estado de seguridad actual:

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- Si el login es correcto, recibe `access_token` y `token_type`.
- `/login` guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token`.
- `/login` muestra el token en `textarea` readonly por transparencia temporal del MVP.
- `/login` detecta si ya existe una sesion temporal en `sessionStorage` y muestra `Ya existe una sesión temporal activa.`.
- `/login` permite ir a `/dashboard` o cerrar la sesion temporal con `clearSessionToken()` sin validar automaticamente contra backend.
- Despues de login exitoso, `/login` muestra `Continuar al dashboard` y no redirige automaticamente.
- `/dashboard` lee automaticamente el token desde `sessionStorage` con `getSessionToken()`.
- `/dashboard` valida sesion contra `GET /api/auth/me`.
- `/dashboard` mantiene fallback tecnico reducido como `Usar token manual` para pegar token manualmente.
- `/dashboard` tiene boton `Cerrar sesion` que limpia `sessionStorage` con `clearSessionToken()`.
- `/login` y `/dashboard` tienen enlace `Volver al inicio`.
- Es una sesion temporal para MVP.
- Se usa `sessionStorage`, no `localStorage`.
- No se usan cookies.
- No hay refresh token.
- No hay middleware de proteccion.
- No hay expiracion/renovacion automatica desde frontend.
- Los endpoints privados siguen protegidos por Bearer token.
- El token vive solo durante la sesion/pestana del navegador.
- `sessionStorage` no se comparte entre pestanas.
- Para produccion se evaluara una estrategia mas robusta.
- El frontend consume datos del usuario autenticado segun las validaciones del backend.
- Tokens y datos medicos no deben loguearse.

Flujo actual:

- Valida sesion contra `GET /api/auth/me`.
- Carga dispositivos con `GET /api/devices`.
- Permite activar/asociar un identificador fisico desde `Activar identificador` con `POST /api/devices/activate`.
- Carga perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Crea o actualiza perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- Si no hay sesion, `/dashboard` muestra estado no autenticado y boton/link `Ir a login`.
- Si el token expiro o es invalido, muestra error controlado y permite volver a login.
- La organizacion visual de `/dashboard` separa estado de sesion, activacion de identificador, dispositivos, editor de perfil y fallback tecnico.
- Los dispositivos muestran `public_id`, estado legible, descripcion operacional y seleccion; no muestran IDs internos visualmente.
- El editor agrupa Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica.

## Device Activation UX

Sprint 12 expone activacion de identificadores desde `/dashboard`; Sprint 14 cambia el backend para exigir `public_id + claim_code`.

- La seccion `Activar identificador` usa `public_id` con formato `PID-XXXXXXXXXX`.
- El `public_id` puede estar impreso o asociado al QR/NFC fisico.
- El `public_id` no contiene datos medicos.
- La UI recomienda verificar fisicamente el identificador antes de activarlo.
- El cliente actual `activateDevice(publicId, accessToken): Promise<Device>` esta en `apps/web/lib/devices.ts`, usa `buildApiUrl` y todavia debe actualizarse para enviar `claim_code`.
- Maneja errores controlados: `400` identificador no disponible para activacion, `401` sesion expirada o no autenticada, `404` identificador no encontrado.
- El dashboard muestra `Activando...` durante la solicitud y `Identificador activado correctamente.` al terminar.
- El dashboard refresca o actualiza la lista de dispositivos y muestra descripcion operacional por estado.
- El dashboard actual puede quedar temporalmente incompatible con la nueva activacion hasta el sprint frontend.
- Estados visibles: `pending_activation` -> `Pendiente de activación`, `active` -> `Activo`, `disabled` -> `Deshabilitado`, `lost` -> `Reportado como perdido`.
- No se deben loguear tokens ni datos medicos.
- No hay scanner QR, lectura NFC, camara, geolocalizacion, tracking, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend ni creacion admin de devices desde frontend.
- El backend sigue siendo la fuente de autorizacion.

## QR Management Frontend

Sprint 11 expone gestion QR administrativa desde `/dashboard` con descarga controlada del PNG sin cambiar la autorizacion backend.

- El dashboard consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- El dashboard permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr`.
- El dashboard permite descargar QR con `GET /api/admin/devices/{device_id}/qr/download` usando `downloadDeviceQr(deviceId, accessToken): Promise<Blob>`.
- Los endpoints QR requieren Bearer token y `role=admin`.
- Si el usuario no es admin o QR responde `403`, el frontend muestra `La gestión de QR requiere rol admin.`.
- Si no hay token o la sesion expiro, la descarga muestra `Sesión expirada o no autenticada.`.
- Si el QR no existe, muestra `QR no encontrado. Genera el QR antes de descargarlo.` o la ayuda `Genera el QR antes de descargarlo.`.
- Si descarga correctamente, muestra `QR descargado correctamente.`.
- El dashboard no debe romper si QR responde `403`; devices y editor de perfil siguen disponibles.
- El QR apunta a `/p/{public_id}`.
- El QR solo contiene la URL publica del perfil y no incluye datos medicos embebidos.
- La visualizacion depende de que el perfil este marcado como publico.
- `object_key` se muestra solo como detalle tecnico.
- La descarga obtiene el PNG desde el backend autenticado.
- El navegador crea un objeto temporal con `URL.createObjectURL` y lo revoca con `URL.revokeObjectURL`.
- No se deben loguear tokens ni datos medicos.
- No hay presigned URLs, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones.

Campos gestionados: `display_name`, `blood_type`, `allergies`, `medical_conditions`, `medications`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes` e `is_public`.

`is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.

## Estado actual

El estado actual no implementa registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR, presigned URL publica, UI first-scan, registro de usuario final desde primer escaneo, provisionamiento masivo con export de `claim_code`, auditoria formal de intentos ni MFA.

Sprint 13 agrega campos de claim a `devices`, servicio `claim_codes` y endpoint publico minimo de estado. Sprint 14 actualiza `POST /api/devices/activate` para requerir `public_id + claim_code` y bloqueo temporal por intentos fallidos, pero no cambia todavia el frontend.

`device_type="qr_nfc_tag"` existe como base del modelo de dispositivo. QR Foundation ya existe; NFC todavia no esta implementado.
