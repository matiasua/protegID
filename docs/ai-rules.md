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

Private Profile Management Frontend inicial ya existe en `/dashboard`. Es una pantalla temporal de validacion manual por access token: permite pegar un JWT, valida contra `GET /api/auth/me`, carga dispositivos con `GET /api/devices`, permite seleccionar un dispositivo, carga perfil privado con `GET /api/devices/{device_id}/emergency-profile` y crea/actualiza con `PUT /api/devices/{device_id}/emergency-profile`.

El token de `/dashboard` debe mantenerse solo en state React hasta que se solicite una solucion de login/sesion. No usar `localStorage`, cookies, refresh token ni sesion persistente sin solicitud explicita.

Campos del perfil privado actual: `display_name`, `blood_type`, `allergies`, `medical_conditions`, `medications`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relationship`, `notes` e `is_public`. `is_public` controla si el perfil puede mostrarse publicamente en `/p/{public_id}`.

La UX actual de `/dashboard` incluye `Panel privado ProtegID`, `Estado de sesion`, `Mis dispositivos`, `Editar perfil`, `Guardar perfil` y estados de carga, error y exito.

Next dev usa `.next-dev`; `next build` usa `.next`. Para validar build frontend sin ensuciar el contenedor dev, usar:

```bash
docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"
```

Validacion esperada de `/dashboard`:

- `GET /dashboard` responde `200 OK`.
- Validacion funcional manual con JWT vigente.

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

No implementar login frontend completo, registro frontend completo, recuperacion de password, refresh token, control de sesion persistente, subida de archivos medicos, gestion de QR desde frontend, NFC funcional, tracking de escaneos, geolocalizacion, notificaciones, descarga publica de QR, presigned URL publica ni MFA salvo solicitud explicita.

No crear nuevas tablas ni migraciones salvo solicitud explicita.

`device_type="qr_nfc_tag"` existe como base del modelo. QR Foundation ya existe; NFC todavia no esta implementado.
