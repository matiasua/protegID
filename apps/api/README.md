# ProtegID API

Backend FastAPI para ProtegID.

## Endpoints actuales

- `GET /api/health`
- `GET /api/ready`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

## Auth Foundation

El backend incluye modelo `User`, tabla `users`, hashing de passwords con Argon2 mediante `pwdlib` y JWT access token.

Variables requeridas para JWT:

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

`password_hash` no se expone en respuestas. Passwords y tokens no deben loguearse.

No hay refresh token, recuperacion de password ni MFA.

## Ejemplos curl

Register:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"change-me-123","full_name":"Example User"}'
```

Login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"change-me-123"}'
```

Me:

```bash
curl http://localhost:8000/api/auth/me \
  -H 'Authorization: Bearer <access_token>'
```

## Limites actuales

No hay devices, QR, perfil medico, contactos de emergencia ni notificaciones.
