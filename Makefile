.PHONY: help build up-light up-full up-monitoring up-local down clean test-unit test-integration benchmark push deploy-cloud check-system

# Default target
help:
	@echo "Agent CAG Build System"
	@echo "====================="
	@echo ""
	@echo "Available targets:"
	@echo "  check-system       - Check system requirements and compatibility"
	@echo "  build              - Build all Docker images"
	@echo "  up-light           - Start lightweight profile (DuckDB + containerized Ollama)"
	@echo "  up-full            - Start full profile (ChromaDB + Neo4j + containerized Ollama)"
	@echo "  up-monitoring      - Start with monitoring stack"
	@echo "  up-local           - Start lightweight profile with local Ollama"
	@echo "  up-full-monitoring - Start full profile with monitoring"
	@echo "  down               - Stop all services"
	@echo "  clean              - Remove all containers, volumes, and images"
	@echo "  test-unit          - Run unit tests"
	@echo "  test-integration   - Run integration tests"
	@echo "  benchmark          - Run performance benchmarks"
	@echo "  push               - Push images to registry"
	@echo "  deploy-cloud       - Deploy to cloud environment"
	@echo "  logs               - Show logs from all services"
	@echo "  status             - Show status of all services"

# Build all Docker images
build:
	@echo "Building all Docker images..."
	sg docker -c "docker-compose build"
	@echo "Build complete!"

# Start lightweight profile (default)
up-light:
	@echo "Starting lightweight profile with DuckDB and containerized Ollama..."
	sg docker -c "docker-compose up -d"
	@echo "Services started! API available at http://localhost:8000"
	@echo "Run 'make logs' to see service logs"

# Start full profile with dedicated databases
up-full:
	@echo "Starting full profile with ChromaDB, Neo4j, and containerized Ollama..."
	sg docker -c "docker-compose -f docker-compose.yml -f docker-compose.full.yml up -d"
	@echo "Services started!"
	@echo "  API: http://localhost:8000"
	@echo "  ChromaDB: http://localhost:8005"
	@echo "  Neo4j Browser: http://localhost:7474"

# Start with monitoring stack
up-monitoring:
	@echo "Starting lightweight profile with monitoring..."
	sg docker -c "docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d"
	@echo "Services started!"
	@echo "  API: http://localhost:8000"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3000 (admin/admin)"

# Start lightweight profile with local Ollama
up-local:
	@echo "Starting lightweight profile with local Ollama..."
	@echo "Note: Make sure Ollama is running on your host machine (ollama serve)"
	sg docker -c "docker-compose -f docker-compose.yml -f docker-compose.local.yml up -d"
	@echo "Services started! API available at http://localhost:8000"
	@echo "Run 'make logs' to see service logs"

# Start full profile with monitoring
up-full-monitoring:
	@echo "Starting full profile with monitoring..."
	sg docker -c "docker-compose -f docker-compose.yml -f docker-compose.full.yml -f docker-compose.monitoring.yml up -d"
	@echo "Services started!"
	@echo "  API: http://localhost:8000"
	@echo "  ChromaDB: http://localhost:8005"
	@echo "  Neo4j Browser: http://localhost:7474"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3000 (admin/admin)"

# Stop all services
down:
	@echo "Stopping all services..."
	sg docker -c "docker-compose -f docker-compose.yml -f docker-compose.full.yml -f docker-compose.monitoring.yml -f docker-compose.local.yml down"
	@echo "All services stopped!"

# Clean up everything
clean:
	@echo "Cleaning up containers, volumes, and images..."
	sg docker -c "docker-compose -f docker-compose.yml -f docker-compose.full.yml -f docker-compose.monitoring.yml -f docker-compose.local.yml down -v --remove-orphans"
	sg docker -c "docker system prune -f"
	@echo "Cleanup complete!"

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && \
		pip install -r requirements-dev.txt && \
		python -m pytest tests/unit/ -v --tb=short
	@echo "Unit tests complete!"

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	@echo "Starting test environment..."
	sg docker -c "docker-compose -f docker-compose.yml up -d --build"
	@sleep 30  # Wait for services to be ready
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && \
		pip install -r requirements-dev.txt && \
		python -m pytest integration_tests/ -v --tb=short
	@echo "Stopping test environment..."
	@sg docker -c "docker-compose down"
	@echo "Integration tests complete!"

# Run performance benchmarks
benchmark:
	@echo "Running performance benchmarks..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && \
		pip install -r requirements-dev.txt && \
		python benchmark/run_benchmarks.py
	@echo "Benchmarks complete! Check benchmark/results/ for reports."

# Push images to registry
push:
	@echo "Pushing images to registry..."
	@if [ -z "$(REGISTRY)" ]; then \
		echo "Error: REGISTRY environment variable not set"; \
		echo "Usage: make push REGISTRY=your-registry.com/project"; \
		exit 1; \
	fi
	sg docker -c "docker tag agent-cag_api $(REGISTRY)/agent-api:latest"
	sg docker -c "docker tag agent-cag_asr $(REGISTRY)/agent-asr:latest"
	sg docker -c "docker tag agent-cag_llm $(REGISTRY)/agent-llm:latest"
	sg docker -c "docker tag agent-cag_tts $(REGISTRY)/agent-tts:latest"
	sg docker -c "docker push $(REGISTRY)/agent-api:latest"
	sg docker -c "docker push $(REGISTRY)/agent-asr:latest"
	sg docker -c "docker push $(REGISTRY)/agent-llm:latest"
	sg docker -c "docker push $(REGISTRY)/agent-tts:latest"
	@echo "Images pushed to $(REGISTRY)!"

# Deploy to cloud environment
deploy-cloud:
	@echo "Deploying to cloud environment..."
	@if [ ! -f "k8s/kustomization.yaml" ]; then \
		echo "Error: Kubernetes manifests not found in k8s/ directory"; \
		exit 1; \
	fi
	kubectl apply -k k8s/
	@echo "Deployment complete! Check 'kubectl get pods' for status."

# Show logs from all services
logs:
	sg docker -c "docker-compose logs -f"

# Show status of all services
status:
	@echo "Service Status:"
	@echo "==============="
	sg docker -c "docker-compose ps"

# Development helpers
dev-setup:
	@echo "Setting up development environment..."
	@if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && \
		pip install -r requirements-dev.txt
	@echo "Development environment ready!"
	@echo "Activate with: source venv/bin/activate"

# Check system requirements
check-system:
	@echo "Checking system requirements for Agent CAG..."
	@python3 check_system.py

# Quick health check
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "API service not responding"
	@curl -s http://localhost:8001/health || echo "ASR service not responding"
	@curl -s http://localhost:8002/health || echo "LLM service not responding"
	@curl -s http://localhost:8003/health || echo "TTS service not responding"
	@curl -s http://localhost:8004/api/health || echo "Sardaukar translator not responding"