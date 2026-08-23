# Arquitectura

ProtegID usa un monorepo con un frontend Next.js, un backend FastAPI, un worker Python y servicios de soporte locales mediante Docker Compose.

## Autenticacion Productiva Sprint 18

La arquitectura actual usa sesiones server-side con token opaco en cookie HttpOnly.

- `auth_sessions` persiste sesiones revocables. Guarda `session_token_hash`, nunca el token raw.
- `POST /api/auth/login` crea sesion, setea `protegid_session` y `protegid_csrf`, y devuelve `user`; no devuelve tokens.
- `GET /api/auth/me` y endpoints privados usan `CurrentUserDep`, que autentica solo por cookie de sesion.
- `POST /api/auth/logout` revoca la sesion y borra cookies.
- El frontend usa `credentials: "include"`; no usa `sessionStorage`, `localStorage`, `access_token` ni `Authorization Bearer`.
- CSRF double-submit protege metodos mutantes con cookie `protegid_csrf` y header `X-CSRF-Token`.

Cookies:

- Local: `protegid_session`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure=false` solo para HTTP local.
- Produccion recomendada: `__Host-protegid_session`, `HttpOnly`, `Secure=true`, `SameSite=Lax`, `Path=/`, sin `Domain`.
- CSRF: `protegid_csrf`, no HttpOnly, `SameSite=Lax`, `Path=/`, `Secure=true` en produccion, sin `Domain`.

Operacionalmente se recomienda servir web y API bajo el mismo dominio/origin con `/api` detras de Nginx/reverse proxy. No usar CORS abierto con credentials. Si se separan dominios en el futuro, revisar `SameSite=None`, `Secure`, CORS y CSRF.

## Verificacion de Email Sprint 19

La verificacion de email agrega `auth_action_tokens` para tokens one-time-use y bloqueo backend de mutaciones criticas.

- `POST /api/auth/register` crea usuario no verificado y no inicia sesion.
- El token raw de verificacion no se persiste; la DB guarda `token_hash`.
- El link enviado apunta a `/verify-email?token=...`.
- `POST /api/auth/verify-email` es publico y no requiere CSRF.
- `POST /api/auth/resend-verification` requiere sesion y CSRF.
- Login se permite aunque `email_verified_at` sea `null`.
- Usuarios no verificados pueden usar dashboard basico y listar devices propios.
- Usuarios no verificados no pueden activar identificadores, editar/publicar perfiles ni operar endpoints admin de devices/QR.

Mailpit queda disponible localmente como servicio Docker Compose para pruebas de correo: UI `http://localhost:8025`, SMTP interno `mailpit:1025`.

Rate limiting usa Redis como dependencia critica. Si Redis falla, endpoints criticos responden `503` fail-closed. Las keys no guardan email plano; el email se hashea con SHA-256 y no se guardan tokens ni `claim_code` en Redis.

Detalle tecnico: `docs/auth-email-verification.md`.

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
Mailpit queda disponible para pruebas locales de email de verificacion.

## Auth Foundation

El backend incluye autenticacion con usuarios y sesiones server-side:

- Modelo SQLAlchemy `User`.
- Tabla `users` gestionada por Alembic.
- Hashing de passwords con Argon2 mediante `pwdlib`.
- Sesiones server-side revocables en `auth_sessions`.
- Tokens de accion one-time-use en `auth_action_tokens`.
- Cookie HttpOnly de sesion y cookie CSRF double-submit.
- Endpoints actuales:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/verify-email`
  - `POST /api/auth/resend-verification`
  - `GET /api/auth/me`

`GET /api/auth/me` requiere cookie de sesion valida. No existe refresh token, recuperacion de password ni MFA en el estado actual.

Sprint 16 endurece el registro/login existente para usuario final:

- `POST /api/auth/register` recibe `{ "email": "usuario@example.com", "password": "Password123!", "full_name": "Nombre Usuario" }`.
- Devuelve `RegisterResponse`; no devuelve token y no inicia sesion automaticamente.
- El rol publico queda forzado a `user`; no existe registro publico de `admin`.
- `password_hash` no se expone y el password no debe loguearse.
- El email se normaliza con `strip().lower()` en registro y login/autenticacion.
- La busqueda por email es case-insensitive.
- Duplicados con casing distinto responden `409`.
- Se captura `IntegrityError` con rollback para race conditions de unique email.
- Genera correo de verificacion y token one-time-use; el raw token no se guarda en DB.

## Device Foundation

El backend incluye la base de dispositivos de Sprint 3:

- Modelo SQLAlchemy `Device`.
- Tabla `devices` gestionada por Alembic.
- Relacion nullable `devices.user_id -> users.id` para permitir dispositivos pendientes antes de ser activados por un usuario.
- `public_id` unico y visible con formato `PID-XXXXXXXXXX`.
- El alfabeto de `public_id` evita caracteres confusos: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`.
- `public_id` no es secuencial y no usa el UUID interno completo como identificador publico.
- Campos de first-scan activation: `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until`.
- Los campos de claim preparan activacion segura por `claim_code` y no se exponen por API.

Estados actuales de `Device`:

- `pending_activation` -> `Pendiente de activación` en dashboard.
- `active` -> `Activo` en dashboard.
- `disabled` -> `Deshabilitado` en dashboard.
- `lost` -> `Reportado como perdido` en dashboard.

Endpoints actuales de devices:

- `GET /api/devices`
- `POST /api/devices/activate`
- `POST /api/admin/devices`
- `GET /api/public/devices/{public_id}/activation-status`

`GET /api/devices` requiere cookie de sesion y solo lista dispositivos del usuario autenticado. `POST /api/devices/activate` requiere cookie de sesion, CSRF y body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`; valida el codigo privado contra `claim_code_hash`, activa/asocia un dispositivo `pending_activation` sin `user_id`, cambia `status` a `active`, setea `user_id`, `activated_at` y `claimed_at`, resetea `claim_attempts` y limpia `claim_locked_until`. `POST /api/admin/devices` requiere cookie de sesion, CSRF y `role=admin`.

## First Scan Activation Foundation

Sprint 13 prepara el flujo de primer escaneo para identificadores fisicos con QR impreso y NFC grabado.

- QR/NFC apuntan a `/p/{public_id}`.
- `public_id` es publico.
- `claim_code` es privado, viene dentro del empaque fisico y no va en QR/NFC.
- `claim_code` no debe guardarse en texto plano; solo se guarda `claim_code_hash`.
- `claim_code` no debe ir en URL, logs ni respuestas API.
- `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` existen en `Device` para soportar claim seguro.
- `claim_code`, `claim_code_hash`, `claimed_at`, `claim_attempts` y `claim_locked_until` no se exponen en respuestas API.
- `claim_code` y `claim_code_hash` no deben loguearse.
- `POST /api/devices/activate` ya no acepta activacion solo con `public_id`; requiere `public_id + claim_code`.
- El backend rechaza devices inexistentes, no pendientes, ya asociados, sin `claim_code_hash`, con codigo incorrecto o bloqueados por intentos.
- Proteccion anti fuerza bruta: `MAX_CLAIM_ATTEMPTS = 5`, `CLAIM_LOCK_MINUTES = 15`; cada codigo incorrecto incrementa `claim_attempts`, el quinto setea `claim_locked_until` y durante el bloqueo responde `429`.

Servicio `apps/api/app/services/claim_codes.py`:

- `generate_claim_code()` genera `XXXX-XXXX-XXXX` con caracteres no ambiguos y `secrets`.
- `normalize_claim_code()` acepta codigo con o sin guiones.
- `hash_claim_code()` reutiliza `hash_password()`.
- `verify_claim_code()` reutiliza `verify_password()` y retorna `False` sin hash o con input vacio.

Endpoint publico minimo:

```http
GET /api/public/devices/{public_id}/activation-status
```

Responde `200 OK` solo si el device existe y `status == "pending_activation"`:

```json
{
  "public_id": "PID-XXXXXXXXXX",
  "activation_required": true,
  "status": "pending_activation"
}
```

Para devices `active`, `disabled`, `lost` o inexistentes responde `404` generico. No revela owner, `user_id`, `claim_code_hash`, `claimed_at`, `claim_attempts`, `claim_locked_until`, datos medicos ni perfil.

## Public Profile Foundation

El backend incluye la base de perfiles publicos de emergencia. Arquitectura
vigente (CONTRACT, Bloque 8.3): `EmergencyProfile` pertenece a
`ProtectedPerson`, no a `Device`. `Device` no es dueno del perfil.

```
User/Account -> ProtectedPerson -> EmergencyProfile
Device -> ProtectedPerson
```

- Modelo SQLAlchemy `EmergencyProfile`.
- Tabla `emergency_profiles` gestionada por Alembic.
- `emergency_profiles.device_id -> devices.id` sigue existiendo en el modelo (columna nullable, compatibilidad historica; su DROP pertenece a un bloque CONTRACT posterior), pero ya NO es la relacion de ownership productiva: la fuente de verdad es `emergency_profiles.protected_person_id -> protected_persons.id`.
- Los endpoints privados de edicion (account-scoped) requieren cookie de sesion y validan ownership con `current_user.id` contra la cuenta autenticada, no contra un `device.user_id`.

Endpoints privados de perfiles de emergencia (account-scoped; los endpoints device-scoped equivalentes existieron como contrato legacy y fueron retirados en Bloque 8.3):

- `GET /api/emergency-profile`
- `PUT /api/emergency-profile`
- `GET /api/emergency-profile/status`

`GET /api/devices/{device_id}/public-access-status` es el unico endpoint de EmergencyProfile que sigue siendo device-scoped y ownership-protegido; combina Device + ProtectedPerson + EmergencyProfile para responder si ESE device concreto esta operativo, sin exponer el perfil.

Endpoint publico de perfil de emergencia:

- `GET /api/public/profiles/{public_id}`

Resolucion publica (CONTRACT): `public_id -> Device -> Device.protected_person_id -> ProtectedPerson -> EmergencyProfile activo`. El endpoint publico no requiere autenticacion. Busca por `Device.public_id`, pero solo responde si `calculate_public_access_status(device, protected_person, profile)` indica `is_operational == true`. La respuesta publica no expone `id`, `device_id`, `user_id`, `is_public`, flags `*_none`, consentimiento, `created_at`, `updated_at` ni `deleted_at`.

Sprint 17 separa identificador vinculado de ProtegID operativo:

- Un identificador queda vinculado cuando el usuario demuestra posesion fisica con `public_id + claim_code`.
- ProtegID queda operativo solo si el perfil cumple datos minimos, consentimiento vigente y `is_public=true`.
- `device.status` sigue representando ciclo de vida fisico/operacional; readiness es derivado del perfil.
- Campos minimos: `display_name`, `emergency_contact_name`, `emergency_contact_relationship`, `emergency_contact_phone`, decision explicita para condiciones medicas, alergias y medicamentos, `public_consent_accepted_at`, `public_consent_version` vigente e `is_public=true`.
- Nuevos campos: `medical_conditions_none`, `allergies_none`, `medications_none`, `public_consent_accepted_at`, `public_consent_version`.
- `is_public` conserva el rol canonico de publicacion, con default `false` para nuevos perfiles.
- `PUBLIC_PROFILE_CONSENT_VERSION` define la version vigente de consentimiento; si no coincide con la aceptada, el perfil no queda operativo.

Readiness backend:

- Servicio: `apps/api/app/services/emergency_profile_status.py`, que separa `ProfileReadiness` (solo perfil), `PublicationEligibility` (agrega consentimiento) y `PublicAccessStatus` (agrega Device + ProtectedPerson, especifico de un device). `profile_readiness.py` (motor legacy `calculate_profile_readiness(device, profile)`) ya no tiene callers productivos.
- Schema: `EmergencyProfileStatusRead`.
- Endpoint privado: `GET /api/emergency-profile/status`.
- Requiere cookie de sesion y no expone valores medicos ni `user_id`.
- El backend bloquea `is_public=true` si `publication_eligibility.can_publish != true` y responde `422 Emergency profile is not ready for publication.`.
- El endpoint publico devuelve `404` generico ante inexistente, no activo, eliminado, incompleto, sin consentimiento vigente o `is_public=false`.

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

Los endpoints requieren cookie de sesion y `role=admin`; `POST` requiere CSRF, genera/sube el QR y `GET /qr` devuelve metadata: `device_id`, `public_id`, `object_key`, `content_type` y `exists`.

`GET /api/admin/devices/{device_id}/qr/download` busca el device por `device_id`, calcula `qr/devices/{public_id}.png`, lee el objeto desde MinIO y no genera QR automaticamente. Si el QR no existe responde `404`. Si existe responde el PNG con `Content-Type: image/png` y `Content-Disposition: attachment; filename="{public_id}.png"`. No usa presigned URLs y no expone bucket ni credenciales.

## Public Profile Frontend

El frontend publico existe en Next.js App Router y Sprint 15 agrega onboarding de primer escaneo.

- Ruta publica: `/p/{public_id}`.
- Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.
- No requiere login.
- Renderiza server-side la ficha de emergencia.
- Consulta el backend mediante `GET /api/public/profiles/{public_id}`.
- Si el perfil existe y esta disponible, responde `200 OK`.
- Si no existe perfil publico, consulta `GET /api/public/devices/{public_id}/activation-status`.
- Si `activation-status` responde `pending_activation`, muestra onboarding publico con titulo `Identificador ProtegID no activado`.
- Si `activation-status` responde `404`, mantiene `404` real o mensaje generico usando `notFound()`.
- Incluye un enlace discreto `ProtegID` hacia `/`.
- El not-found publico mantiene `404` real, permite volver al inicio y no revela si el `public_id` existe.

La vista publica no expone IDs internos, `device_id`, timestamps ni `deleted_at`. Solo muestra los campos incluidos en `EmergencyProfilePublicRead`. El 404 no debe revelar si el `public_id` existe o no.

La UI es una ficha de emergencia mobile-first. Prioriza datos criticos arriba, destaca tipo de sangre, contacto y telefono de emergencia, organiza la informacion en secciones y muestra campos vacios como `No informado`.

## First Scan Onboarding Frontend

Sprint 15 implementa el flujo frontend de primer escaneo sin cambiar la URL publica permanente.

- QR/NFC apuntan a `/p/{public_id}`.
- Si existe perfil publico, `/p/{public_id}` muestra la ficha publica.
- Si no existe perfil publico, `apps/web/lib/public-devices.ts` consulta `GET /api/public/devices/{public_id}/activation-status` con `getPublicDeviceActivationStatus(publicId)`.
- El cliente publico retorna estado de activacion en `200`, retorna `null` en `404`, no usa token, no envia `Authorization` y no maneja `claim_code`.
- Si el device esta `pending_activation`, `/p/{public_id}` muestra `Identificador ProtegID no activado`.
- El onboarding indica que el identificador fisico aun no esta vinculado, que el `claim_code` viene dentro del empaque fisico y que el QR/NFC solo contiene la URL publica permanente.
- Muestra `public_id` como referencia tecnica discreta.
- Sin sesion, muestra CTA `Iniciar sesión` hacia `/login?returnTo=/p/{public_id}` y CTA `Crear cuenta` hacia `/register?returnTo=/p/{public_id}`.
- El componente cliente `apps/web/app/p/[publicId]/activation-form.tsx` valida sesion con `/api/auth/me`.
- Con sesion, permite ingresar `claim_code` y llama `activateDeviceWithClaimCode(publicId, claimCode)` usando cookie y CSRF.
- La activacion envia `POST /api/devices/activate` con body `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`.
- En exito muestra `Identificador vinculado correctamente.` y CTA `Completar perfil de emergencia` hacia `/dashboard?publicId={public_id}`.

Flujo Sprint 16 esperado: `/p/{public_id}` -> `/register?returnTo=/p/{public_id}` -> `/login?returnTo=/p/{public_id}` -> `/p/{public_id}` -> `claim_code` -> identificador vinculado -> `/dashboard?publicId={public_id}` -> completar perfil de emergencia.

## Home y Navegacion MVP

Sprint 9 reorganiza la entrada y navegacion principal del frontend sin cambiar endpoints ni auth.

- `/` funciona como landing inicial del MVP.
- La landing muestra el nombre ProtegID y describe identificadores fisicos de emergencia con QR y NFC.
- Incluye accesos principales a `/login` y `/dashboard`.
- Explica el flujo: activar identificador, completar perfil de emergencia y compartir acceso publico mediante QR/NFC.
- Muestra el estado actual: login con cookie HttpOnly, dashboard privado, perfil publico por `public_id` y QR generado hacia `/p/{public_id}`.
- Incluye nota de alcance: `Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.`
- `/login` y `/dashboard` incluyen `Volver al inicio`.
- `/p/{public_id}` enlaza discretamente al inicio mediante `ProtegID`.

## Private Profile Management Frontend

El frontend privado inicial existe en Next.js App Router.

- Ruta frontend de login: `/login`.
- Ruta privada base: `/dashboard`.
- `/login` permite ingresar email y password.
- `/login` consume `POST /api/auth/login`.
- `/register` permite crear cuenta con Nombre, Email y Password; consume `POST /api/auth/register`, envia `full_name`, no guarda token, no usa storage y no inicia sesion automaticamente.
- `/register` limpia password tras registro exitoso y muestra `Ya existe una cuenta con este correo.` para `409`.
- `/register` y `/login` soportan `returnTo` sanitizado.
- `returnTo` solo acepta rutas internas seguras; rechaza URLs externas, rutas de API/build y auth loops.
- Despues de login exitoso, `/login` redirige automaticamente con `router.replace()` al `returnTo` seguro o `/dashboard`.
- `/login` detecta sesion activa contra `/api/auth/me` y redirige automaticamente al destino seguro.
- Si el login es correcto, el backend setea cookies y no devuelve tokens.
- No guarda tokens en storage y no muestra tokens.
- `/login` muestra estados de carga, exito y error; `401` muestra credenciales invalidas.
- `/dashboard` valida sesion contra `GET /api/auth/me` usando cookie.
- Si la sesion es valida, carga dispositivos con `GET /api/devices`.
- Permite activar/asociar identificadores fisicos desde `Activar identificador` ingresando `public_id` y `claim_code` con `POST /api/devices/activate`.
- Si no hay sesion, muestra estado no autenticado y boton/link `Ir a login`.
- No mantiene fallback de token manual.
- Tiene boton `Cerrar sesion` que llama `POST /api/auth/logout` con CSRF.
- Permite seleccionar un dispositivo.
- Carga el perfil privado de la cuenta con `GET /api/emergency-profile` (account-scoped, no depende del device seleccionado).
- Crea o actualiza el perfil con `PUT /api/emergency-profile`.
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

`is_public` expresa intencion de publicacion; el backend solo publica si readiness y consentimiento vigente permiten operacion.

La UX actual de `/login` tiene encabezado claro, formulario limpio, estados visibles, deteccion de sesion activa y redireccion automatica segura. La UX actual de `/dashboard` esta organizada en secciones de estado de sesion, activacion de identificador, dispositivos y editor de perfil. Los dispositivos muestran `public_id`, estado legible, descripcion operacional, seleccion, gestion QR secundaria y boton claro `Editar perfil`. El editor agrupa campos en Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica. Mantiene `Guardar perfil`, `Cerrar sesion` y estados de carga, guardado, error y exito.

## Device Activation UX

Sprint 12 agrega activacion de identificadores desde `/dashboard`; Sprint 14 cambia el backend para exigir `public_id + claim_code`; Sprint 15 actualiza el frontend para enviar ambos campos.

- La seccion `Activar identificador` permite ingresar el `public_id` impreso o asociado al QR/NFC fisico y el `claim_code` incluido dentro del empaque.
- El `public_id` esperado tiene formato `PID-XXXXXXXXXX`.
- El `claim_code` esperado tiene formato `XXXX-XXXX-XXXX`.
- El `public_id` no contiene datos medicos y la UI recomienda verificar fisicamente el identificador antes de activarlo.
- El formulario muestra boton `Activar identificador`, estado `Activando...` y exito `Identificador vinculado correctamente.`.
- El frontend usa `activateDeviceWithClaimCode(publicId, claimCode): Promise<Device>` desde `apps/web/lib/devices.ts`.
- El backend requiere cookie de sesion, CSRF y body JSON `{ "public_id": "PID-XXXXXXXXXX", "claim_code": "XXXX-XXXX-XXXX" }`.
- Maneja errores controlados: `400` datos de activacion invalidos, `401` sesion expirada o no autenticada, `404` identificador no disponible, `422` codigo de activacion invalido o incompleto y `429` demasiados intentos.
- Al activar correctamente, el dashboard refresca/actualiza `Mis dispositivos` y mantiene perfil, QR, generacion, descarga y edicion.
- El dashboard limpia `claim_code` del estado despues del envio y no lo guarda en storage.
- El dashboard muestra descripcion operacional por estado de device.
- Para `active` mantiene edicion de perfil y gestion QR.
- Para `disabled`, `lost` o `pending_activation` muestra advertencias y deshabilita acciones sensibles cuando aplica.
- El backend sigue siendo la fuente de autorizacion.

## QR Management Frontend

Sprint 11 mantiene la gestion QR desde el dashboard y agrega descarga controlada del PNG mediante backend autenticado.

- `/dashboard` consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`.
- `/dashboard` permite generar o regenerar QR con `POST /api/admin/devices/{device_id}/qr`.
- `/dashboard` permite descargar QR con `GET /api/admin/devices/{device_id}/qr/download` mediante `downloadDeviceQr(deviceId): Promise<Blob>`.
- Estados visibles: `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`.
- El boton de descarga muestra `Descargar QR` y, durante la solicitud, `Descargando QR...`.
- Si la descarga es correcta, muestra `QR descargado correctamente.`.
- Si el QR no existe, muestra `Genera el QR antes de descargarlo.`.
- Los endpoints QR requieren cookie de sesion y `role=admin`; los metodos mutantes requieren CSRF.
- Para usuarios no-admin, `/dashboard` oculta toda Gestion QR: estado QR, generar, regenerar, descargar, `object_key` y mensajes de permisos QR.
- Para admin, `/dashboard` mantiene Gestion QR.
- El dashboard no debe romper si QR responde `403`; devices y editor de perfil siguen disponibles.
- El backend sigue siendo la fuente de autorizacion.
- El QR apunta a `/p/{public_id}` y solo contiene la URL publica del perfil.
- El QR no incluye datos medicos embebidos.
- La visualizacion publica depende de `readiness.is_public_operational == true`.
- `object_key` se muestra solo como detalle tecnico en la Gestion QR administrativa.
- La descarga usa `URL.createObjectURL(blob)` y revoca el objeto temporal con `URL.revokeObjectURL()`.
- No se expone URL publica de MinIO, bucket ni credenciales.
- No hay presigned URLs, preview de imagen QR, apertura directa de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones.

## Seguridad de esta version

- Usa sesion server-side revocable con cookie HttpOnly.
- Usa CSRF double-submit para metodos mutantes con sesion.
- No guarda tokens de auth en `sessionStorage` ni `localStorage`.
- No envia `Authorization Bearer` desde el frontend.
- No hay refresh token.
- No hay expiracion/renovacion automatica desde frontend.
- El backend valida cookies de sesion en endpoints privados.
- El endpoint publico de estado de activacion evita revelar estados internos distintos de `pending_activation`.
- La activacion frontend envia `public_id + claim_code` desde onboarding y dashboard.
- En produccion debe usarse HTTPS, `Secure=true`, prefijo `__Host-`, `Path=/` y sin `Domain`.

## Restricciones de esta version

- No hay recuperacion de password.
- No hay refresh token.
- No hay refresh token.
- No hay roles avanzados en frontend.
- No hay expiracion visual previa de la sesion.
- No hay subida de archivos medicos.
- No hay presigned URLs.
- No hay preview de imagen QR.
- No hay apertura directa de MinIO.
- No hay scanner QR.
- No hay lectura NFC.
- No hay camara.
- No hay NFC funcional.
- No hay tracking de escaneos.
- No hay geolocalizacion.
- No hay notificaciones.
- No hay cambio de estado desde frontend.
- No hay reporte de perdido desde frontend.
- No hay creacion admin de devices desde frontend.
- El registro de usuario final desde primer escaneo existe, pero no inicia sesion automaticamente.
- No hay provisionamiento masivo con export de `claim_code`.
- No hay auditoria formal de intentos de claim.

Los endpoints privados estan protegidos por cookie de sesion. El frontend solo consume datos del usuario autenticado segun las validaciones de ownership del backend.

## Limites de esta etapa

No hay validacion estricta de telefono internacional, wizard profesional multi-vista para perfil, recuperacion de password, refresh token, MFA, captcha, proteccion anti-bot, roles avanzados en frontend, expiracion visual previa de la sesion, auditoria formal de eventos criticos, historial/versionado completo de consentimientos, segundo contacto de emergencia, normalizacion avanzada de datos medicos, hardening de rate limiting publico, subida de archivos medicos, preview de imagen QR, apertura directa de MinIO, scanner QR, lectura NFC real desde navegador, camara, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, cambio de estado desde frontend, reporte de perdido desde frontend, creacion admin de devices desde frontend, descarga publica de QR, presigned URL publica ni provisionamiento masivo con export de `claim_code`. El registro no inicia sesion automaticamente y roles siguen siendo strings.

Sprint 13 agrega campos a `devices` mediante migracion Alembic para preparar claim seguro. Sprint 14 actualiza el backend de activacion para requerir `public_id + claim_code` y bloqueo temporal por intentos fallidos. Sprint 15 agrega onboarding de primer escaneo y actualiza dashboard para enviar `claim_code`. Sprint 16 agrega registro de usuario final, `returnTo` seguro, integracion onboarding -> registro/login y UX post-vinculacion hacia perfil. Sprint 17 agrega readiness productivo, consentimiento explicito, bloqueo de publicacion incompleta, endpoint privado de readiness, endpoint publico endurecido y progreso en dashboard. Sprint 18 migra auth a sesiones server-side con cookie HttpOnly y CSRF double-submit.

`device_type="qr_nfc_tag"` existe como base del modelo de dispositivo. QR Foundation ya existe; NFC todavia no esta implementado.

## CodeGraph

CodeGraph esta inicializado y operativo para este proyecto. OpenCode tiene integracion MCP con herramientas `codegraph_*`, que deben usarse para busquedas estructurales del proyecto antes de cambios relevantes.

La carpeta `.codegraph/` no debe modificarse manualmente ni subirse como indice del proyecto.
