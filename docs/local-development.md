# Desarrollo Local

## Requisitos

- Docker
- Docker Compose
- Make

## Configuracion

```bash
cp .env.example .env
```

Los valores de `.env.example` son ejemplos locales. No deben usarse como secretos reales fuera del entorno local.

## Levantar servicios

```bash
make up
```

Servicios principales:

- Home / landing MVP via Nginx: `http://localhost:8080`
- Login frontend temporal: `http://localhost:8080/login`
- Dashboard privado temporal: `http://localhost:8080/dashboard`
- Perfil publico frontend: `http://localhost:8080/p/PID-XXXXXXXXXX`
- API healthcheck: `http://localhost:8080/api/health`
- API readiness: `http://localhost:8080/api/ready`
- Auth register: `http://localhost:8080/api/auth/register`
- Auth login: `http://localhost:8080/api/auth/login`
- Auth me: `http://localhost:8080/api/auth/me`
- Devices list: `http://localhost:8080/api/devices`
- Device activate: `http://localhost:8080/api/devices/activate`
- Public device activation status: `http://localhost:8080/api/public/devices/{public_id}/activation-status`
- Admin device create: `http://localhost:8080/api/admin/devices`
- Admin device QR status: `http://localhost:8080/api/admin/devices/{device_id}/qr`
- Admin device QR generate: `http://localhost:8080/api/admin/devices/{device_id}/qr`
- Admin device QR download: `http://localhost:8080/api/admin/devices/{device_id}/qr/download`
- Private emergency profile: `http://localhost:8080/api/devices/{device_id}/emergency-profile`
- Public emergency profile: `http://localhost:8080/api/public/profiles/{public_id}`
- Web directa en desarrollo: `http://localhost:3000`
- API directa en desarrollo: `http://localhost:8000/api/health`
- MinIO console: `http://localhost:9001`

## Variables JWT

La API requiere estas variables para emitir y validar access tokens:

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Los valores de `.env.example` son solo para desarrollo local.

## Variables publicas para QR

La API usa estas variables para construir la URL publica que se codifica dentro del QR:

- `PUBLIC_APP_URL`: origen publico de la aplicacion. Valor local: `http://localhost:8080`.
- `PUBLIC_PROFILE_PATH`: path publico de perfil. Valor local: `/p`.

El helper `build_public_profile_url(public_id)` construye URLs con formato `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

## Build frontend con Docker

El contenedor de desarrollo de Next usa `.next-dev`. El build usa `.next`.

Para validar el build del frontend sin reutilizar los artefactos del contenedor de desarrollo:

```bash
docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"
```

Evitar ejecutar `npm run build` dentro del contenedor dev vivo si puede mezclar artefactos `.next`.

## Comandos utiles

```bash
make ps
make logs
make down
make build
```

Validaciones basicas del backend:

```bash
python3 -m py_compile apps/api/app/models/device.py apps/api/app/services/claim_codes.py apps/api/app/api/public_devices.py apps/api/app/main.py apps/api/app/schemas/device.py
docker compose exec protegid-api python -m compileall app alembic
git diff --check
```

## Migraciones de base de datos

Alembic vive dentro de `apps/api` y lee `DATABASE_URL` desde la configuracion de la API.

```bash
docker compose exec protegid-api alembic current
docker compose exec protegid-api alembic upgrade head
docker compose exec protegid-api alembic history
```

## Auth Foundation

Endpoints actuales:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

`GET /api/auth/me` requiere header `Authorization: Bearer <access_token>`.

No hay refresh token, recuperacion de password ni MFA.

## Device Foundation

La API incluye la base de dispositivos:

- Modelo `Device`.
- Tabla `devices`.
- Relacion nullable `devices.user_id -> users.id`.
- `public_id` con formato `PID-XXXXXXXXXX`.
- Alfabeto seguro para `public_id`: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`.
- Campos de claim seguro: `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until`.

Estados actuales:

- `pending_activation` -> `Pendiente de activación` en dashboard.
- `active` -> `Activo` en dashboard.
- `disabled` -> `Deshabilitado` en dashboard.
- `lost` -> `Reportado como perdido` en dashboard.

Endpoints protegidos:

- `GET /api/devices`: requiere Bearer token y solo lista devices del usuario autenticado.
- `POST /api/devices/activate`: requiere Bearer token y body `{ "public_id": "PID-XXXXXXXXXX" }`; activa/asocia un device `pending_activation` por `public_id`, cambia `status` a `active` y setea `user_id` y `activated_at`.
- `POST /api/admin/devices`: requiere Bearer token y `role=admin`; crea un device `pending_activation`.
- `GET /api/public/devices/{public_id}/activation-status`: no requiere autenticacion y responde `200` solo para devices `pending_activation`.

`public_id` no es secuencial, no expone el UUID interno completo y no contiene datos medicos. `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` no se exponen por API.

## First Scan Activation Foundation

Flujo de negocio objetivo:

- ProtegID vendera identificadores fisicos con QR impreso y NFC grabado.
- QR/NFC apuntan a `/p/{public_id}`.
- `public_id` es publico.
- `claim_code` es privado y viene dentro del empaque fisico.
- `claim_code` no va en QR/NFC, no va en URL, no debe loguearse y no debe guardarse en texto plano.

Servicio backend:

- `generate_claim_code()` genera formato `XXXX-XXXX-XXXX` con caracteres no ambiguos y `secrets`.
- `normalize_claim_code()` acepta codigo con o sin guiones.
- `hash_claim_code()` reutiliza `hash_password()`.
- `verify_claim_code()` reutiliza `verify_password()`.

Endpoint publico de estado:

```bash
curl http://localhost:8000/api/public/devices/PID-XXXXXXXXXX/activation-status
```

- Para `pending_activation`: `200 OK` con `public_id`, `activation_required` y `status`.
- Para `active`, `disabled`, `lost` o inexistente: `404` generico.
- No revela owner, `user_id`, `claim_code_hash`, `claimed_at`, `claim_attempts`, `claim_locked_until`, datos medicos ni perfil.

Validacion esperada:

```bash
python3 -m py_compile apps/api/app/models/device.py apps/api/app/services/claim_codes.py apps/api/app/api/public_devices.py apps/api/app/main.py apps/api/app/schemas/device.py
docker compose exec -T protegid-api alembic upgrade head
```

- `GET /api/public/devices/{public_id}/activation-status` con `pending_activation` debe responder `200`.
- `GET /api/public/devices/{public_id}/activation-status` con `active` debe responder `404`.
- `GET /api/public/devices/{public_id}/activation-status` con `disabled` debe responder `404`.
- `GET /api/public/devices/{public_id}/activation-status` con `lost` debe responder `404`.
- `GET /api/public/devices/{public_id}/activation-status` con inexistente debe responder `404`.

Limites actuales: `POST /api/devices/activate` aun no exige `claim_code`, no existe UI first-scan en `/p/{public_id}`, no existe registro de usuario final desde primer escaneo, no existe provisionamiento masivo con export de `claim_code`, no hay rate limit completo aplicado al endpoint de claim y no hay auditoria formal de intentos.

## Public Profile Foundation

La API incluye la base de perfiles publicos de emergencia:

- Modelo `EmergencyProfile`.
- Tabla `emergency_profiles`.
- Relacion unica `emergency_profiles.device_id -> devices.id`.

Endpoints protegidos:

- `GET /api/devices/{device_id}/emergency-profile`: requiere Bearer token, valida ownership del device y devuelve el perfil completo del dueno.
- `PUT /api/devices/{device_id}/emergency-profile`: requiere Bearer token, valida ownership del device y crea o actualiza el perfil.

Endpoint publico:

- `GET /api/public/profiles/{public_id}`: no requiere autenticacion y devuelve solo campos publicos del perfil.

Reglas del endpoint publico:

- Busca por `Device.public_id`.
- Solo responde si `device.status == "active"`.
- Solo responde si `emergency_profile.is_public == true`.
- Solo responde si `emergency_profile.deleted_at is null`.
- No expone `id`, `device_id`, `created_at`, `updated_at` ni `deleted_at`.

## Public Profile Frontend

La ruta publica frontend `/p/{public_id}` muestra la ficha de emergencia asociada al `public_id`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

- No requiere login.
- Renderiza server-side.
- Consulta `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si no existe o no esta disponible, responde `404` real usando `notFound()`.
- No expone IDs internos, `device_id`, timestamps ni `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El 404 no revela si el `public_id` existe o no.
- La vista es mobile-first y usa formato de ficha de emergencia.
- Tipo de sangre, contacto y telefono de emergencia aparecen destacados.
- Los campos vacios se muestran como `No informado`.
- `/p/{public_id}` incluye enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real y permite volver al inicio sin revelar si el `public_id` existe.

## Home y Navegacion Frontend

La ruta `/` funciona como landing inicial del MVP.

- Incluye accesos a `/login` y `/dashboard`.
- Explica el flujo: activar identificador, completar perfil de emergencia y compartir acceso publico mediante QR/NFC.
- Muestra el estado actual del MVP: login temporal, dashboard privado, perfil publico por `public_id` y QR generado hacia `/p/{public_id}`.
- Incluye nota: `Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.`
- `/login` y `/dashboard` tienen enlace `Volver al inicio`.
- `/p/{public_id}` tiene enlace discreto a inicio mediante `ProtegID`.

## Private Profile Management Frontend

La ruta `/login` contiene la primera version del login frontend. La ruta `/dashboard` contiene el dashboard privado para gestion de perfiles de emergencia.

Estado actual:

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- Si el login es correcto, recibe `access_token` y `token_type`.
- `/login` guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token`.
- `/login` muestra el token en `textarea` readonly por transparencia temporal del MVP.
- `/login` detecta sesion temporal existente desde `sessionStorage`, muestra `Ya existe una sesión temporal activa.`, permite ir a `/dashboard` y permite cerrar la sesion temporal.
- Despues de login exitoso muestra `Continuar al dashboard` sin redireccion automatica.
- `/login` muestra estados de carga, exito y error; `401` muestra credenciales invalidas.
- `/dashboard` lee automaticamente el token desde `sessionStorage` con `getSessionToken()`.
- `/dashboard` valida sesion contra `GET /api/auth/me`.
- Si la sesion es valida, carga dispositivos con `GET /api/devices`.
- Permite activar/asociar un identificador fisico desde `Activar identificador` con `POST /api/devices/activate`.
- Si no hay sesion, muestra estado no autenticado y boton/link `Ir a login`.
- Mantiene fallback tecnico reducido como `Usar token manual` para pegar token manualmente.
- Tiene boton `Cerrar sesion` que limpia `sessionStorage` con `clearSessionToken()`.
- Permite seleccionar un dispositivo.
- Carga el perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Permite crear o actualizar el perfil con `PUT /api/devices/{device_id}/emergency-profile`.

Campos disponibles del perfil:

- `display_name`
- `blood_type`
- `allergies`
- `medical_conditions`
- `medications`
- `emergency_contact_name`
- `emergency_contact_phone`
- `emergency_contact_relationship`
- `notes`
- `is_public`

`is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.

Seguridad de esta version:

- Es una sesion temporal para MVP.
- El token se guarda en `sessionStorage`.
- No se guarda en `localStorage`.
- No se guarda en cookies.
- No se implemento refresh token.
- No se implemento middleware de proteccion.
- No hay expiracion/renovacion automatica desde frontend.
- Los endpoints privados siguen protegidos por Bearer token.
- El token vive solo durante la sesion/pestana del navegador.
- `sessionStorage` no se comparte entre pestanas.
- Para produccion se evaluara una estrategia mas robusta.

UX actual: `/login` con estados de carga, exito y error, deteccion de sesion temporal existente, cierre de sesion temporal y continuidad manual al dashboard. `/dashboard` esta organizado en estado de sesion, activacion de identificador, dispositivos, editor de perfil y fallback tecnico. Los dispositivos muestran `public_id`, estado legible, descripcion operacional y seleccion. El editor agrupa Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica.

## Device Activation UX

Sprint 12 agrega activacion de identificadores desde `/dashboard`.

- Se usa el formulario `Activar identificador`.
- El input recibe `public_id` con placeholder `PID-XXXXXXXXXX`.
- El `public_id` puede estar impreso o asociado al QR/NFC fisico.
- El `public_id` no contiene datos medicos.
- La UI recomienda verificar fisicamente el identificador antes de activarlo.
- El boton muestra `Activar identificador` y durante la solicitud `Activando...`.
- Si activa correctamente muestra `Identificador activado correctamente.`.
- La lista `Mis dispositivos` se refresca o actualiza despues de activar.
- El dashboard mantiene perfil, QR, generacion, descarga y edicion.
- El cliente frontend es `activateDevice(publicId, accessToken): Promise<Device>` en `apps/web/lib/devices.ts`.
- El cliente usa `buildApiUrl` y maneja errores controlados `400`, `401` y `404`.

Endpoint usado por la UI:

```bash
curl -X POST http://localhost:8000/api/devices/activate \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"public_id":"PID-XXXXXXXXXX"}'
```

Validacion esperada de activacion:

- `GET /dashboard` debe responder `200 OK`.
- Prueba GUI: iniciar sesion, ir a `/dashboard`, ingresar un `public_id` pendiente, activar identificador, ver `Identificador activado correctamente.` y confirmar que aparece en `Mis dispositivos` como `Activo`.
- No hay scanner QR, lectura NFC, camara, geolocalizacion, tracking, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend ni creacion admin de devices desde frontend.
- El backend sigue siendo la fuente de autorizacion.

Validacion esperada:

```bash
docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"
```

- `GET /login` debe responder `200 OK`.
- `GET /dashboard` debe responder `200 OK`.
- `GET /` debe responder `200 OK`.
- `GET /p/PID-G2NYZP87KA` debe responder `200 OK`.
- `GET /p/PID-AAAAAAAAAA` debe responder `404 Not Found`.
- Prueba GUI: login con usuario de prueba, confirmar `protegid_access_token` en `sessionStorage`, abrir `/dashboard` en la misma pestana, confirmar carga automatica de usuario/devices y cerrar sesion.
- Prueba GUI de activacion: ingresar un `public_id` pendiente en `Activar identificador`, activar y confirmar `Identificador activado correctamente.`.
- Usuario admin: ve estado QR y puede generar/regenerar QR desde `/dashboard`.
- Usuario no admin: ve `La gestión de QR requiere rol admin.` y el dashboard sigue mostrando devices/perfil.

## QR Foundation

La API incluye la base de QR:

- Dependencia `qrcode[pil]`.
- Generacion de QR PNG en memoria.
- Persistencia del PNG en MinIO/S3 compatible.
- Object key estable: `qr/devices/{public_id}.png`.

El QR no contiene datos medicos. El QR contiene solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`.

Endpoints admin:

- `GET /api/admin/devices/{device_id}/qr`: requiere Bearer token y `role=admin`; devuelve metadata y `exists`.
- `POST /api/admin/devices/{device_id}/qr`: requiere Bearer token y `role=admin`; genera/sube el QR y devuelve metadata.
- `GET /api/admin/devices/{device_id}/qr/download`: requiere Bearer token y `role=admin`; descarga el PNG existente.

La metadata incluye `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`. La descarga busca el device por `device_id`, usa `qr/devices/{public_id}.png`, no genera QR automaticamente, devuelve `404` si no existe y responde `Content-Type: image/png` con `Content-Disposition: attachment; filename="{public_id}.png"` si existe. No se entrega presigned URL ni se expone MinIO.

## QR Management Frontend

Sprint 11 agrega gestion QR desde `/dashboard` con descarga controlada del PNG.

- El dashboard consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- El dashboard muestra `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`.
- El dashboard permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr` para usuarios admin.
- El dashboard permite descargar QR con el boton `Descargar QR`; durante la descarga muestra `Descargando QR...`.
- El cliente frontend usa `downloadDeviceQr(deviceId, accessToken): Promise<Blob>`.
- Si descarga correctamente muestra `QR descargado correctamente.`.
- Si el QR no existe muestra `Genera el QR antes de descargarlo.`.
- La descarga usa `URL.createObjectURL` y revoca el objeto temporal con `URL.revokeObjectURL`.
- Si no hay permisos, muestra `La gestión de QR requiere rol admin.` y no rompe la gestion de devices/perfil.
- El QR apunta a `/p/{public_id}` y solo contiene la URL publica del perfil.
- La visualizacion depende de que el perfil este marcado como publico.
- `object_key` se muestra como detalle tecnico.
- No hay presigned URLs, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones.

Validacion esperada para descarga QR:

- `GET /api/admin/devices/{device_id}/qr/download` sin token responde `401`.
- `GET /api/admin/devices/{device_id}/qr/download` con usuario no admin responde `403`.
- `GET /api/admin/devices/{device_id}/qr/download` con admin y QR existente responde `200` con `Content-Type: image/png`.
- `GET /dashboard` responde `200 OK`.
- Prueba GUI: admin puede descargar `PID-XXXXXXXXXX.png` y QR inexistente muestra ayuda para generarlo antes.

Limites actuales: no hay registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR, presigned URL publica, UI first-scan, activacion obligatoria con `claim_code`, provisionamiento masivo con export de `claim_code`, rate limit completo para claim ni auditoria formal de intentos.
