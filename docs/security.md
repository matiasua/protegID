# Seguridad

## Reglas iniciales

- No guardar datos medicos en QR.
- No subir secretos al repositorio.
- No hardcodear credenciales.
- No loguear datos medicos o sensibles.
- No usar IDs secuenciales como identificadores publicos.
- No exponer IDs internos en URLs publicas.
- Mantener configuracion sensible mediante variables de entorno.

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
- `POST /api/devices/activate` requiere Bearer token.
- `POST /api/admin/devices` requiere `role=admin`.
- `public_id` no es secuencial.
- `public_id` no usa el UUID interno completo como identificador publico visible.

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
- Endpoints admin `GET /api/admin/devices/{device_id}/qr` y `POST /api/admin/devices/{device_id}/qr`.

Reglas de seguridad y privacidad:

- El QR no contiene datos medicos.
- El QR contiene solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`.
- Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.
- Ambos endpoints QR requieren Bearer token.
- Ambos endpoints QR requieren `role=admin`.
- Los endpoints QR solo devuelven metadata: `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`.
- No se devuelve el archivo PNG todavia.
- No se entrega presigned URL todavia.

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
- Los datos medicos no deben loguearse.

## Private Profile Management Frontend

Sprint 8 agrega Auth Frontend Foundation inicial con `/login` y sesion temporal para `/dashboard`.

Estado de seguridad actual:

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- Si el login es correcto, recibe `access_token` y `token_type`.
- `/login` guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token`.
- `/login` muestra el token en `textarea` readonly por transparencia temporal del MVP.
- `/dashboard` lee automaticamente el token desde `sessionStorage` con `getSessionToken()`.
- `/dashboard` valida sesion contra `GET /api/auth/me`.
- `/dashboard` mantiene fallback tecnico para pegar token manualmente.
- `/dashboard` tiene boton `Cerrar sesion` que limpia `sessionStorage` con `clearSessionToken()`.
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
- Carga perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Crea o actualiza perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- Si no hay sesion, `/dashboard` muestra estado no autenticado y boton/link `Ir a login`.
- Si el token expiro o es invalido, muestra error controlado y permite volver a login.

Campos gestionados: `display_name`, `blood_type`, `allergies`, `medical_conditions`, `medications`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes` e `is_public`.

`is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.

## Estado actual

El estado actual no implementa registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, subida de archivos medicos, gestion de QR desde frontend, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, descarga publica de QR, presigned URL publica ni MFA.

Sprint 8 no agrega nuevas tablas ni nuevas migraciones.

`device_type="qr_nfc_tag"` existe como base del modelo de dispositivo. QR Foundation ya existe; NFC todavia no esta implementado.
