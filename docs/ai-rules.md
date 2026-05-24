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
- Toda futura tabla debe tener migracion.
- Todo futuro endpoint debe usar schemas/validaciones.
- No modificar Auth Foundation sin justificacion explicita de producto o seguridad.

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

Auth Foundation ya existe e incluye modelo `User`, tabla `users`, hashing de passwords, JWT access token y endpoints `register`, `login` y `me`.

Device Foundation ya existe e incluye modelo `Device`, tabla `devices`, relacion nullable `devices.user_id -> users.id`, generacion de `public_id` con formato `PID-XXXXXXXXXX` y endpoints protegidos basicos de devices.

Public Profile Foundation ya existe e incluye modelo `EmergencyProfile`, tabla `emergency_profiles`, relacion unica `emergency_profiles.device_id -> devices.id`, endpoints privados para ver/crear/editar el perfil de un device y endpoint publico de lectura por `public_id`.

QR Foundation ya existe e incluye configuracion `PUBLIC_APP_URL` y `PUBLIC_PROFILE_PATH`, helper `build_public_profile_url(public_id)`, generacion de QR PNG en memoria con `qrcode[pil]`, persistencia en MinIO/S3 compatible y object key estable `qr/devices/{public_id}.png`.

El QR no debe contener datos medicos. El QR debe contener solo la URL publica `{PUBLIC_APP_URL}{PUBLIC_PROFILE_PATH}/{public_id}`. Ejemplo local: `http://localhost:8080/p/PID-XXXXXXXXXX`.

Public Profile Frontend ya existe en `/p/{public_id}`. La pagina no requiere login, consulta server-side `GET /api/public/profiles/{public_id}`, responde `200 OK` si el perfil esta disponible y responde `404` real con `notFound()` si no lo esta. No expone IDs internos, `device_id`, timestamps ni `deleted_at`; solo muestra datos de `EmergencyProfilePublicRead`. El 404 no debe revelar si el `public_id` existe o no.

La vista publica debe mantenerse como ficha de emergencia mobile-first: tipo de sangre destacado, contacto y telefono de emergencia destacados, secciones claras y campos vacios como `No informado`.

Sprint 9 agrega UX Hardening & Navigation. `/` funciona como landing inicial del MVP, incluye accesos a `/login` y `/dashboard`, explica el flujo activar identificador, completar perfil de emergencia y compartir acceso publico mediante QR/NFC, muestra el estado actual del MVP e incluye la nota `Este MVP aún no reemplaza credenciales oficiales ni atención médica profesional.`.

Auth Frontend Foundation ya existe. `/login` permite ingresar email y password, consume `POST /api/auth/login`, recibe `access_token` y `token_type`, guarda `access_token` temporalmente en `sessionStorage` con key `protegid_access_token` y muestra el token en `textarea` readonly por transparencia temporal del MVP. `/login` muestra estados de carga, exito y error; `401` muestra credenciales invalidas. `/login` tiene `Volver al inicio`, detecta sesion temporal existente, muestra `Ya existe una sesión temporal activa.`, permite ir al dashboard, permite cerrar sesion temporal y despues de login exitoso muestra `Continuar al dashboard` sin redireccion automatica.

Private Profile Management Frontend ya existe en `/dashboard`. Lee automaticamente el token desde `sessionStorage` con `getSessionToken()`, valida contra `GET /api/auth/me`, carga dispositivos con `GET /api/devices`, permite seleccionar un dispositivo, carga perfil privado con `GET /api/devices/{device_id}/emergency-profile` y crea/actualiza con `PUT /api/devices/{device_id}/emergency-profile`. Si no hay sesion muestra estado no autenticado y boton/link `Ir a login`. Mantiene fallback tecnico reducido como `Usar token manual` y tiene boton `Cerrar sesion` con `clearSessionToken()`. `/dashboard` tiene `Volver al inicio`.

La sesion frontend actual es temporal para MVP. Usa `sessionStorage`, no `localStorage`, no cookies, no refresh token, no middleware de proteccion y no expiracion/renovacion automatica desde frontend. El backend sigue validando Bearer token en endpoints privados. El token vive solo durante la sesion/pestana del navegador y `sessionStorage` no se comparte entre pestanas. Para produccion se evaluara una estrategia mas robusta.

Campos del perfil privado actual: `display_name`, `blood_type`, `allergies`, `medical_conditions`, `medications`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes` e `is_public`. `is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.

La UX actual incluye `/login` con estados de carga, exito y error, deteccion de sesion temporal existente, cierre de sesion temporal y continuidad manual al dashboard. `/dashboard` esta organizado en estado de sesion, dispositivos, editor de perfil y fallback tecnico. Los dispositivos muestran `public_id`, status visual y seleccion. El editor agrupa Datos personales, Informacion medica, Contacto de emergencia y Visibilidad publica.

QR Management Frontend ya existe en `/dashboard`. Consulta estado QR por dispositivo con `GET /api/admin/devices/{device_id}/qr`, muestra `QR generado`, `QR pendiente`, `QR no disponible`, `Consultando QR...` y `Generando QR...`, y permite generar/regenerar QR con `POST /api/admin/devices/{device_id}/qr` para usuarios admin.

Si el usuario no es admin o QR responde `403`, `/dashboard` muestra `La gestión de QR requiere rol admin.` y debe seguir mostrando devices/perfil. El backend sigue siendo la fuente de autorizacion.

El QR apunta a `/p/{public_id}` y solo contiene la URL publica del perfil. No incluye datos medicos embebidos. La visualizacion depende de que el perfil este marcado como publico. `object_key` puede mostrarse como detalle tecnico, pero no se debe implementar descarga PNG, presigned URLs, preview de imagen QR, apertura de MinIO, NFC funcional, tracking, geolocalizacion ni notificaciones salvo solicitud explicita.

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
- Prueba GUI: login con usuario de prueba, confirmar `protegid_access_token` en `sessionStorage`, abrir `/dashboard` en la misma pestana, confirmar carga automatica de usuario/devices y cerrar sesion.
- Usuario admin: ve estado QR y puede generar/regenerar QR.
- Usuario no admin: ve `La gestión de QR requiere rol admin.` y el dashboard sigue mostrando devices/perfil.

Estados de device existentes:

- `pending_activation`
- `active`
- `disabled`
- `lost`

Endpoints de devices existentes:

- `GET /api/devices`
- `POST /api/devices/activate`
- `POST /api/admin/devices`

Endpoints de perfiles de emergencia existentes:

- `GET /api/devices/{device_id}/emergency-profile`
- `PUT /api/devices/{device_id}/emergency-profile`
- `GET /api/public/profiles/{public_id}`

Endpoints admin de QR existentes:

- `GET /api/admin/devices/{device_id}/qr`
- `POST /api/admin/devices/{device_id}/qr`

El endpoint publico no requiere autenticacion, busca por `Device.public_id`, solo responde si el device esta `active`, el perfil tiene `is_public == true` y `deleted_at is null`, y no expone `id`, `device_id`, `created_at`, `updated_at` ni `deleted_at`.

Los endpoints QR requieren Bearer token y `role=admin`. No devuelven el archivo PNG ni entregan presigned URL. Solo devuelven metadata: `device_id`, `public_id`, `object_key`, `content_type` y, para `GET`, `exists`.

No implementar registro frontend completo, recuperacion de password, refresh token, cookies HttpOnly, middleware de proteccion, roles avanzados en frontend, expiracion visual previa del token, subida de archivos medicos, descarga PNG desde frontend, presigned URLs, preview de imagen QR, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, descarga publica de QR, presigned URL publica ni MFA salvo solicitud explicita.

No crear nuevas tablas ni migraciones salvo solicitud explicita.

`device_type="qr_nfc_tag"` existe como base del modelo. QR Foundation ya existe; NFC todavia no esta implementado.
