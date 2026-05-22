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

PostgreSQL, Redis y MinIO quedan disponibles para futuras funcionalidades. Alembic queda configurado con un baseline tecnico vacio; este setup no crea modelos, tablas de negocio ni buckets.

## Limites de esta etapa

No se implementa login, generacion de QR, activacion de dispositivos, modelos de base de datos, identificadores publicos ni logica medica.

## Preparacion para Code Graph

La estructura del repositorio y la documentacion quedan organizadas para poder indexarse posteriormente con Code Graph. Code Graph no esta inicializado ni configurado en esta etapa.
