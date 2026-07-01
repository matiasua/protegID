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
- Login frontend: `http://localhost:8080/login`
- Registro frontend: `http://localhost:8080/register`
- Dashboard privado: `http://localhost:8080/dashboard`
- Perfil publico frontend: `http://localhost:8080/p/PID-XXXXXXXXXX`
- API healthcheck: `http://localhost:8080/api/health`
- API readiness: `http://localhost:8080/api/ready`
- Auth register: `http://localhost:8080/api/auth/register`
- Auth login: `http://localhost:8080/api/auth/login`
- Auth verify email: `http://localhost:8080/api/auth/verify-email`
- Auth resend verification: `http://localhost:8080/api/auth/resend-verification`
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
- Mailpit UI: `http://localhost:8025`

## Sesiones Seguras Locales

El flujo local recomendado es entrar por Nginx en `http://localhost:8080` para que web y API sean same-origin.

Auth actual:

- `POST /api/auth/login` setea `protegid_session` HttpOnly y `protegid_csrf`, y devuelve `user`; no devuelve tokens.
- `POST /api/auth/register` crea usuario no verificado, no inicia sesion y envia correo de verificacion.
- `POST /api/auth/verify-email` es publico y no requiere CSRF.
- `POST /api/auth/resend-verification` requiere sesion y CSRF.
- `GET /api/auth/me` usa cookie de sesion.
- `POST /api/auth/logout` requiere `X-CSRF-Token`, revoca la sesion y borra cookies.
- Endpoints privados usan cookie de sesion; no usan `Authorization Bearer`.
- Metodos mutantes con sesion requieren CSRF double-submit.

Variables locales en `.env.example`:

- `SESSION_COOKIE_NAME=protegid_session`
- `SESSION_COOKIE_SECURE=false`
- `SESSION_COOKIE_SAMESITE=lax`
- `SESSION_COOKIE_PATH=/`
- `SESSION_ABSOLUTE_TTL_SECONDS=604800`
- `SESSION_TOKEN_BYTES=32`
- `SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS=300`
- `CSRF_COOKIE_NAME=protegid_csrf`
- `CSRF_HEADER_NAME=X-CSRF-Token`
- `CSRF_TOKEN_BYTES=32`

Produccion debe usar HTTPS, `SESSION_COOKIE_SECURE=true`, `SESSION_COOKIE_NAME=__Host-protegid_session`, `Path=/`, sin `Domain`, y web/API bajo mismo dominio u origen siempre que sea posible.

## Mailpit y Verificacion de Email Local

Mailpit corre dentro de Docker Compose para simular recepcion de correos de verificacion.

- UI web: `http://localhost:8025`.
- SMTP interno para `protegid-api`: `mailpit:1025`.
- Variables locales: `EMAIL_DELIVERY_MODE=smtp`, `SMTP_HOST=mailpit`, `SMTP_PORT=1025`, `SMTP_FROM_EMAIL=no-reply@protegid.local`, `SMTP_FROM_NAME=ProtegID`, `MAILPIT_SMTP_PORT=1025`, `MAILPIT_WEB_PORT=8025`.

Flujo local recomendado:

```bash
docker compose up -d
docker compose exec -T protegid-api alembic upgrade head
curl http://localhost:8080/api/health
curl http://localhost:8080/api/ready
```

Luego abrir `http://localhost:8025`, registrar un usuario y usar el link `/verify-email?token=...` recibido.

No usar dominios `.test` en usuarios seed porque `EmailStr` los rechaza como dominio reservado. Usar `@protegid.cl` para usuarios locales.

## Variables JWT Legadas

Estas variables pueden existir por legado tecnico JWT, pero el flujo web actual no emite ni valida tokens Bearer:

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

`GET /api/auth/me` requiere cookie de sesion valida.

`POST /api/auth/register` recibe `{ "email": "usuario@example.com", "password": "Password123!", "full_name": "Nombre Usuario" }`, devuelve `RegisterResponse`, no devuelve token y no inicia sesion automaticamente. El rol publico se fuerza a `user`, `password_hash` no se expone, email se normaliza con `strip().lower()` en registro/login, la busqueda por email es case-insensitive y duplicados con casing distinto responden `409`. Se captura `IntegrityError` con rollback.

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

- `GET /api/devices`: requiere cookie de sesion y solo lista devices del usuario autenticado.
- `POST /api/devices/activate`: requiere cookie de sesion, CSRF y body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`; valida `claim_code` contra `claim_code_hash`, activa/asocia un device `pending_activation` sin `user_id`, cambia `status` a `active`, setea `user_id`, `activated_at` y `claimed_at`, resetea `claim_attempts` y limpia `claim_locked_until`.
- `POST /api/admin/devices`: requiere cookie de sesion, CSRF y `role=admin`; crea un device `pending_activation`.
- `GET /api/public/devices/{public_id}/activation-status`: no requiere autenticacion y responde `200` solo para devices `pending_activation`.

`public_id` no es secuencial, no expone el UUID interno completo y no contiene datos medicos. `claim_code`, `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` no se exponen por API.

## First Scan Activation Foundation

Flujo de negocio objetivo:

- ProtegID vendera identificadores fisicos con QR impreso y NFC grabado.
- QR/NFC apuntan a `/p/{public_id}`.
- `public_id` es publico.
- `claim_code` es privado y viene dentro del empaque fisico.
- `claim_code` no va en QR/NFC, no va en URL, no debe loguearse y no debe guardarse en texto plano.
- `claim_code` se valida contra `claim_code_hash` en `POST /api/devices/activate`.
- `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` no se exponen por API.
- `claim_code` y `claim_code_hash` no deben loguearse.

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

Activacion privada:

```bash
curl -X POST http://localhost:8000/api/devices/activate \
  -H 'Cookie: protegid_session=<cookie>; protegid_csrf=<csrf>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  -d '{"public_id":"PID-XXXXXXXXXX","claim_code":"XXXX-XXXX-XXXX"}'
```

- Requiere cookie de sesion, CSRF, `public_id` valido y `claim_code` valido.
- Solo activa devices `pending_activation`, sin `user_id` y con `claim_code_hash` existente.
- Errores esperados: `401` sin token, `422` sin `claim_code`, `422` con `public_id` invalido, `404 Identifier not available` para inexistente/no disponible/ya activo/asociado, `400 Identifier cannot be activated` sin `claim_code_hash`, `400 Invalid activation data` con codigo incorrecto y `429 Too many activation attempts. Try again later.` durante bloqueo.
- Proteccion anti fuerza bruta: `MAX_CLAIM_ATTEMPTS = 5`, `CLAIM_LOCK_MINUTES = 15`; cada codigo incorrecto incrementa `claim_attempts`, el quinto setea `claim_locked_until`, y una activacion correcta resetea `claim_attempts` y limpia `claim_locked_until`.

Validacion esperada:

```bash
python3 -m py_compile apps/api/app/api/devices.py apps/api/app/schemas/device.py
docker compose exec -T protegid-api alembic upgrade head
```

- `GET /api/public/devices/{public_id}/activation-status` con `pending_activation` debe responder `200`.
- `GET /api/public/devices/{public_id}/activation-status` con `active` debe responder `404`.
- `GET /api/public/devices/{public_id}/activation-status` con `disabled` debe responder `404`.
- `GET /api/public/devices/{public_id}/activation-status` con `lost` debe responder `404`.
- `GET /api/public/devices/{public_id}/activation-status` con inexistente debe responder `404`.

Limites actuales: el registro de usuario final desde primer escaneo existe, pero no inicia sesion automaticamente; el usuario debe iniciar sesion antes de reclamar. No existe scanner QR, no existe lectura NFC real desde navegador, no existe provisionamiento masivo con export de `claim_code` y no hay auditoria formal de intentos.

## Public Profile Foundation

La API incluye la base de perfiles publicos de emergencia:

- Modelo `EmergencyProfile`.
- Tabla `emergency_profiles`.
- Relacion unica `emergency_profiles.device_id -> devices.id`.

Endpoints protegidos:

- `GET /api/devices/{device_id}/emergency-profile`: requiere cookie de sesion, valida ownership del device y devuelve el perfil completo del dueno.
- `PUT /api/devices/{device_id}/emergency-profile`: requiere cookie de sesion y CSRF, valida ownership del device y crea o actualiza el perfil.
- `GET /api/devices/{device_id}/emergency-profile/readiness`: requiere cookie de sesion, valida ownership y devuelve readiness sin valores medicos.

Endpoint publico:

- `GET /api/public/profiles/{public_id}`: no requiere autenticacion y devuelve solo campos publicos del perfil.

Reglas del endpoint publico:

- Busca por `Device.public_id`.
- Solo responde si `readiness.is_public_operational == true`.
- Esto exige device `active`, `device.deleted_at is null`, profile existente, `profile.deleted_at is null`, campos minimos completos, consentimiento vigente e `is_public=true`.
- Si no cumple, responde `404` generico.
- No expone `id`, `device_id`, `user_id`, `is_public`, flags `*_none`, consentimiento, `created_at`, `updated_at` ni `deleted_at`.

## Public Profile Frontend

La ruta publica frontend `/p/{public_id}` muestra la ficha de emergencia asociada al `public_id` o el onboarding de primer escaneo cuando el identificador esta pendiente. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

- No requiere login.
- Renderiza server-side.
- Consulta `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si no existe perfil publico, consulta `GET /api/public/devices/{public_id}/activation-status` mediante `getPublicDeviceActivationStatus(publicId)`.
- Si `activation-status` responde `pending_activation`, muestra onboarding `Identificador ProtegID no activado`.
- Si `activation-status` responde `404`, mantiene `404` real o mensaje generico usando `notFound()`.
- No expone IDs internos, `device_id`, timestamps ni `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El 404 no revela si el `public_id` existe o no.
- La vista es mobile-first y usa formato de ficha de emergencia.
- Tipo de sangre, contacto y telefono de emergencia aparecen destacados.
- Los campos vacios se muestran como `No informado`.
- `/p/{public_id}` incluye enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real y permite volver al inicio sin revelar si el `public_id` existe.

## First Scan Onboarding Frontend

Flujo local esperado:

- QR/NFC apuntan a `/p/{public_id}`.
- Si existe perfil publico, se muestra la ficha publica.
- Si no existe perfil publico y `activation-status` responde `pending_activation`, se muestra onboarding publico.
- `apps/web/lib/public-devices.ts` expone `getPublicDeviceActivationStatus(publicId)`.
- El cliente publico retorna estado en `200`, retorna `null` en `404`, no usa token, no envia `Authorization` y no maneja `claim_code`.
- El onboarding indica que el identificador fisico aun no esta vinculado, que el `claim_code` viene dentro del empaque fisico y que el QR/NFC solo contiene la URL publica permanente.
- Muestra `public_id` como referencia tecnica discreta.
- Sin sesion, `apps/web/app/p/[publicId]/activation-form.tsx` muestra CTA `Iniciar sesión`.
- Sin sesion, Login apunta a `/login?returnTo=/p/{public_id}` y Crear cuenta apunta a `/register?returnTo=/p/{public_id}`.
- Con sesion por cookie, permite ingresar `claim_code` y llama `activateDeviceWithClaimCode(publicId, claimCode)` con CSRF.
- La activacion envia `POST /api/devices/activate` con body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`.
- En exito muestra `Identificador vinculado correctamente.` y CTA `Completar perfil de emergencia` hacia `/dashboard?publicId={public_id}`.

Flujo GUI esperado: `/p/{public_id}` -> `/register?returnTo=/p/{public_id}` -> `/login?returnTo=/p/{public_id}` -> `/p/{public_id}` -> `claim_code` -> `/dashboard?publicId={public_id}` -> completar perfil.

## Home y Navegacion Frontend

La ruta `/` funciona como landing inicial del MVP.

- Incluye accesos a `/login` y `/dashboard`.
- Explica el flujo: activar identificador, completar perfil de emergencia y compartir acceso publico mediante QR/NFC.
- Muestra el estado actual: login con cookie HttpOnly, dashboard privado, perfil publico por `public_id` y QR generado hacia `/p/{public_id}`.
- Incluye nota: `Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.`
- `/login` y `/dashboard` tienen enlace `Volver al inicio`.
- `/p/{public_id}` tiene enlace discreto a inicio mediante `ProtegID`.

## Private Profile Management Frontend

La ruta `/login` contiene la primera version del login frontend. La ruta `/dashboard` contiene el dashboard privado para gestion de perfiles de emergencia.

Estado actual:

- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- `/register` permite crear cuenta con Nombre, Email y Password; consume `POST /api/auth/register`, envia `full_name`, no guarda token, no usa storage y limpia password tras registro exitoso.
- `/register` muestra `Ya existe una cuenta con este correo.` ante `409`.
- `/register` y `/login` soportan `returnTo` sanitizado; solo aceptan rutas internas seguras.
- Tras login exitoso, `/login` redirige automaticamente con `router.replace()` al `returnTo` seguro o `/dashboard`.
- Si el login es correcto, el backend setea cookies y no devuelve tokens.
- `/login` no guarda tokens en storage ni muestra tokens.
- `/login` detecta sesion activa contra `/api/auth/me` y redirige automaticamente al destino seguro.
- `/login` muestra estados de carga, exito y error; `401` muestra credenciales invalidas.
- `/dashboard` valida sesion contra `GET /api/auth/me` usando cookie.
- Si la sesion es valida, carga dispositivos con `GET /api/devices`.
- Permite activar/asociar un identificador fisico desde `Activar identificador` con `public_id`, `claim_code` y `POST /api/devices/activate`.
- Si no hay sesion, muestra estado no autenticado y boton/link `Ir a login`.
- No mantiene fallback de token manual.
- Tiene boton `Cerrar sesion` que llama `POST /api/auth/logout` con CSRF.
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

`is_public` expresa intencion de publicacion; el backend solo publica si readiness y consentimiento vigente permiten operacion.

Seguridad de esta version:

- Usa cookie HttpOnly de sesion server-side.
- Usa CSRF double-submit para metodos mutantes con sesion.
- No guarda tokens de auth en `sessionStorage` ni `localStorage`.
- No envia `Authorization Bearer` desde frontend.
- No se implemento refresh token.
- No hay expiracion/renovacion automatica desde frontend.
- Para produccion se debe usar HTTPS, `Secure=true`, prefijo `__Host-`, `Path=/` y sin `Domain`.

UX actual: `/login` con estados de carga, exito y error, deteccion de sesion activa y redireccion automatica segura. `/dashboard` esta organizado en estado de sesion, activacion de identificador, dispositivos y editor de perfil. Los dispositivos muestran `public_id`, estado legible, descripcion operacional y seleccion. El editor agrupa Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica.

## Device Activation UX

Sprint 12 agrega activacion de identificadores desde `/dashboard`; Sprint 14 cambia el backend para exigir `public_id + claim_code`.

- Se usa el formulario `Activar identificador`.
- El input recibe `public_id` con placeholder `PID-XXXXXXXXXX`.
- El formulario tambien recibe `claim_code` con placeholder `XXXX-XXXX-XXXX`.
- El `public_id` puede estar impreso o asociado al QR/NFC fisico.
- El `public_id` no contiene datos medicos.
- La UI recomienda verificar fisicamente el identificador antes de activarlo.
- El boton muestra `Activar identificador` y durante la solicitud `Activando...`.
- Si activa correctamente muestra `Identificador vinculado correctamente.`.
- La lista `Mis dispositivos` se refresca o actualiza despues de activar.
- El dashboard mantiene perfil, QR, generacion, descarga y edicion.
- El cliente frontend es `activateDeviceWithClaimCode(publicId, claimCode): Promise<Device>` en `apps/web/lib/devices.ts`.
- El cliente usa `buildApiUrl` y maneja errores controlados `400`, `401`, `404`, `422` y `429`.
- El dashboard limpia `claim_code` del estado despues del envio y no lo guarda en storage.

Endpoint usado por la UI:

```bash
curl -X POST http://localhost:8000/api/devices/activate \
  -H 'Cookie: protegid_session=<cookie>; protegid_csrf=<csrf>' \
  -H 'X-CSRF-Token: <csrf>' \
  -H 'Content-Type: application/json' \
  -d '{"public_id":"PID-XXXXXXXXXX","claim_code":"XXXX-XXXX-XXXX"}'
```

Validacion esperada de activacion:

- `GET /dashboard` debe responder `200 OK`.
- Prueba HTTP backend: enviar `public_id + claim_code` validos y confirmar `200`, `status=active`, `user_id`, `activated_at` y `claimed_at`.
- Prueba GUI: ingresar `public_id + claim_code` validos en `/dashboard`, activar y confirmar `Identificador vinculado correctamente.`.
- No hay scanner QR, lectura NFC, camara, geolocalizacion, tracking, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend ni creacion admin de devices desde frontend.
- El backend sigue siendo la fuente de autorizacion.

Validacion esperada:

```bash
docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"
```

- `GET /login` debe responder `200 OK`.
- `GET /dashboard` debe responder `200 OK`.
- `GET /` debe responder `200 OK`.
- `GET /p/{public_id_pending}` debe responder `200 OK` y mostrar onboarding.
- `GET /p/PID-G2NYZP87KA` debe responder `200 OK`.
- `GET /p/PID-AAAAAAAAAA` debe responder `404 Not Found`.
- Prueba GUI: login con usuario de prueba, confirmar cookies `protegid_session` HttpOnly y `protegid_csrf`, abrir/refrescar `/dashboard`, confirmar carga automatica de usuario/devices y cerrar sesion.
- Prueba GUI de onboarding: sin sesion muestra CTA login; con sesion muestra formulario `claim_code`; `claim_code` correcto activa device; `claim_code` incorrecto muestra error controlado.
- Prueba GUI de dashboard: activar con `public_id + claim_code` y confirmar que `claim_code` no queda en storage.
- Usuario admin: ve estado QR y puede generar/regenerar QR desde `/dashboard`.
- Usuario no admin: no ve Gestion QR, generar, regenerar, descargar QR, `object_key` ni mensaje de permisos QR.
- Admin: mantiene Gestion QR.

## QR Foundation

La API incluye la base de QR:

- Dependencia `qrcode[pil]`.
- Generacion de QR PNG en memoria.
- Persistencia del PNG en MinIO/S3 compatible.
- Object key estable: `qr/devices/{public_id}.png`.

El QR no contiene datos medicos. El QR contiene solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`.

Endpoints admin:

- `GET /api/admin/devices/{device_id}/qr`: requiere cookie de sesion y `role=admin`; devuelve metadata y `exists`.
- `POST /api/admin/devices/{device_id}/qr`: requiere cookie de sesion, CSRF y `role=admin`; genera/sube el QR y devuelve metadata.
- `GET /api/admin/devices/{device_id}/qr/download`: requiere cookie de sesion y `role=admin`; descarga el PNG existente.

La metadata incluye `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`. La descarga busca el device por `device_id`, usa `qr/devices/{public_id}.png`, no genera QR automaticamente, devuelve `404` si no existe y responde `Content-Type: image/png` con `Content-Disposition: attachment; filename="{public_id}.png"` si existe. No se entrega presigned URL ni se expone MinIO.

## QR Management Frontend

Sprint 11 agrega gestion QR desde `/dashboard` con descarga controlada del PNG.

- El dashboard consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- El dashboard muestra `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`.
- El dashboard permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr` para usuarios admin.
- El dashboard permite descargar QR con el boton `Descargar QR`; durante la descarga muestra `Descargando QR...`.
- El cliente frontend usa `downloadDeviceQr(deviceId): Promise<Blob>`.
- Si descarga correctamente muestra `QR descargado correctamente.`.
- Si el QR no existe muestra `Genera el QR antes de descargarlo.`.
- La descarga usa `URL.createObjectURL` y revoca el objeto temporal con `URL.revokeObjectURL`.
- Para usuarios no-admin, `/dashboard` oculta Gestion QR y no muestra mensaje de permisos QR.
- El QR apunta a `/p/{public_id}` y solo contiene la URL publica del perfil.
- La visualizacion depende de que el perfil este operativo segun readiness.
- `object_key` se muestra solo como detalle tecnico administrativo.
- No hay presigned URLs, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones.

Validacion esperada para descarga QR:

- `GET /api/admin/devices/{device_id}/qr/download` sin token responde `401`.
- `GET /api/admin/devices/{device_id}/qr/download` con usuario no admin responde `403`.
- `GET /api/admin/devices/{device_id}/qr/download` con admin y QR existente responde `200` con `Content-Type: image/png`.
- `GET /dashboard` responde `200 OK`.
- Prueba GUI: admin puede descargar `PID-XXXXXXXXXX.png` y QR inexistente muestra ayuda para generarlo antes.

Limites actuales: no hay validacion estricta de telefono internacional, wizard profesional multi-vista para perfil, recuperacion de password, refresh token, MFA, captcha, proteccion anti-bot, roles avanzados en frontend, expiracion visual previa de la sesion, auditoria formal de eventos criticos, historial/versionado completo de consentimientos, segundo contacto de emergencia, normalizacion avanzada de datos medicos, hardening de rate limiting publico, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC real desde navegador, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR, presigned URL publica ni provisionamiento masivo con export de `claim_code`. Registro no inicia sesion automaticamente y roles siguen siendo strings.
