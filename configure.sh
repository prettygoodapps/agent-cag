#!/bin/bash

# Configuration Management Script for Agent CAG
# This script helps manage parameterized configurations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  setup <env>     Setup environment configuration (dev|prod|groq|custom)"
    echo "  validate        Validate current configuration"
    echo "  start <profile> Start services with profile (lightweight|full|monitoring|monitoring-full)"
    echo "  stop            Stop all services"
    echo "  status          Show service status"
    echo "  logs <service>  Show logs for specific service"
    echo "  backup          Backup current configuration"
    echo "  restore         Restore configuration from backup"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup dev                    # Setup development environment"
    echo "  $0 start lightweight           # Start with lightweight profile"
    echo "  $0 start monitoring            # Start with monitoring enabled"
    echo "  $0 validate                    # Validate configuration"
    echo "  $0 logs api                    # Show API service logs"
}

# Setup environment configuration
setup_env() {
    local env_type="$1"
    
    case "$env_type" in
        "dev"|"development")
            print_info "Setting up development environment..."
            cp .env.development .env
            print_success "Development configuration copied to .env"
            ;;
        "prod"|"production")
            print_info "Setting up production environment..."
            cp .env.production .env
            print_warning "Please review and update passwords in .env file!"
            print_warning "Default passwords should be changed for production use."
            ;;
        "groq")
            print_info "Setting up Groq API environment..."
            cp .env.groq .env
            print_success "Groq configuration copied to .env"
            print_info "Using Groq API for fast LLM inference (no local Ollama needed)"
            ;;
        "custom")
            print_info "Setting up custom environment..."
            cp .env.example .env
            print_info "Template copied to .env - please customize as needed"
            ;;
        *)
            print_error "Invalid environment type. Use: dev, prod, groq, or custom"
            exit 1
            ;;
    esac
    
    print_info "Environment setup complete. You can now run: $0 validate"
}

# Validate configuration
validate_config() {
    print_info "Validating configuration..."
    
    # Check if .env file exists
    if [[ ! -f .env ]]; then
        print_error ".env file not found. Run: $0 setup <env>"
        exit 1
    fi
    
    # Validate Docker Compose configuration
    if docker-compose -f docker-compose.parameterized.yml config > /dev/null 2>&1; then
        print_success "Main configuration is valid"
    else
        print_error "Main configuration validation failed"
        docker-compose -f docker-compose.parameterized.yml config
        exit 1
    fi
    
    # Validate basic monitoring configuration
    if docker-compose -f docker-compose.parameterized.yml -f docker-compose.monitoring.parameterized.yml config > /dev/null 2>&1; then
        print_success "Basic monitoring configuration is valid"
    else
        print_warning "Basic monitoring configuration validation failed"
    fi
    
    # Validate full monitoring configuration
    if docker-compose -f docker-compose.parameterized.yml -f docker-compose.monitoring.full.yml config > /dev/null 2>&1; then
        print_success "Full monitoring configuration is valid"
    else
        print_warning "Full monitoring configuration validation failed"
    fi
    
    # Check for required variables
    source .env
    required_vars=("API_PORT" "ASR_PORT" "LLM_PORT" "TTS_PORT")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            print_warning "Variable $var is not set"
        fi
    done
    
    print_success "Configuration validation complete"
}

# Start services
start_services() {
    local profile="$1"
    
    if [[ ! -f .env ]]; then
        print_error ".env file not found. Run: $0 setup <env>"
        exit 1
    fi
    
    case "$profile" in
        "lightweight"|"light")
            print_info "Starting services with lightweight profile..."
            docker-compose -f docker-compose.parameterized.yml up -d
            ;;
        "full")
            print_info "Starting services with full profile..."
            # Assuming you have a full profile compose file
            docker-compose -f docker-compose.parameterized.yml -f docker-compose.full.yml up -d
            ;;
        "monitoring"|"monitor")
            print_info "Starting services with basic monitoring enabled..."
            docker-compose -f docker-compose.parameterized.yml -f docker-compose.monitoring.parameterized.yml up -d
            ;;
        "monitoring-full"|"monitor-full")
            print_info "Starting services with full monitoring stack (includes ChromaDB and Neo4j)..."
            docker-compose -f docker-compose.parameterized.yml -f docker-compose.monitoring.full.yml up -d
            ;;
        *)
            print_error "Invalid profile. Use: lightweight, full, monitoring, or monitoring-full"
            exit 1
            ;;
    esac
    
    print_success "Services started successfully"
    print_info "Use '$0 status' to check service status"
}

# Stop services
stop_services() {
    print_info "Stopping all services..."
    docker-compose -f docker-compose.parameterized.yml -f docker-compose.monitoring.parameterized.yml down
    print_success "All services stopped"
}

# Show service status
show_status() {
    print_info "Service status:"
    docker-compose -f docker-compose.parameterized.yml ps
}

# Show logs
show_logs() {
    local service="$1"
    if [[ -z "$service" ]]; then
        print_error "Please specify a service name"
        exit 1
    fi
    
    print_info "Showing logs for service: $service"
    docker-compose -f docker-compose.parameterized.yml logs -f "$service"
}

# Backup configuration
backup_config() {
    local backup_dir="config_backup_$(date +%Y%m%d_%H%M%S)"
    print_info "Creating configuration backup in $backup_dir..."
    
    mkdir -p "$backup_dir"
    
    # Backup configuration files
    [[ -f .env ]] && cp .env "$backup_dir/"
    [[ -f docker-compose.yml ]] && cp docker-compose.yml "$backup_dir/"
    [[ -f docker-compose.monitoring.yml ]] && cp docker-compose.monitoring.yml "$backup_dir/"
    [[ -f monitoring/prometheus.yml ]] && cp monitoring/prometheus.yml "$backup_dir/"
    
    print_success "Configuration backed up to $backup_dir"
}

# Restore configuration
restore_config() {
    print_warning "This will restore configuration from the most recent backup"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Restore cancelled"
        exit 0
    fi
    
    # Find most recent backup
    local backup_dir=$(ls -1d config_backup_* 2>/dev/null | sort -r | head -n1)
    
    if [[ -z "$backup_dir" ]]; then
        print_error "No backup found"
        exit 1
    fi
    
    print_info "Restoring from $backup_dir..."
    
    # Restore files
    [[ -f "$backup_dir/.env" ]] && cp "$backup_dir/.env" .env
    [[ -f "$backup_dir/docker-compose.yml" ]] && cp "$backup_dir/docker-compose.yml" docker-compose.yml
    [[ -f "$backup_dir/docker-compose.monitoring.yml" ]] && cp "$backup_dir/docker-compose.monitoring.yml" docker-compose.monitoring.yml
    [[ -f "$backup_dir/monitoring/prometheus.yml" ]] && cp "$backup_dir/monitoring/prometheus.yml" monitoring/prometheus.yml
    
    print_success "Configuration restored from $backup_dir"
}

# Main script logic
case "${1:-help}" in
    "setup")
        setup_env "$2"
        ;;
    "validate")
        validate_config
        ;;
    "start")
        start_services "$2"
        ;;
    "stop")
        stop_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "$2"
        ;;
    "backup")
        backup_config
        ;;
    "restore")
        restore_config
        ;;
    "help"|*)
        show_usage
        ;;
esac