# Admin Startpage - Makefile for Docker operations

.PHONY: help build up down restart logs logs-follow clean ps test health

# Default target
help:
	@echo "Admin Startpage - Docker Management"
	@echo ""
	@echo "Available targets:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all containers"
	@echo "  make up-connector - Start with Windows Connector"
	@echo "  make up-proxy    - Start with Nginx proxy"
	@echo "  make down        - Stop all containers"
	@echo "  make restart     - Restart all containers"
	@echo "  make logs        - Show container logs"
	@echo "  make logs-follow - Follow container logs (Ctrl+C to stop)"
	@echo "  make ps          - Show running containers"
	@echo "  make health      - Show health status"
	@echo "  make clean       - Remove containers and volumes"
	@echo "  make test        - Run tests"

# Build images
build:
	docker-compose build

# Start containers (default: web only)
up:
	docker-compose up -d

# Start with connector
up-connector:
	docker-compose --profile connector up -d

# Start with nginx proxy
up-proxy:
	docker-compose --profile proxy up -d

# Stop containers
down:
	docker-compose down

# Restart containers
restart:
	docker-compose restart

# Show logs
logs:
	docker-compose logs --tail=100

# Follow logs
logs-follow:
	docker-compose logs -f

# Show running containers
ps:
	docker-compose ps

# Show health status
health:
	@echo "=== Web Backend ==="
	@curl -s http://localhost:8080/api/health | python -m json.tool 2>/dev/null || echo "Not running"
	@echo ""
	@echo "=== Connector (if running) ==="
	@curl -s http://localhost:8090/health | python -m json.tool 2>/dev/null || echo "Not running"

# Clean up
clean:
	docker-compose down -v
	rm -rf data/*

# Run tests
test:
	docker-compose exec -T startpage-web python -m pytest tests/ -v

# Production deployment
deploy-prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Development mode (with hot reload)
dev:
	docker-compose up

# Show version info
version:
	@echo "Admin Startpage $(shell git describe --tags --always)"
	@docker-compose version