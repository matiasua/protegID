# ProtegID

ProtegID es una plataforma MVP para identificadores fisicos de emergencia con QR + NFC. Este repositorio contiene el monorepo con frontend Next.js, backend FastAPI y servicios locales base.

## Stack

- Frontend: Next.js + TypeScript + Tailwind CSS + shadcn/ui
- Backend: FastAPI + Python
- DB: PostgreSQL
- Queue/cache: Redis
- Worker: Python
- Archivos: MinIO compatible S3
- Reverse proxy: Nginx
- Entorno local: Docker Compose

## Estructura

```text
apps/
  web/        Frontend Next.js.
  api/        API FastAPI y worker Python base.
infra/
  nginx/      Reverse proxy local.
  scripts/    Espacio para scripts de infraestructura.
docs/         Arquitectura, desarrollo local, seguridad y reglas para IA.
```

## Servicios locales

- `protegid-web`
- `protegid-api`
- `protegid-worker`
- `protegid-db`
- `protegid-redis`
- `protegid-minio`
- `protegid-nginx`

## Primer uso

```bash
cp .env.example .env
make up
```

La aplicacion queda disponible en:

- Home / landing MVP via Nginx: `http://localhost:8080`
- Login frontend temporal: `http://localhost:8080/login`
- Registro frontend: `http://localhost:8080/register`
- Dashboard privado temporal: `http://localhost:8080/dashboard`
- Perfil publico frontend: `http://localhost:8080/p/PID-XXXXXXXXXX`
- API healthcheck via Nginx: `http://localhost:8080/api/health`
- API readiness via Nginx: `http://localhost:8080/api/ready`
- MinIO console: `http://localhost:9001`

## Comandos

```bash
make up       # Levanta el entorno local
make down     # Detiene los servicios
make logs     # Muestra logs de todos los servicios
make ps       # Lista servicios
make build    # Construye imagenes
```

Para validar el build del frontend sin reutilizar los artefactos `.next` del contenedor de desarrollo:

```bash
docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"
```

Evitar ejecutar `npm run build` dentro del contenedor dev vivo si puede mezclar artefactos. En desarrollo, Next usa `.next-dev`; en build, usa `.next`.

## Home / Landing MVP

La ruta `/` funciona como landing inicial del MVP de ProtegID.

- Presenta ProtegID como identificadores fisicos de emergencia con QR y NFC.
- Incluye acceso directo a `/login` mediante `Iniciar sesion`.
- Incluye acceso directo a `/dashboard` mediante `Ir al dashboard`.
- Explica el flujo principal: activar identificador, completar perfil de emergencia y compartir acceso publico mediante QR/NFC.
- Muestra el estado actual del MVP: login temporal, dashboard privado, perfil publico por `public_id` y QR generado hacia `/p/{public_id}`.
- Incluye la nota de alcance: `Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.`

## Perfil Publico Frontend

La ruta publica frontend `/p/{public_id}` ya existe. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

- La pagina no requiere login.
- Consulta server-side `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK` y renderiza una ficha de emergencia.
- Si no existe perfil publico, consulta `GET /api/public/devices/{public_id}/activation-status` mediante `getPublicDeviceActivationStatus(publicId)` en `apps/web/lib/public-devices.ts`.
- Si `activation-status` responde `pending_activation`, muestra onboarding publico con titulo `Identificador ProtegID no activado`.
- Si `activation-status` retorna `404`, mantiene `404` real o mensaje generico usando `notFound()`.
- No expone IDs internos, `device_id`, timestamps ni `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El estado 404 no revela si el `public_id` existe o no.
- La vista es mobile-first, destaca tipo de sangre, contacto y telefono de emergencia.
- Los campos vacios se muestran como `No informado`.
- `/p/{public_id}` incluye un enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.

## First Scan Onboarding Frontend

Sprint 15 agrega el flujo frontend de primer escaneo sobre la URL publica permanente `/p/{public_id}`. Sprint 16 conecta ese onboarding con registro de usuario final, login y retorno al identificador.

- El QR/NFC apunta a `/p/{public_id}` y solo contiene esa URL publica permanente.
- Si existe perfil publico, `/p/{public_id}` mantiene la ficha publica.
- Si no existe perfil publico, el frontend consulta `GET /api/public/devices/{public_id}/activation-status`.
- El cliente publico vive en `apps/web/lib/public-devices.ts` y expone `getPublicDeviceActivationStatus(publicId)`.
- `getPublicDeviceActivationStatus(publicId)` retorna estado de activacion en `200`, retorna `null` en `404`, no usa token, no envia `Authorization` y no maneja `claim_code`.
- Si el estado es `pending_activation`, `/p/{public_id}` muestra `Identificador ProtegID no activado`.
- El onboarding indica que el identificador fisico aun no esta vinculado a una cuenta.
- Indica que el codigo de activacion viene dentro del empaque fisico.
- Indica que el QR/NFC solo contiene la URL publica permanente del identificador.
- Muestra `public_id` como referencia tecnica discreta.
- Si no hay sesion temporal, muestra CTA `Iniciar sesión` hacia `/login?returnTo=/p/{public_id}`.
- Si no hay sesion temporal, muestra CTA `Crear cuenta` hacia `/register?returnTo=/p/{public_id}`.
- Si hay sesion temporal, `apps/web/app/p/[publicId]/activation-form.tsx` permite ingresar `claim_code`.
- El formulario usa `getSessionToken()` y llama `activateDeviceWithClaimCode(publicId, claimCode, accessToken)`.
- La activacion envia `POST /api/devices/activate` con body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`.
- En exito muestra `Identificador vinculado correctamente.`.
- El CTA posterior es `Completar perfil de emergencia` y apunta a `/dashboard?publicId={public_id}`.
- `/dashboard?publicId={public_id}` selecciona automaticamente el dispositivo si pertenece al usuario y carga el editor de perfil.

Flujo esperado de usuario final:

- `/p/{public_id}`.
- `/register?returnTo=/p/{public_id}`.
- `/login?returnTo=/p/{public_id}`.
- `/p/{public_id}`.
- Ingreso de `claim_code`.
- Identificador vinculado.
- `/dashboard?publicId={public_id}`.
- Completar perfil de emergencia y marcarlo publico si corresponde.

## Auth Frontend Foundation

La primera version del login frontend y sesion temporal existe.

- Ruta frontend de login: `/login`.
- Ruta frontend de registro: `/register`.
- Ruta privada: `/dashboard`.
- `/register` permite crear cuenta con Nombre, Email y Password.
- `/register` consume `POST /api/auth/register` mediante `register(payload)` y envia `full_name` al backend.
- El registro devuelve `UserRead`, no devuelve token y no inicia sesion automaticamente.
- `/register` no guarda token, no usa `localStorage` ni `sessionStorage`, y limpia el password tras registro exitoso.
- Si el backend responde `409`, `/register` muestra `Ya existe una cuenta con este correo.`.
- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- `/login` soporta `returnTo` y, despues de login exitoso, si `returnTo` valido existe muestra CTA `Continuar activación`.
- `/login` mantiene CTA `Continuar al dashboard`.
- `returnTo` se sanitiza: solo acepta rutas internas que empiezan con `/`, rechaza `//` y rechaza URLs absolutas `http://` o `https://`.
- `/login` tiene enlace `Volver al inicio`.
- `/login` detecta si ya existe `protegid_access_token` en `sessionStorage` y muestra `Ya existe una sesión temporal activa.`.
- Desde `/login` se puede ir a `/dashboard` o cerrar la sesion temporal con `clearSessionToken()` sin validar automaticamente contra backend.
- Si el login es correcto, recibe `access_token` y `token_type`.
- Guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token`.
- Muestra el token en un `textarea` readonly por transparencia temporal del MVP.
- Despues de login exitoso muestra `Continuar al dashboard` y no redirige automaticamente.
- `/login` muestra estados de carga, exito y error; `401` muestra credenciales invalidas.
- `/dashboard` tiene enlace `Volver al inicio`.
- `/dashboard` lee automaticamente el token con `getSessionToken()`.
- `/dashboard` valida sesion contra `GET /api/auth/me`.
- Si la sesion es valida, carga dispositivos con `GET /api/devices`.
- Permite activar/asociar un identificador fisico desde la seccion `Activar identificador` ingresando `public_id` y `claim_code`.
- Por cada dispositivo, consulta estado QR con `GET /api/admin/devices/{device_id}/qr`.
- Permite generar o regenerar QR desde la GUI con `POST /api/admin/devices/{device_id}/qr` cuando el usuario tiene `role=admin`.
- Permite seleccionar un dispositivo y cargar su perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Permite crear o actualizar el perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- Si no hay sesion, `/dashboard` muestra estado no autenticado y boton/link `Ir a login`.
- Mantiene fallback tecnico reducido como `Usar token manual` para pegar token manualmente.
- Tiene boton `Cerrar sesion` que limpia `sessionStorage` con `clearSessionToken()`.
- La sesion es temporal para MVP: usa `sessionStorage`, no `localStorage`, no cookies y no refresh token.
- No hay middleware de proteccion ni expiracion/renovacion automatica desde frontend.
- El backend sigue validando Bearer token en endpoints privados.
- El token vive solo durante la sesion/pestana del navegador y `sessionStorage` no se comparte entre pestanas.

Campos editables del perfil: `display_name`, `blood_type`, `allergies`, `medical_conditions`, `medications`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes` e `is_public`.

`is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.

## User Registration Flow

Sprint 16 habilita registro publico de usuario final desde primer escaneo.

Backend:

- `POST /api/auth/register` recibe body `{ "email": "usuario@example.com", "password": "Password123!", "full_name": "Nombre Usuario" }`.
- Devuelve `UserRead`; no devuelve token y no inicia sesion automaticamente.
- El rol publico se fuerza a `user`; no se permite registrar `admin` desde el endpoint publico.
- `password_hash` no se expone y el password no debe loguearse.
- El email se normaliza con `strip().lower()` al registrar y al autenticar.
- La busqueda por email es case-insensitive.
- Registro duplicado con casing distinto responde `409`.
- Se captura `IntegrityError` con rollback para evitar race condition del unique email.

Frontend:

- `/register` muestra formulario Nombre, Email y Password.
- Envia `full_name` al backend.
- No guarda password, token ni `claim_code`.
- No inicia sesion automaticamente.
- Soporta `returnTo` y enlaza a `/login?returnTo={returnTo}` si la ruta es interna valida.

Validacion cubierta:

- Registro con email mixto -> `201`.
- Email guardado en lowercase.
- Login con lowercase -> `200`.
- Login con casing mixto -> `200`.
- `GET /api/auth/me` -> `200`.
- Registro duplicado con casing distinto -> `409`.
- `password_hash` no expuesto.
- Rol creado como `user`.
- `GET /register` -> `200`.
- `GET /register?returnTo=/p/{public_id}` -> `200`.
- `GET /login?returnTo=/p/{public_id}` -> `200`.
- `returnTo` externo se descarta.
- Build frontend OK.

UX actual de `/dashboard`: validacion automatica si existe token temporal, secciones de estado de sesion, activacion de identificador, dispositivos, editor de perfil y fallback tecnico. Los dispositivos muestran `public_id`, estado legible, descripcion operacional, seleccion, gestion QR secundaria y boton claro `Editar perfil`. El editor agrupa campos en Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica. Mantiene `Guardar perfil`, `Cerrar sesion` y estados de carga, guardado, error y exito.

## Claim Code Activation Backend

Sprint 14 actualiza `POST /api/devices/activate`: ya no activa solo con `public_id`. Ahora requiere token Bearer y body `public_id + claim_code`.

- El `claim_code` viene dentro del empaque fisico.
- El `claim_code` no va en QR/NFC, URL, logs ni respuestas API.
- El `claim_code` no se guarda en texto plano; se valida contra `claim_code_hash`.
- `claim_code_hash`, `claim_attempts`, `claim_locked_until` y `claimed_at` no se exponen en `DeviceRead`.
- El backend sigue siendo la fuente de autorizacion.
- Solo se activa un device existente con `status == "pending_activation"`, sin `user_id` asignado y con `claim_code_hash` existente.
- Si la activacion es valida, el device pasa a `active`, se asigna `user_id`, se setean `activated_at` y `claimed_at`, `claim_attempts` vuelve a `0` y `claim_locked_until` queda `null`.
- Proteccion anti fuerza bruta: `MAX_CLAIM_ATTEMPTS = 5`, `CLAIM_LOCK_MINUTES = 15`; cada codigo incorrecto incrementa `claim_attempts`, el quinto intento setea `claim_locked_until` y durante el bloqueo responde `429`.
- El dashboard usa `activateDeviceWithClaimCode()` y envia `public_id + claim_code`.
- La seccion `Activar identificador` del dashboard pide `public_id` y `claim_code`, refresca la lista de dispositivos despues de activar y limpia `claim_code` del estado.
- Errores controlados en frontend: `400` -> `Datos de activación inválidos.`, `401` -> `Sesión expirada o no autenticada.`, `404` -> `Identificador no disponible.`, `422` -> `Código de activación inválido o incompleto.`, `429` -> `Demasiados intentos. Intenta nuevamente más tarde.`.
- `claim_code` no va en QR/NFC, no va en URL, no se guarda en `sessionStorage`, no se guarda en `localStorage`, no se loguea y no se muestra despues del envio.
- El access token sigue siendo temporal en `sessionStorage` y el backend sigue siendo la fuente de autorizacion.

Endpoint usado:

```http
POST /api/devices/activate
Authorization: Bearer <access_token>
Content-Type: application/json

{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }
```

Errores esperados: sin token `401`; body sin `claim_code` `422`; `public_id` invalido `422`; inexistente o no disponible `404 Identifier not available`; `pending_activation` sin `claim_code_hash` `400 Identifier cannot be activated`; `claim_code` incorrecto `400 Invalid activation data`; bloqueo por intentos `429 Too many activation attempts. Try again later.`.

Estados visibles de device en dashboard:

- `pending_activation` -> `Pendiente de activación`.
- `active` -> `Activo`.
- `disabled` -> `Deshabilitado`.
- `lost` -> `Reportado como perdido`.

El dashboard muestra una descripcion operacional por estado y deshabilita acciones sensibles para estados no activos cuando aplica.

## First Scan Activation Foundation

Sprint 13 prepara la base tecnica para activacion segura en primer escaneo con `claim_code`; Sprint 14 aplica la validacion `public_id + claim_code` en el backend de activacion.

Flujo de negocio objetivo:

- ProtegID vendera identificadores fisicos con QR impreso y NFC grabado.
- QR/NFC apuntan a la URL publica permanente `/p/{public_id}`.
- `public_id` es publico y no debe ser secuencial.
- `claim_code` es privado y viene dentro del empaque fisico.
- `claim_code` no va en QR/NFC, no va en URL, no debe loguearse y no debe guardarse en texto plano.
- El backend debe guardar solo hash del `claim_code`.

Campos agregados a `Device` para preparar activacion segura:

- `claim_code_hash`: hash del codigo privado; nullable por compatibilidad con devices existentes.
- `claimed_at`: fecha/hora en que el device fue reclamado correctamente.
- `claim_attempts`: contador de intentos de claim.
- `claim_locked_until`: bloqueo temporal por intentos fallidos.

Estos campos no se exponen por API.

Servicio `apps/api/app/services/claim_codes.py`:

- `generate_claim_code()` genera codigos con formato `XXXX-XXXX-XXXX`.
- `normalize_claim_code()` acepta codigo con o sin guiones y normaliza a uppercase con guiones.
- `hash_claim_code()` normaliza y reutiliza `hash_password()`.
- `verify_claim_code()` normaliza y reutiliza `verify_password()`.
- Usa `secrets` para generacion y caracteres no ambiguos.
- No loguea `claim_code` ni persiste el codigo plano.

Endpoint publico de estado de activacion:

```http
GET /api/public/devices/{public_id}/activation-status
```

- No requiere autenticacion.
- Responde `200 OK` solo si el device existe y `status == "pending_activation"`.
- Respuesta minima: `{ "public_id": "PID-XXXXXXXXXX", "activation_required": true, "status": "pending_activation" }`.
- Para `active`, `disabled`, `lost` o inexistente responde `404` generico.
- No revela owner, `user_id`, `claim_code_hash`, `claimed_at`, `claim_attempts`, `claim_locked_until`, datos medicos ni perfil.

Limites actuales:

- Existe registro de usuario final desde primer escaneo mediante `/register?returnTo=/p/{public_id}`.
- El boton `Crear cuenta` apunta a `/register?returnTo=/p/{public_id}`.
- El registro no inicia sesion automaticamente; el usuario debe iniciar sesion antes de reclamar.
- La sesion sigue siendo temporal por `sessionStorage`.
- No hay scanner QR.
- No hay lectura NFC real desde navegador.
- No hay tracking.
- No hay geolocalizacion.
- No hay notificaciones.
- Aun no existe provisionamiento masivo con export de `claim_code`.
- Aun no hay auditoria formal de intentos.

Validacion esperada:

- `python3 -m py_compile apps/api/app/api/devices.py apps/api/app/schemas/device.py`
- `git diff --check`
- `docker compose exec -T protegid-api alembic upgrade head`
- `docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"`
- `GET /p/{public_id_pending}` -> `200` y muestra onboarding.
- `GET /dashboard` -> `200`.
- Onboarding sin sesion muestra CTA login.
- Onboarding con sesion muestra formulario `claim_code`.
- `claim_code` correcto activa device.
- `claim_code` incorrecto muestra error controlado.
- Dashboard activa con `public_id + claim_code`.
- `claim_code` no queda en `sessionStorage` ni `localStorage`.
- `GET /api/public/devices/{public_id}/activation-status` con `pending_activation` -> `200`.
- `GET /api/public/devices/{public_id}/activation-status` con `active`, `disabled`, `lost` o inexistente -> `404`.
- `POST /api/devices/activate` sin token -> `401`.
- `POST /api/devices/activate` sin `claim_code` -> `422`.
- `POST /api/devices/activate` con `public_id` invalido -> `422`.
- `POST /api/devices/activate` con `public_id` inexistente -> `404`.
- Device pendiente sin `claim_code_hash` -> `400`.
- Claim incorrecto -> `400` e incrementa `claim_attempts`.
- Quinto intento incorrecto -> `claim_locked_until` seteado.
- Intento durante bloqueo -> `429`.
- Claim correcto en device no bloqueado -> `200` y device `active` con `user_id`, `activated_at` y `claimed_at`.
- Reactivar device ya activo -> `404`.
- Respuestas no exponen `claim_code`, `claim_code_hash`, `claimed_at`, `claim_attempts` ni `claim_locked_until`.

## QR Management Frontend

Sprint 11 agrega gestion QR desde `/dashboard` con descarga controlada del PNG desde backend autenticado.

- El dashboard consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- El dashboard permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr`.
- El dashboard permite descargar el PNG con `GET /api/admin/devices/{device_id}/qr/download` mediante el cliente `downloadDeviceQr(deviceId, accessToken): Promise<Blob>`.
- Estados visibles por dispositivo: `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`.
- Durante la descarga muestra `Descargando QR...`.
- Si la descarga termina correctamente muestra `QR descargado correctamente.`.
- Si el QR no existe, el dashboard indica `Genera el QR antes de descargarlo.`.
- Los endpoints QR requieren Bearer token y `role=admin`.
- Para usuario no-admin, el dashboard no muestra `Gestión QR`, estado QR, generar/regenerar/descargar QR, `object_key` ni el mensaje `La gestión de QR requiere rol admin.`.
- Para admin, el dashboard mantiene `Gestión QR`.
- El backend sigue siendo la fuente de autorizacion.
- El QR apunta a la URL publica `/p/{public_id}`.
- El QR solo contiene la URL publica del perfil; no incluye datos medicos embebidos.
- La visualizacion depende de que el perfil este marcado como publico con `is_public=true`.
- `object_key` se muestra solo en la gestion QR administrativa.
- La descarga genera un objeto temporal en el navegador con `URL.createObjectURL(blob)` y luego lo revoca con `URL.revokeObjectURL()`.
- La descarga obtiene el PNG desde el backend autenticado. No se expone URL publica de MinIO.
- No hay presigned URLs, preview de imagen QR, apertura de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones.

Validacion esperada:

- `python3 -m py_compile apps/api/app/api/qr_codes.py apps/api/app/services/qr_storage.py`
- `docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"`
- `GET /` responde `200 OK`.
- `GET /login` responde `200 OK`.
- `GET /dashboard` responde `200 OK`.
- `GET /p/PID-G2NYZP87KA` responde `200 OK`.
- `GET /p/PID-AAAAAAAAAA` responde `404 Not Found`.
- `GET /api/admin/devices/{device_id}/qr/download` sin token responde `401`.
- `GET /api/admin/devices/{device_id}/qr/download` con usuario no admin responde `403`.
- `GET /api/admin/devices/{device_id}/qr/download` con admin y QR existente responde `200` con `Content-Type: image/png`.
- Prueba GUI: login con usuario de prueba, confirmar `protegid_access_token` en `sessionStorage`, abrir `/dashboard` en la misma pestana, confirmar carga automatica de usuario/devices y cerrar sesion.
- Prueba GUI de activacion: crear cuenta desde primer escaneo, login con `returnTo`, volver a `/p/{public_id}`, ingresar `claim_code`, ver `Identificador vinculado correctamente.`, ir a `/dashboard?publicId={public_id}` y completar perfil.
- Usuario admin: ve estado QR y puede generar/regenerar QR.
- Usuario admin: puede descargar `PID-XXXXXXXXXX.png` desde Gestion QR.
- QR inexistente: muestra ayuda para generarlo antes de descargarlo.
- Usuario no admin: no ve Gestion QR, generar, regenerar, descargar QR, `object_key` ni mensaje de permisos QR.

## Estado actual

Existen Auth Foundation, Device Foundation, Public Profile Foundation, QR Foundation, Public Profile Frontend, Private Profile Management Frontend, UX Hardening & Navigation de Sprint 9, QR Management Frontend de Sprint 10, descarga controlada de QR de Sprint 11, Device Activation UX de Sprint 12, First Scan Activation Foundation de Sprint 13, Claim Code Activation Backend de Sprint 14, First Scan Onboarding Frontend de Sprint 15 y User Registration Flow de Sprint 16.

Limites actuales: no hay email verification, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, MFA, captcha, proteccion anti-bot, roles avanzados en frontend, expiracion visual previa del token, readiness completo de perfil publico, bloqueo de publicacion por campos minimos obligatorios, presigned URLs, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC real desde navegador, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, provisionamiento masivo con export de `claim_code` ni auditoria formal de intentos. El registro no inicia sesion automaticamente, los roles siguen siendo strings y la sesion sigue siendo temporal en `sessionStorage`. Email verification queda propuesto para un sprint posterior.
