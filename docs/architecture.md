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

PostgreSQL, Redis y MinIO quedan disponibles para funcionalidades actuales y futuras. Alembic esta configurado y el backend ya incluye la tabla de negocio `users` para la base de autenticacion.

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

## Limites de esta etapa

No se implementan devices, QR, perfil medico, contactos de emergencia, notificaciones, refresh token, recuperacion de password ni MFA.

## CodeGraph

CodeGraph esta inicializado y operativo para este proyecto. OpenCode tiene integracion MCP con herramientas `codegraph_*`, que deben usarse para busquedas estructurales del proyecto antes de cambios relevantes.

La carpeta `.codegraph/` no debe modificarse manualmente ni subirse como indice del proyecto.
