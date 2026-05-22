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

## Estado actual

El estado actual no implementa generacion de QR, escritura NFC, vista publica `/p/{public_id}`, perfil medico, contactos de emergencia, notificaciones, logica de escaneo, refresh token, recuperacion de password ni MFA.

`device_type="qr_nfc_tag"` existe solo como base del modelo de dispositivo, no como implementacion QR/NFC.
