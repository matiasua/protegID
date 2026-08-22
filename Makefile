.PHONY: up down logs ps build restart api-shell web-shell test-db-up test-db-down test-api

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

build:
	docker compose build

restart:
	docker compose restart

api-shell:
	docker compose exec protegid-api sh

web-shell:
	docker compose exec protegid-web sh

# -p protegid-test es obligatorio: el .env raíz define COMPOSE_PROJECT_NAME=protegid,
# que tiene prioridad sobre el `name:` del compose file y colapsaría este stack
# dentro del proyecto de desarrollo si no se fuerza aquí.
test-db-up:
	docker compose -p protegid-test -f docker-compose.test.yml up -d --wait protegid-db-test protegid-redis-test

test-db-down:
	docker compose -p protegid-test -f docker-compose.test.yml down -v

test-api: test-db-up
	docker compose -p protegid-test -f docker-compose.test.yml run --rm protegid-api-test
