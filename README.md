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
- Si no existe o no esta disponible, responde `404` real usando `notFound()`.
- No expone IDs internos, `device_id`, timestamps ni `deleted_at`.
- Solo muestra datos incluidos en `EmergencyProfilePublicRead`.
- El estado 404 no revela si el `public_id` existe o no.
- La vista es mobile-first, destaca tipo de sangre, contacto y telefono de emergencia.
- Los campos vacios se muestran como `No informado`.
- `/p/{public_id}` incluye un enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.

## Auth Frontend Foundation

La primera version del login frontend y sesion temporal existe.

- Ruta frontend de login: `/login`.
- Ruta privada: `/dashboard`.
- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
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
- Permite activar/asociar un identificador fisico desde la seccion `Activar identificador` usando `public_id`.
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

UX actual de `/dashboard`: validacion automatica si existe token temporal, secciones de estado de sesion, activacion de identificador, dispositivos, editor de perfil y fallback tecnico. Los dispositivos muestran `public_id`, estado legible, descripcion operacional, seleccion, gestion QR secundaria y boton claro `Editar perfil`. El editor agrupa campos en Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica. Mantiene `Guardar perfil`, `Cerrar sesion` y estados de carga, guardado, error y exito.

## Device Activation UX

Sprint 12 agrega activacion de identificadores desde `/dashboard` sin cambiar backend ni el flujo publico.

- La seccion `Activar identificador` permite vincular un identificador fisico a la cuenta autenticada.
- El formulario usa un input `public_id`, placeholder `PID-XXXXXXXXXX` y boton `Activar identificador`.
- Durante la solicitud muestra `Activando...`.
- Si la activacion es correcta muestra `Identificador activado correctamente.`.
- Despues de activar, el dashboard actualiza/refresca la lista de dispositivos y mantiene perfil, QR, generacion, descarga y edicion.
- El `public_id` puede estar impreso o asociado al QR/NFC fisico.
- El `public_id` no contiene datos medicos.
- Se recomienda verificar fisicamente el identificador antes de activarlo.
- El cliente frontend es `activateDevice(publicId, accessToken): Promise<Device>` en `apps/web/lib/devices.ts` y usa `buildApiUrl`.
- Errores controlados: `400` identificador no disponible para activacion, `401` sesion expirada o no autenticada, `404` identificador no encontrado.

Endpoint usado:

```http
POST /api/devices/activate
Authorization: Bearer <access_token>
Content-Type: application/json

{ "public_id": "PID-XXXXXXXXXX" }
```

El endpoint activa/asocia un device `pending_activation` al usuario autenticado, cambia `status` a `active` y setea `user_id` y `activated_at` segun la logica backend existente.

Estados visibles de device en dashboard:

- `pending_activation` -> `Pendiente de activación`.
- `active` -> `Activo`.
- `disabled` -> `Deshabilitado`.
- `lost` -> `Reportado como perdido`.

El dashboard muestra una descripcion operacional por estado y deshabilita acciones sensibles para estados no activos cuando aplica.

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
- Si el usuario no es admin o QR responde `403`, el frontend muestra `La gestión de QR requiere rol admin.` y el dashboard sigue mostrando devices y editor de perfil.
- El backend sigue siendo la fuente de autorizacion.
- El QR apunta a la URL publica `/p/{public_id}`.
- El QR solo contiene la URL publica del perfil; no incluye datos medicos embebidos.
- La visualizacion depende de que el perfil este marcado como publico con `is_public=true`.
- `object_key` se muestra como detalle tecnico.
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
- Prueba GUI de activacion: iniciar sesion, ir a `/dashboard`, ingresar un `public_id` pendiente, activar identificador, ver `Identificador activado correctamente.` y confirmar que aparece en `Mis dispositivos` como `Activo`.
- Usuario admin: ve estado QR y puede generar/regenerar QR.
- Usuario admin: puede descargar `PID-XXXXXXXXXX.png` desde Gestion QR.
- QR inexistente: muestra ayuda para generarlo antes de descargarlo.
- Usuario no admin: ve `La gestión de QR requiere rol admin.` y el dashboard sigue mostrando devices/perfil.

## Estado actual

Existen Auth Foundation, Device Foundation, Public Profile Foundation, QR Foundation, Public Profile Frontend, Private Profile Management Frontend, UX Hardening & Navigation de Sprint 9, QR Management Frontend de Sprint 10, descarga controlada de QR de Sprint 11 y Device Activation UX de Sprint 12.

Limites actuales: no hay registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, presigned URLs, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend ni creacion admin de devices desde frontend. Para produccion se evaluara una estrategia de sesion mas robusta.
