# Agent CAG Build System

This document describes the comprehensive build and deployment system for the Agent CAG project, implementing the architecture outlined in [`BUILD_PLAN.md`](BUILD_PLAN.md).

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Make (for automation commands)

### System Requirements Check

**IMPORTANT**: Before deploying, run the system requirements checker to ensure your system can handle the framework:

```bash
# Check system compatibility and get deployment recommendations
make check-system
```

This will analyze your system and recommend the optimal deployment mode based on:
- Available RAM and disk space
- Docker configuration
- GPU availability
- Ollama installation status

### Basic Usage

```bash
# Check system requirements first (recommended)
make check-system

# Start lightweight profile (DuckDB + containerized Ollama)
make up-light

# Start full profile (requires docker-compose.full.yml - not currently implemented)
# make up-full

# Start with local Ollama (requires Ollama installed on host)
make up-local

# Start with monitoring
make up-monitoring

# Run tests
make test-unit
make test-integration

# Run benchmarks
make benchmark

# Stop all services
make down
```

## Architecture Overview

The system supports multiple deployment profiles and Ollama deployment modes:

### Deployment Profiles
- **Lightweight**: Uses DuckDB for embedded storage (minimal external dependencies)
- **Full**: Uses ChromaDB and Neo4j for scalable storage
- **Monitoring**: Adds Prometheus and Grafana for observability

### Ollama Deployment Modes
- **Containerized** (default): Ollama runs as a Docker service with GPU passthrough
- **Local**: Ollama runs on the host machine (requires manual installation)

## Services

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Main orchestration service |
| ASR Service | 8001 | Speech-to-text using Whisper |
| LLM Service | 8002 | Text generation using Ollama |
| TTS Service | 8003 | Text-to-speech with Sardaukar integration |
| Sardaukar Translator | 8004 | Fictional language translation |
| Ollama | 11434 | LLM inference engine (containerized mode) |
| ChromaDB | 8005 | Vector database (full profile) |
| Neo4j | 7474/7687 | Graph database (full profile) |
| Prometheus | 9090 | Metrics collection (monitoring) |
| Grafana | 3000 | Metrics visualization (monitoring) |

## Deployment Profiles

### Lightweight Profile

Perfect for development, testing, or resource-constrained environments:

```bash
make up-light
```

Features:
- Single DuckDB file for all data storage
- Containerized Ollama with GPU support
- Minimal external dependencies
- Fast startup time
- Self-contained deployment

### Full Profile

**Note: Full profile is currently not implemented. The `docker-compose.full.yml` file does not exist.**

For future implementation, this would be designed for production deployments requiring scalability with:
- ChromaDB for vector similarity search
- Neo4j for graph relationships
- Containerized Ollama with GPU support
- Horizontal scaling capabilities
- Advanced query performance

### Monitoring Profile

Adds comprehensive observability to any profile:

```bash
make up-monitoring          # Lightweight + monitoring
# make up-full-monitoring   # Full + monitoring (requires full profile implementation)
```

Features:
- Prometheus metrics collection
- Grafana dashboards
- Performance comparison tools
- Real-time system monitoring

## Ollama Deployment Modes

### Containerized Ollama (Default)

The recommended deployment mode runs Ollama as a containerized service:

```bash
make up-light    # Uses containerized Ollama
make up-full     # Uses containerized Ollama
```

**Advantages:**
- Self-contained deployment
- GPU passthrough support
- Consistent environment
- Easy scaling and management
- No host dependencies

**Requirements:**
- Docker with GPU support (NVIDIA Container Toolkit)
- Sufficient disk space for models (stored in `ollama_data` volume)

### Local Ollama Mode

For users who prefer to run Ollama on the host machine:

```bash
# First, install and start Ollama on your host
ollama serve

# Then start the system with local mode
make up-local
```

**Advantages:**
- Direct access to host GPU
- Shared models across multiple projects
- Easier model management
- Lower memory overhead

**Requirements:**
- Ollama installed on host machine
- Ollama service running (`ollama serve`)
- Models downloaded locally (`ollama pull llama3`)

### Switching Between Modes

You can easily switch between deployment modes:

```bash
# Stop current deployment
make down

# Start with containerized Ollama (default)
make up-light

# Or start with local Ollama
make up-local
```

**Note:** The system automatically detects the Ollama mode and configures the LLM service accordingly.

## System Requirements Checker

The Agent CAG framework includes a comprehensive system requirements checker that analyzes your host system before deployment. This helps prevent deployment failures and ensures optimal performance.

### Running the System Check

```bash
# Basic system check with recommendations
make check-system

# Save detailed report to JSON file
python3 check_system.py --save-report
```

### What It Checks

The system checker analyzes:

1. **System Resources**
   - Available RAM and disk space
   - CPU cores and architecture
   - Operating system compatibility

2. **Docker Configuration**
   - Docker installation and version
   - Docker daemon status
   - Docker Compose availability
   - User permissions (docker group membership)
   - GPU support (NVIDIA Container Toolkit)

3. **Ollama Status**
   - Local Ollama installation
   - Running status and available models
   - Version compatibility

4. **GPU Capabilities**
   - NVIDIA GPU detection
   - Driver version and CUDA support
   - Available GPU memory

### Deployment Recommendations

Based on the analysis, the checker provides specific recommendations:

- **Containerized Ollama**: For systems with sufficient resources and Docker GPU support
- **Local Ollama**: For systems with limited RAM or existing Ollama installations
- **Lightweight Profile**: For development and testing environments
- **Full Profile**: For production deployments with adequate resources

### Example Output

```
🚀 AGENT CAG SYSTEM REQUIREMENTS REPORT  (EXAMPLE)
================================================================================

📊 SYSTEM INFORMATION
CPU: x86_64 (6 cores)
Memory: 7.6GB total, 2.4GB available
Disk: 92.7GB free of 270.0GB total

🎯 DEPLOYMENT PROFILE ANALYSIS
✓ Local Ollama Mode (GOOD)
✗ Lightweight Profile (LIMITED) - Insufficient RAM
✗ Full Profile (LIMITED) - Insufficient RAM

💡 RECOMMENDATIONS
1. Recommended deployment: make up-local
2. Consider closing other applications to free up memory
```

### Troubleshooting Common Issues

The system checker helps identify and resolve common deployment issues:

- **Docker daemon not running**: Provides commands to start Docker
- **Permission issues**: Suggests adding user to docker group
- **Insufficient resources**: Recommends appropriate profiles
- **GPU setup**: Guides NVIDIA Container Toolkit installation
- **Port conflicts**: Detects running services on required ports

## Sardaukar Integration

The system integrates with the Sardaukar translator for fictional language support:

1. **Automatic Translation**: When `use_sardaukar=true` in TTS requests, English text is automatically translated to Sardaukar before speech synthesis
2. **Fallback Handling**: If translation fails, the system gracefully falls back to English
3. **Performance Monitoring**: Sardaukar translation requests are tracked in metrics

### Example Usage

```bash
# Query with Sardaukar speech output
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you?",
    "user_id": "test-user",
    "generate_speech": true,
    "use_sardaukar": true
  }'
```

## Testing

### Unit Tests

Test individual service components:

```bash
make test-unit
```

Located in `tests/unit/` directory, these tests mock external dependencies and focus on business logic.

### Integration Tests

Test the complete system pipeline:

```bash
make test-integration
```

Located in `integration_tests/` directory, these tests verify:
- Service-to-service communication
- End-to-end workflows
- Error handling
- Performance characteristics

### Benchmarking

Performance testing and comparison:

```bash
make benchmark
```

Features:
- Response time measurements
- Throughput testing
- Concurrent load testing
- Profile comparison reports
- Results saved to `benchmark/results/`

## Development

### Local Development Setup

```bash
# Create development environment
make dev-setup

# Activate virtual environment
source venv/bin/activate

# Start services for development
make up-light
```

### Adding New Services

1. Create service directory: `mkdir new-service`
2. Add `Dockerfile` and `requirements.txt`
3. Implement FastAPI application with health check
4. Add service to `docker-compose.yml`
5. Update `Makefile` if needed
6. Add tests in `tests/unit/test_new_service.py`

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Monitoring and Observability

### Metrics

Each service exposes Prometheus metrics on `/metrics` endpoint:

- Request counts and rates
- Response times and latencies
- Error rates and types
- Custom business metrics

### Dashboards

Grafana dashboards provide:

- System overview
- Service-specific metrics
- Performance comparisons
- Alert configurations

Access Grafana at http://localhost:3000 (admin/admin)

### Health Checks

All services implement health checks:

```bash
# Check all service health
make health

# Individual service health
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Cloud Deployment

### Container Registry

Push images to your registry:

```bash
make push REGISTRY=your-registry.com/agent-cag
```

### Kubernetes

**Note: Kubernetes deployment files are not currently implemented. The `k8s/` directory does not exist.**

For future implementation, Kubernetes deployment would be available via:
```bash
# Deploy to Kubernetes (when implemented)
# make deploy-cloud
```

### Environment Variables

Key configuration variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEPLOYMENT_PROFILE` | Storage backend | `lightweight` |
| `OLLAMA_HOST` | Ollama server URL | `http://ollama:11434` |
| `OLLAMA_MODE` | Ollama deployment mode | `containerized` |
| `MODEL_NAME` | LLM model name | `llama3` |
| `SARDAUKAR_ENABLED` | Enable Sardaukar translation | `false` |
| `METRICS_ENABLED` | Enable Prometheus metrics | `false` |
| `WHISPER_MODEL` | Whisper model size | `base` |

## Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker daemon and available ports
2. **Database connection errors**: Ensure profile-specific services are running
3. **Slow responses**: Check resource allocation and model sizes
4. **Translation failures**: Verify Sardaukar translator service health

### Logs

View service logs:

```bash
# All services
make logs

# Specific service
docker-compose logs -f api
docker-compose logs -f llm
```

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Restart services
make down && make up-light
```

## Performance Optimization

### Resource Allocation

Adjust Docker resource limits in `docker-compose.yml`:

```yaml
services:
  llm:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

### Model Selection

Choose appropriate model sizes:

- **Whisper**: `tiny`, `base`, `small`, `medium`, `large`
- **LLM**: Depends on available models in Ollama

### Caching

The system implements several caching layers:

- Database query results
- Model inference results
- Generated audio files

## Security Considerations

- Services run as non-root users
- No sensitive data in environment variables
- Health checks don't expose internal details
- Network isolation between services
- Regular security updates for base images

## Contributing

1. Follow the established patterns for new services
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure monitoring metrics are included
5. Test both lightweight and full profiles

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review service logs
3. Run health checks
4. Check the monitoring dashboards
5. Create an issue with detailed information

---

This build system provides a robust, scalable, and observable foundation for the Agent CAG project, supporting development, testing, and production deployment scenarios.