# Makefile for Python Microservice
# Customize this for your team's specific service

.PHONY: help install install-dev format lint build run docker-build docker-run docker-compose-up docker-compose-down clean proto

# Default target
help: ## Show this help message
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development setup
install: ## Install production dependencies
	pip install .

install-dev: ## Install development dependencies
	pip install -e ".[dev,docs]"
	pre-commit install

# Code quality
format: ## Format code with black and isort
	black src
	isort src

lint: ## Lint code with flake8 and mypy
	flake8 src
	mypy src

# Testing removed - not needed in this repo yet

# Protocol Buffers (optional - customize for your service)
proto: ## Generate gRPC code from proto files
	python -m grpc_tools.protoc \
        --python_out=src/generated \
        --grpc_python_out=src/generated \
        --proto_path=proto \
        proto/*.proto
	@echo "Generated gRPC code in src/generated/"

# Build and run
build: ## Build the application (install deps)
	@echo "Building application..."
	$(MAKE) install

run: ## Run your service (customize the command)
	@echo "Note: Update this command for your specific service"
	# TODO: Replace with your actual run command
	# python -m src.server
	# flask run --host=0.0.0.0 --port=5000
	# uvicorn src.server:app --host=0.0.0.0 --port=5000

run-client: ## Run example client (customize if needed)
	@echo "Note: Update this for your service's client"
	# python scripts/example_client.py

# Docker
docker-build: ## Build Docker image
	@echo "Building Docker image for your service..."
	docker build -t your-service:latest .

docker-run: ## Run Docker container
	@echo "Note: Update port mapping for your service"
	docker run -p 5000:5000 your-service:latest

docker-compose-up: ## Start all services with docker-compose
	docker-compose up -d
	docker-compose logs -f your-service

docker-compose-down: ## Stop all services
	docker-compose down

docker-compose-logs: ## Show logs from all services
	docker-compose logs -f

# Development workflow
dev-setup: install-dev ## Complete development setup
	@echo "Development environment ready!"
	@echo "Next steps:"
	@echo "1. Define your service in proto/ (if using gRPC) or src/"
	@echo "2. Update Dockerfile for your dependencies"
	@echo "3. Update docker-compose.yml for your database/services"
	@echo "4. Run 'make run' to start your service"

check: format lint ## Run all code quality checks
	@echo "All checks passed!"

# Utilities
clean: ## Clean up generated files and caches
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

# Team coordination helpers
team-setup: ## Help message for team setup
	@echo "Team Setup Guide:"
	@echo "1. Each member should customize src/ files for their domain"
	@echo "2. Update requirements.txt with needed dependencies"
	@echo "3. Configure database in docker-compose.yml"
	@echo "4. Update Dockerfile for your service's needs"
	@echo "5. Define API contract in proto/ (if using gRPC) or REST endpoints"

team-db: ## Start just the database for development
	@echo "Starting database for development..."
	@echo "Note: Uncomment database service in docker-compose.yml first"
	# docker-compose up -d db

# Release
version: ## Show current version
	@python -c "import src; print(f'Version: {src.__version__}')"

# Optional: Remove if not using Kubernetes
k8s-apply: ## Apply Kubernetes manifests
	kubectl apply -f deployments/k8s/

k8s-delete: ## Delete Kubernetes resources
	kubectl delete -f deployments/k8s/