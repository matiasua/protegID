# Arquitectura

ProtegID usa un monorepo con un frontend Next.js, un backend FastAPI, un worker Python y servicios de soporte locales mediante Docker Compose.

## Componentes

- `apps/web`: interfaz web en Next.js, TypeScript, Tailwind CSS y shadcn/ui.
- `apps/api`: API FastAPI, worker Python base y migraciones Alembic.
- `infra/nginx`: Nginx como reverse proxy local.
- `infra/scripts`: scripts futuros de infraestructura.
- `docs`: documentacion tecnica del proyecto.

## Flujo local

Nginx recibe trafico HTTP en `localhost:8080`.

- `/` se enruta hacia `protegid-web:3000`.
- `/api/*` se enruta hacia `protegid-api:8000`.

PostgreSQL, Redis y MinIO quedan disponibles para funcionalidades actuales y futuras. Alembic esta configurado y el backend ya incluye las tablas de negocio `users`, `devices` y `emergency_profiles`.

## Auth Foundation

El backend incluye la base de autenticacion de Sprint 2:

- Modelo SQLAlchemy `User`.
- Tabla `users` gestionada por Alembic.
- Hashing de passwords con Argon2 mediante `pwdlib`.
- JWT access token para autenticacion Bearer.
- Endpoints actuales:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`

`GET /api/auth/me` requiere un token Bearer valido. No existe refresh token, recuperacion de password ni MFA en el estado actual.

## Device Foundation

El backend incluye la base de dispositivos de Sprint 3:

- Modelo SQLAlchemy `Device`.
- Tabla `devices` gestionada por Alembic.
- Relacion nullable `devices.user_id -> users.id` para permitir dispositivos pendientes antes de ser activados por un usuario.
- `public_id` unico y visible con formato `PID-XXXXXXXXXX`.
- El alfabeto de `public_id` evita caracteres confusos: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`.
- `public_id` no es secuencial y no usa el UUID interno completo como identificador publico.

Estados actuales de `Device`:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints actuales de devices:

- `GET /api/devices`
- `POST /api/devices/activate`
- `POST /api/admin/devices`

`GET /api/devices` requiere token Bearer y solo lista dispositivos del usuario autenticado. `POST /api/devices/activate` requiere token Bearer y activa un dispositivo `pending_activation` para el usuario autenticado. `POST /api/admin/devices` requiere token Bearer y `role=admin`.

## Public Profile Foundation

El backend incluye la base de perfiles publicos de emergencia de Sprint 4:

- Modelo SQLAlchemy `EmergencyProfile`.
- Tabla `emergency_profiles` gestionada por Alembic.
- Relacion unica y obligatoria `emergency_profiles.device_id -> devices.id`.
- Un perfil de emergencia queda asociado a un unico device.
- Los endpoints privados requieren token Bearer y validan ownership con `current_user.id == device.user_id`.

Endpoints privados de perfiles de emergencia:

- `GET /api/devices/{device_id}/emergency-profile`
- `PUT /api/devices/{device_id}/emergency-profile`

Endpoint publico de perfil de emergencia:

- `GET /api/public/profiles/{public_id}`

El endpoint publico no requiere autenticacion. Busca por `Device.public_id` y solo responde si el device esta `active`, el perfil tiene `is_public == true` y `deleted_at is null`. La respuesta publica no expone `id`, `device_id`, `created_at`, `updated_at` ni `deleted_at`.

## QR Foundation

El backend incluye la base de QR de Sprint 5:

- Variables de configuracion `PUBLIC_APP_URL` y `PUBLIC_PROFILE_PATH`.
- Helper `build_public_profile_url(public_id)` para construir la URL publica estable del perfil.
- Generacion de QR PNG en memoria mediante `qrcode[pil]`.
- Persistencia del QR en MinIO/S3 compatible.
- Object key estable por device: `qr/devices/{public_id}.png`.

El QR no contiene datos medicos. El QR contiene solo la URL publica con formato `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`. En local, un ejemplo es `http://localhost:8080/p/PID-XXXXXXXXXX`.

Endpoints admin de QR:

- `POST /api/admin/devices/{device_id}/qr`
- `GET /api/admin/devices/{device_id}/qr`
- `GET /api/admin/devices/{device_id}/qr/download`

Los endpoints requieren token Bearer y `role=admin`. `POST` genera/sube el QR y `GET /qr` devuelve metadata: `device_id`, `public_id`, `object_key`, `content_type` y `exists`.

`GET /api/admin/devices/{device_id}/qr/download` busca el device por `device_id`, calcula `qr/devices/{public_id}.png`, lee el objeto desde MinIO y no genera QR automaticamente. Si el QR no existe responde `404`. Si existe responde el PNG con `Content-Type: image/png` y `Content-Disposition: attachment; filename="{public_id}.png"`. No usa presigned URLs y no expone bucket ni credenciales.

## Public Profile Frontend

El frontend publico de Sprint 6 ya existe en Next.js App Router.

- Ruta publica: `/p/{public_id}`.
- Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.
- No requiere login.
- Renderiza server-side la ficha de emergencia.
- Consulta el backend mediante `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si el perfil no existe o no esta disponible, responde `404` real usando `notFound()`.
- Tiene estado visual especifico para perfil no disponible.
- Incluye un enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.

La vista publica no expone IDs internos, `device_id`, timestamps ni `deleted_at`. Solo muestra los campos incluidos en `EmergencyProfilePublicRead`. El 404 no debe revelar si el `public_id` existe o no.

La UI es una ficha de emergencia mobile-first. Prioriza datos criticos arriba, destaca tipo de sangre, contacto y telefono de emergencia, organiza la informacion en secciones y muestra campos vacios como `No informado`.

## Home y Navegacion MVP

Sprint 9 reorganiza la entrada y navegacion principal del frontend sin cambiar endpoints ni auth.

- `/` funciona como landing inicial del MVP.
- La landing muestra el nombre ProtegID y describe identificadores fisicos de emergencia con QR y NFC.
- Incluye accesos principales a `/login` y `/dashboard`.
- Explica el flujo: activar identificador, completar perfil de emergencia y compartir acceso publico mediante QR/NFC.
- Muestra el estado actual del MVP: login temporal, dashboard privado, perfil publico por `public_id` y QR generado hacia `/p/{public_id}`.
- Incluye nota de alcance: `Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.`
- `/login` y `/dashboard` incluyen `Volver al inicio`.
- `/p/{public_id}` enlaza discretamente al inicio mediante `ProtegID`.

## Private Profile Management Frontend

El frontend privado inicial existe en Next.js App Router.

- Ruta frontend de login: `/login`.
- Ruta privada base: `/dashboard`.
- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- `/login` detecta una sesion temporal existente desde `sessionStorage`.
- Si existe token temporal, muestra `Ya existe una sesión temporal activa.`, permite ir a `/dashboard` y permite cerrar la sesion temporal con `clearSessionToken()`.
- Si el login es correcto, recibe `access_token` y `token_type`.
- Guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token`.
- Muestra el token en un `textarea` readonly por transparencia temporal del MVP.
- Despues de login exitoso muestra `Continuar al dashboard` y no redirige automaticamente.
- `/login` muestra estados de carga, exito y error; `401` muestra credenciales invalidas.
- `/dashboard` lee automaticamente el token desde `sessionStorage` con `getSessionToken()`.
- `/dashboard` valida sesion contra `GET /api/auth/me`.
- Si la sesion es valida, carga dispositivos con `GET /api/devices`.
- Si no hay sesion, muestra estado no autenticado y boton/link `Ir a login`.
- Mantiene fallback tecnico reducido como `Usar token manual` para pegar token manualmente.
- Tiene boton `Cerrar sesion` que limpia `sessionStorage` con `clearSessionToken()`.
- Permite seleccionar un dispositivo.
- Carga el perfil privado con `GET /api/devices/{device_id}/emergency-profile`.
- Crea o actualiza el perfil con `PUT /api/devices/{device_id}/emergency-profile`.
- Consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- Permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr` cuando el usuario tiene `role=admin`.

Campos gestionados por el formulario privado:

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

La UX actual de `/login` tiene encabezado claro, formulario limpio, estados visibles, deteccion de sesion temporal existente, cierre de sesion temporal y continuidad manual al dashboard. La UX actual de `/dashboard` esta organizada en secciones de estado de sesion, dispositivos, editor de perfil y fallback tecnico. Los dispositivos muestran `public_id`, status visual, seleccion, gestion QR secundaria y boton claro `Editar perfil`. El editor agrupa campos en Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica. Mantiene `Guardar perfil`, `Cerrar sesion` y estados de carga, guardado, error y exito.

## QR Management Frontend

Sprint 11 mantiene la gestion QR desde el dashboard y agrega descarga controlada del PNG mediante backend autenticado.

- `/dashboard` consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- `/dashboard` permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr`.
- `/dashboard` permite descargar QR con `GET /api/admin/devices/{device_id}/qr/download` mediante `downloadDeviceQr(deviceId, accessToken): Promise<Blob>`.
- Estados visibles: `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`.
- El boton de descarga muestra `Descargar QR` y, durante la solicitud, `Descargando QR...`.
- Si la descarga es correcta, muestra `QR descargado correctamente.`.
- Si el QR no existe, muestra `Genera el QR antes de descargarlo.`.
- Los endpoints QR requieren Bearer token y `role=admin`.
- Si el usuario no es admin o QR responde `403`, el frontend muestra `La gestión de QR requiere rol admin.`.
- El dashboard no debe romper si QR responde `403`; devices y editor de perfil siguen disponibles.
- El backend sigue siendo la fuente de autorizacion.
- El QR apunta a `/p/{public_id}` y solo contiene la URL publica del perfil.
- El QR no incluye datos medicos embebidos.
- La visualizacion publica depende de `emergency_profile.is_public == true`.
- `object_key` se muestra como detalle tecnico.
- La descarga usa `URL.createObjectURL(blob)` y revoca el objeto temporal con `URL.revokeObjectURL()`.
- No se expone URL publica de MinIO, bucket ni credenciales.
- No hay presigned URLs, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones.

## Seguridad de esta version

- Es una sesion temporal para MVP.
- Usa `sessionStorage`; no usa `localStorage`.
- No usa cookies.
- No hay refresh token.
- No hay middleware de proteccion.
- No hay expiracion/renovacion automatica desde frontend.
- El backend sigue validando Bearer token en endpoints privados.
- El token vive solo durante la sesion/pestana del navegador.
- `sessionStorage` no se comparte entre pestanas.
- Para produccion se evaluara una estrategia mas robusta.

## Restricciones de esta version

- No hay registro frontend completo.
- No hay recuperacion de password.
- No hay refresh token.
- No hay cookies HttpOnly.
- No hay middleware de proteccion.
- No hay roles avanzados en frontend.
- No hay expiracion visual previa del token.
- No hay subida de archivos medicos.
- No hay presigned URLs.
- No hay preview de imagen QR.
- No hay apertura directa de MinIO.
- No hay NFC funcional.
- No hay tracking de escaneos.
- No hay geolocalizacion.
- No hay notificaciones.

Los endpoints privados siguen protegidos por Bearer token. El frontend solo consume datos del usuario autenticado segun las validaciones de ownership del backend.

## Limites de esta etapa

No hay registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, descarga publica de QR, presigned URL publica ni MFA.

Sprint 11 no agrega nuevas tablas ni nuevas migraciones.

`device_type="qr_nfc_tag"` existe como base del modelo de dispositivo. QR Foundation ya existe; NFC todavia no esta implementado.

## CodeGraph

CodeGraph esta inicializado y operativo para este proyecto. OpenCode tiene integracion MCP con herramientas `codegraph_*`, que deben usarse para busquedas estructurales del proyecto antes de cambios relevantes.

La carpeta `.codegraph/` no debe modificarse manualmente ni subirse como indice del proyecto.
