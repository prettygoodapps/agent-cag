# Configuration Parameterization Guide

## ⚠️ SECURITY NOTICE

**IMPORTANT**: Environment files containing API keys and sensitive configuration are automatically excluded from git tracking via `.gitignore`. Never commit files containing:
- API keys (Groq, OpenAI, etc.)
- Database passwords
- Authentication tokens
- Private keys or certificates

The following files are ignored and should remain local only:
- `.env`
- `.env.development`
- `.env.production`
- `.env.groq`
- `.env.custom`
- Any `.env.*` files

Only `.env.example` (template without sensitive data) should be committed to version control.

---

This guide explains how to use parameterized YAML configurations instead of hard-coded values in your Agent CAG project.

## Overview

The project now supports multiple parameterization approaches:

1. **Environment Variables** - Using `.env` files with Docker Compose
2. **Environment-Specific Configurations** - Separate configs for dev/prod
3. **Template-Based Configuration** - Using tools like `envsubst` or Helm
4. **Runtime Configuration** - Dynamic configuration loading

## 1. Environment Variables with Docker Compose

### Files Created:
- [`.env.example`](.env.example) - Template with all available variables
- [`.env.development`](.env.development) - Development-specific values
- [`.env.production`](.env.production) - Production-specific values
- [`docker-compose.parameterized.yml`](docker-compose.parameterized.yml) - Parameterized main compose file
- [`docker-compose.monitoring.parameterized.yml`](docker-compose.monitoring.parameterized.yml) - Parameterized monitoring setup
- [`monitoring/prometheus.parameterized.yml`](monitoring/prometheus.parameterized.yml) - Parameterized Prometheus config

### Usage:

#### For Development:
```bash
# Copy development configuration
cp .env.development .env

# Or use Groq API (recommended - faster, no local resources needed)
./configure.sh setup groq

# Start services with parameterized configuration
./configure.sh start lightweight

# With monitoring
./configure.sh start monitoring
```

#### For Production:
```bash
# Copy production configuration
cp .env.production .env

# Edit .env to set secure passwords
nano .env

# Start services
docker-compose -f docker-compose.parameterized.yml up -d
```

#### Custom Configuration:
```bash
# Override specific variables
export API_PORT=9000
export LLM_MODEL_NAME=llama3:13b

# Or create custom .env file
echo "API_PORT=9000" > .env.custom
echo "LLM_MODEL_NAME=llama3:13b" >> .env.custom

# Use custom configuration
docker-compose --env-file .env.custom -f docker-compose.parameterized.yml up -d
```

## 2. Groq API Integration

### Why Groq?
- **Ultra-fast inference**: 10x faster than local Ollama
- **No local resources**: No GPU/CPU intensive LLM processing
- **Generous free tier**: 14,400 requests/day, 6,000 requests/hour
- **High-quality models**: Llama 3.1, Mixtral, Gemma 2

### Setup Steps:
1. **Get API Key**: Visit [console.groq.com](https://console.groq.com)
2. **Sign up/Login**: Use Google, GitHub, or email
3. **Create API Key**: Go to API Keys section → Create API Key
4. **Configure**: Run `./configure.sh setup groq`
5. **Update Key**: Edit `.env` and replace `your_groq_api_key_here` with your actual key

### Available Models:
- `llama-3.1-8b-instant` - Fast, lightweight (development)
- `llama-3.1-70b-versatile` - High quality (production)
- `mixtral-8x7b-32768` - Good balance of speed/quality
- `gemma2-9b-it` - Efficient for simple tasks

### Usage:
```bash
# Setup Groq configuration
./configure.sh setup groq

# Edit .env to add your API key
nano .env  # Replace LLM_API_KEY=your_groq_api_key_here

# Start services (no Ollama container needed)
./configure.sh start lightweight

# Check status
./configure.sh status
```

## 3. Advanced Parameterization Methods

### A. Using envsubst for Template Processing

Create template files and process them at runtime:

```bash
# Create a template
envsubst < docker-compose.parameterized.yml > docker-compose.processed.yml

# Use the processed file
docker-compose -f docker-compose.processed.yml up -d
```

### B. Using External Configuration Management

#### With Consul Template:
```bash
# Install consul-template
# Create template files with Consul KV syntax
# Process templates: consul-template -template="config.yml.tpl:config.yml"
```

#### With Kubernetes ConfigMaps:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-cag-config
data:
  API_PORT: "8000"
  LLM_MODEL_NAME: "phi3:mini"
```

### C. Using Docker Secrets (Production)

```yaml
# In docker-compose.yml
secrets:
  neo4j_password:
    external: true
  grafana_password:
    external: true

services:
  api:
    secrets:
      - neo4j_password
    environment:
      - NEO4J_PASSWORD_FILE=/run/secrets/neo4j_password
```

## 4. Configuration Variables Reference

### Port Configuration
- `API_PORT` - API service port (default: 8000)
- `ASR_PORT` - ASR service port (default: 8001)
- `LLM_PORT` - LLM service port (default: 8002)
- `TTS_PORT` - TTS service port (default: 8003)
- `SARDAUKAR_PORT` - Sardaukar service port (default: 8004)
- `OLLAMA_PORT` - Ollama service port (default: 11434)
- `PROMETHEUS_PORT` - Prometheus port (default: 9090)
- `GRAFANA_PORT` - Grafana port (default: 3000)

### Service URLs
- `ASR_SERVICE_URL` - ASR service endpoint
- `LLM_SERVICE_URL` - LLM service endpoint
- `TTS_SERVICE_URL` - TTS service endpoint
- `SARDAUKAR_TRANSLATOR_URL` - Sardaukar translator endpoint

### Model Configuration
- `WHISPER_MODEL` - Whisper ASR model (base, small, medium, large)
- `LLM_MODEL_NAME` - LLM model name (phi3:mini, llama3:8b, etc.)
- `PIPER_MODEL` - TTS voice model
- `OLLAMA_HOST` - Ollama service host

### Database Configuration
- `NEO4J_URI` - Neo4j connection string
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password
- `CHROMA_HOST` - ChromaDB host
- `CHROMA_PORT` - ChromaDB port

### Monitoring Configuration
- `GRAFANA_ADMIN_USER` - Grafana admin username
- `GRAFANA_ADMIN_PASSWORD` - Grafana admin password
- `PROMETHEUS_RETENTION` - Metrics retention period
- `METRICS_SCRAPE_INTERVAL` - Global scrape interval
- `SERVICE_SCRAPE_INTERVAL` - Service-specific scrape interval

### Deployment Configuration
- `DEPLOYMENT_PROFILE` - Deployment profile (lightweight, full)
- `SARDAUKAR_ENABLED` - Enable Sardaukar translator
- `METRICS_ENABLED` - Enable metrics collection

### Health Check Configuration
- `HEALTH_CHECK_INTERVAL` - Health check frequency
- `HEALTH_CHECK_TIMEOUT` - Health check timeout
- `HEALTH_CHECK_RETRIES` - Health check retry count
- `HEALTH_CHECK_START_PERIOD` - Initial health check delay

## 5. Best Practices

### Security
1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use Docker secrets** for sensitive data in production
3. **Rotate passwords regularly**
4. **Use strong, unique passwords** for each environment

### Environment Management
1. **Use descriptive variable names**
2. **Provide sensible defaults** with `${VAR:-default}` syntax
3. **Document all variables** in `.env.example`
4. **Validate configurations** before deployment

### Deployment
1. **Test configurations** in staging first
2. **Use CI/CD pipelines** to manage environment-specific configs
3. **Monitor configuration drift**
4. **Backup configurations** along with data

## 6. Migration from Hard-coded Values

To migrate your existing setup:

1. **Backup current configurations**:
   ```bash
   cp docker-compose.yml docker-compose.yml.backup
   ```

2. **Replace with parameterized versions**:
   ```bash
   mv docker-compose.parameterized.yml docker-compose.yml
   mv docker-compose.monitoring.parameterized.yml docker-compose.monitoring.yml
   mv monitoring/prometheus.parameterized.yml monitoring/prometheus.yml
   ```

3. **Set up environment file**:
   ```bash
   cp .env.development .env
   # Edit .env as needed
   ```

4. **Test the setup**:
   ```bash
   docker-compose config  # Validate configuration
   docker-compose up -d   # Start services
   ```

## 7. Troubleshooting

### Common Issues:

1. **Variable not substituted**:
   - Check variable name spelling
   - Ensure `.env` file is in the same directory as `docker-compose.yml`
   - Use `docker-compose config` to see resolved values

2. **Service fails to start**:
   - Check logs: `docker-compose logs <service_name>`
   - Verify environment variable values
   - Ensure required variables are set

3. **Port conflicts**:
   - Check if ports are already in use: `netstat -tulpn | grep <port>`
   - Modify port variables in `.env`

### Debugging Commands:
```bash
# Show resolved configuration
docker-compose config

# Show environment variables for a service
docker-compose exec <service> env

# Validate specific compose file
docker-compose -f docker-compose.parameterized.yml config
```

This parameterized approach provides flexibility, security, and maintainability for your Agent CAG deployment across different environments.