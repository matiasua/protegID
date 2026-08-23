# Verificacion de Email y Proteccion de Abuso

Esta guia describe el flujo tecnico vigente para la version productiva inicial de ProtegID.

## Flujo de Registro y Verificacion

- `POST /api/auth/register` crea un usuario con `email_verified_at=null`.
- El registro no inicia sesion automaticamente.
- El backend genera un token one-time-use con proposito `email_verification`.
- El token raw no se guarda en base de datos.
- La tabla `auth_action_tokens` guarda `token_hash`, `purpose`, `expires_at`, `used_at`, `revoked_at` y el email de destino normalizado.
- Antes de crear un token nuevo se revocan tokens pendientes del mismo usuario/proposito.
- El link enviado por email apunta a `/verify-email?token=...`.
- `POST /api/auth/verify-email` es publico y no requiere CSRF.
- Al verificar correctamente, el usuario queda con `email_verified_at` seteado, el token se marca con `used_at` y se revocan tokens pendientes que ya no correspondan.
- Login se permite aunque `email_verified_at` sea `null`; la verificacion controla acciones criticas, no autenticacion basica.

## Acciones Permitidas y Bloqueadas

Usuarios autenticados pero no verificados pueden:

- Iniciar sesion.
- Consultar `GET /api/auth/me`.
- Ver el dashboard basico.
- Listar sus devices con `GET /api/devices`.
- Reenviar verificacion con `POST /api/auth/resend-verification` usando sesion y CSRF.

Usuarios autenticados pero no verificados no pueden:

- Activar un identificador fisico con `POST /api/devices/activate`.
- Crear devices admin con `POST /api/admin/devices`.
- Editar perfil de emergencia con `PUT /api/emergency-profile`.
- Publicar perfil de emergencia.
- Generar u operar endpoints admin de devices/QR.
- Ejecutar otras mutaciones criticas que usen la dependencia de email verificado.

El frontend solo guia la UX. El backend es la fuente de verdad para autenticacion, autorizacion, verificacion y publicacion.

## CSRF

CSRF usa double-submit para mutaciones autenticadas:

- Cookie `protegid_csrf` legible por JS.
- Header `X-CSRF-Token` en `POST`, `PUT`, `PATCH` y `DELETE` cuando existe cookie de sesion.
- Requests privados sin sesion deben responder `401`.
- Requests con sesion y CSRF faltante/incorrecto deben responder `403 CSRF validation failed`.

Excepciones exactas:

- `POST /api/auth/login` no requiere CSRF porque crea la sesion.
- `POST /api/auth/verify-email` no requiere CSRF porque usa token one-time-use opaco, hasheado en DB, con expiracion, `used_at`, `revoked_at` y proposito `email_verification`.

Endpoints que siguen protegidos por CSRF:

- `POST /api/auth/resend-verification`: requiere sesion y CSRF.
- `POST /api/auth/logout`: requiere CSRF cuando hay sesion.
- `POST /api/devices/activate`: requiere sesion, email verificado y CSRF.
- `PUT /api/emergency-profile`: requiere sesion, email verificado y CSRF.
- `POST /api/admin/devices/{device_id}/qr`: requiere sesion, rol admin, email verificado y CSRF.

## Rate Limiting

Redis es dependencia critica para rate limiting. Si Redis falla, los endpoints criticos responden `503 Rate limit service unavailable.` para fallar cerrado.

Endpoints con rate limiting:

- `POST /api/auth/login`.
- `POST /api/auth/register`.
- `POST /api/auth/resend-verification`.
- `POST /api/auth/verify-email`.
- `POST /api/devices/activate`.
- `GET /api/public/devices/{public_id}/activation-status`.
- `GET /api/public/profiles/{public_id}`.

Reglas de privacidad del rate limit:

- Las keys no guardan email plano.
- Email se normaliza y se hashea con SHA-256 antes de formar keys.
- Redis no guarda tokens raw de verificacion.
- Redis no guarda `claim_code`.
- Las respuestas `429` son genericas: `Too many requests. Try again later.`.

## Mailpit Local

Mailpit permite probar correos de verificacion en desarrollo local.

- UI web: `http://localhost:8025`.
- SMTP interno Docker Compose: `mailpit:1025`.
- SMTP host visto por `protegid-api`: `mailpit`.

Variables locales:

```dotenv
EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=no-reply@protegid.local
SMTP_FROM_NAME=ProtegID
MAILPIT_SMTP_PORT=1025
MAILPIT_WEB_PORT=8025
```

## Entorno Local

Comandos base:

```bash
cp .env.example .env
docker compose up -d
docker compose exec -T protegid-api alembic upgrade head
curl http://localhost:8080/api/health
curl http://localhost:8080/api/ready
```

Despues de levantar servicios, abrir Mailpit en `http://localhost:8025`.

Nota para seeds locales: no usar dominios `.test` en usuarios seed porque `EmailStr` los rechaza como dominio reservado. Usar dominios locales validos como `@protegid.cl`.

## Checklist Sprint 19

- Registrar usuario nuevo.
- Confirmar que el correo llega a Mailpit.
- Verificar email con token valido desde `/verify-email?token=...`.
- Confirmar que token invalido/expirado falla con error controlado.
- Login de usuario no verificado funciona.
- Dashboard muestra banner de email no verificado.
- Reenvio de verificacion desde dashboard funciona.
- Acciones criticas no verificadas devuelven `403`.
- Usuario verificado puede activar identificador y editar perfil como antes.
- Rate limit devuelve `429` al exceder limites.
- `/api/ready` devuelve `database`, `redis` y `minio` en estado `ok`.
- Build web pasa con `docker compose run --rm --no-deps protegid-web sh -lc "rm -rf .next && npm run build"`.

## Seguridad

- Email verification no reemplaza autenticacion.
- Login y sesion siguen dependiendo de credenciales y cookie HttpOnly.
- Frontend solo guia la UX; backend es fuente de verdad.
- El perfil publico solo se muestra si readiness esta operativo.
- No exponer token raw de verificacion.
- No exponer `claim_code`.
- No incluir emails planos en Redis keys.
- No loguear tokens raw, `claim_code`, passwords ni datos medicos.
- Usar HTTPS en produccion.
- Usar `SESSION_COOKIE_SECURE=true` en produccion.
- Recomendado en produccion: `SESSION_COOKIE_NAME=__Host-protegid_session`, `SESSION_COOKIE_PATH=/` y sin `Domain`.
