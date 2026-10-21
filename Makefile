SHELL := /bin/bash

.PHONY: build up down logs restart shell health clean dev dev-backend dev-frontend lint test

IMAGE_NAME ?= trendy-ai
CONTAINER_NAME ?= trendy-ai-app
APP_PORT ?= 3000
export IMAGE_NAME CONTAINER_NAME APP_PORT

# Docker
build:
	@source frontend/.env.local 2>/dev/null || true; \
	docker build \
		--build-arg NEXT_PUBLIC_STORAGE_PUBLIC_URL="$${NEXT_PUBLIC_STORAGE_PUBLIC_URL:-http://127.0.0.1:9000}" \
		--build-arg NEXT_SERVER_API_URL="$${NEXT_SERVER_API_URL:-http://127.0.0.1:8000}" \
		-t $(IMAGE_NAME):latest .

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker logs -f $(CONTAINER_NAME)

restart: down up

shell:
	docker exec -it $(CONTAINER_NAME) bash

health:
	@docker inspect --format='{{.State.Health.Status}}' $(CONTAINER_NAME) 2>/dev/null || echo "Container not running"

clean:
	docker compose down
	-docker rmi $(IMAGE_NAME):latest 2>/dev/null

# Local development (no Docker)
dev-backend:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Run in two terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

# Quality
lint:
	cd backend && ruff check .
	cd frontend && npm run lint

test:
	cd backend && pytest
