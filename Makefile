.PHONY: up down logs ps build restart api-shell web-shell

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
