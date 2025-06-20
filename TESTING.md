# Testing Guide for Agent CAG

This document provides comprehensive information about testing the Agent CAG system, including unit tests, integration tests, security tests, load tests, and monitoring tests.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Development Workflow](#development-workflow)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)

## Overview

Agent CAG uses a comprehensive testing strategy that includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions and workflows
- **Security Tests**: Test for vulnerabilities and security issues
- **Load Tests**: Test system performance under load
- **Monitoring Tests**: Test observability and metrics collection
- **End-to-End Tests**: Test complete user workflows

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_api.py         # API service tests
│   ├── test_asr.py         # ASR service tests
│   ├── test_llm.py         # LLM service tests
│   ├── test_tts.py         # TTS service tests
│   └── test_database.py    # Database tests
├── integration/             # Integration tests
│   └── test_enhanced_integration.py
├── security/               # Security tests
│   └── test_security.py
├── monitoring/             # Monitoring tests
│   └── test_monitoring.py
└── load/                   # Load tests
    └── test_load.py

integration_tests/          # Legacy integration tests
└── test_full_pipeline.py

benchmark/                  # Performance benchmarks
└── run_benchmarks.py
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
python run_tests.py --all

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --security
python run_tests.py --monitoring
python run_tests.py --load
```

### Test Runner Options

The `run_tests.py` script provides comprehensive testing capabilities:

```bash
# Basic usage
python run_tests.py [OPTIONS]

# Options:
--unit                  # Run unit tests only
--integration          # Run integration tests only
--security             # Run security tests only
--monitoring           # Run monitoring tests only
--load                 # Run load tests only
--code-quality         # Run code quality checks only
--all                  # Run all tests (default)
--with-load            # Include load tests in full run
--with-services        # Start services for testing
--no-coverage          # Skip coverage reporting
--no-parallel          # Disable parallel test execution
--load-users N         # Number of users for load testing (default: 10)
--load-duration TIME   # Duration for load testing (default: 30s)
--output FILE          # Output file for test report
```

### Examples

```bash
# Run unit tests with coverage
python run_tests.py --unit

# Run integration tests with services
python run_tests.py --integration --with-services

# Run load tests with 50 users for 2 minutes
python run_tests.py --load --load-users 50 --load-duration 2m

# Run all tests including load tests
python run_tests.py --all --with-load --with-services

# Generate detailed report
python run_tests.py --all --output test_report.json
```

### Direct pytest Usage

```bash
# Run specific test files
pytest tests/unit/test_api.py -v

# Run with coverage
pytest tests/unit/ --cov=api --cov-report=html

# Run parallel tests
pytest tests/unit/ -n auto

# Run with specific markers
pytest -m "unit and not slow"

# Run integration tests
pytest tests/integration/ --tb=short
```

## Test Categories

### Unit Tests

Unit tests verify individual components in isolation using mocks and stubs.

**Location**: `tests/unit/`

**Coverage**:
- API endpoints and request handling
- ASR service functionality
- LLM service integration
- TTS service operations
- Database abstraction layer
- Error handling and edge cases

**Running**:
```bash
python run_tests.py --unit
# or
pytest tests/unit/ -v
```

### Integration Tests

Integration tests verify component interactions and complete workflows.

**Location**: `tests/integration/`, `integration_tests/`

**Coverage**:
- Service-to-service communication
- Database consistency across operations
- End-to-end workflows (voice-to-voice, text conversations)
- Deployment profile testing (lightweight vs full)
- Error recovery and fallback mechanisms

**Running**:
```bash
python run_tests.py --integration --with-services
# or
pytest tests/integration/ -v
```

### Security Tests

Security tests check for vulnerabilities and security best practices.

**Location**: `tests/security/`

**Coverage**:
- Input validation and sanitization
- SQL injection protection
- XSS protection
- Command injection protection
- Path traversal protection
- Authentication and authorization
- File upload security
- Security headers
- Dependency vulnerabilities

**Running**:
```bash
python run_tests.py --security
# or
pytest tests/security/ -v
```

### Load Tests

Load tests verify system performance under various load conditions.

**Location**: `tests/load/`

**Coverage**:
- Concurrent user simulation
- Performance under load
- Resource usage monitoring
- Error rate under stress
- Database performance
- Service degradation handling

**Running**:
```bash
python run_tests.py --load --load-users 50 --load-duration 2m
# or
locust -f tests/load/test_load.py --headless --users 50 --spawn-rate 5 --run-time 2m --host http://localhost:8000
```

### Monitoring Tests

Monitoring tests verify observability and metrics collection.

**Location**: `tests/monitoring/`

**Coverage**:
- Prometheus metrics collection
- Health check endpoints
- Service discovery
- Logging functionality
- Performance monitoring
- Alerting integration

**Running**:
```bash
python run_tests.py --monitoring
# or
pytest tests/monitoring/ -v
```

## Development Workflow

### Pre-commit Testing

Before committing code, run:

```bash
# Quick smoke tests
pytest tests/unit/ -m "smoke" -x

# Full unit test suite
python run_tests.py --unit

# Code quality checks
python run_tests.py --code-quality
```

### Feature Development

When developing new features:

1. Write unit tests first (TDD approach)
2. Implement the feature
3. Run unit tests: `python run_tests.py --unit`
4. Write integration tests
5. Run integration tests: `python run_tests.py --integration --with-services`
6. Update security tests if needed
7. Run full test suite: `python run_tests.py --all`

### Bug Fixes

When fixing bugs:

1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify the test passes
4. Run related test suites
5. Run regression tests

## Test Configuration

### pytest Configuration

Configuration is in `pytest.ini` and `pyproject.toml`:

- Test discovery patterns
- Markers for test categorization
- Coverage settings
- Async test support
- Logging configuration
- Warning filters

### Environment Variables

Tests use these environment variables:

```bash
TESTING=true                    # Enable test mode
PYTHONPATH=.                   # Python path
LOG_LEVEL=INFO                 # Logging level
DEPLOYMENT_PROFILE=lightweight # Test deployment profile
DATABASE_URL=:memory:          # In-memory database for tests
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_api_endpoint():
    pass

@pytest.mark.integration
@pytest.mark.requires_services
def test_full_workflow():
    pass

@pytest.mark.slow
def test_large_dataset():
    pass
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        python run_tests.py --all --output test_report.json
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Docker Testing

```bash
# Build test image using main Dockerfile
docker build -t agent-cag-test .

# Run tests in container
docker run --rm agent-cag-test python run_tests.py --all
```

## Code Quality

### Coverage Requirements

- Minimum coverage: 80%
- Unit test coverage: 90%+
- Integration test coverage: 70%+

### Code Quality Tools

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **Bandit**: Security scanning
- **Safety**: Dependency vulnerability scanning

```bash
# Run all quality checks
python run_tests.py --code-quality

# Individual tools
black --check .
flake8 .
mypy api/ asr/ llm/ tts/
bandit -r api/ asr/ llm/ tts/
safety check
```

## Performance Testing

### Load Testing Scenarios

1. **Normal Load**: 10 concurrent users
2. **Peak Load**: 50 concurrent users
3. **Stress Test**: 100+ concurrent users
4. **Endurance Test**: Extended duration testing
5. **Spike Test**: Sudden traffic increases

### Performance Metrics

- Response time percentiles (50th, 95th, 99th)
- Throughput (requests per second)
- Error rate
- Resource utilization (CPU, memory)
- Database performance

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Solution: Install dependencies
pip install -e ".[dev]"

# Or set PYTHONPATH
export PYTHONPATH=.
```

#### Service Connection Errors
```bash
# Solution: Start services
python run_tests.py --with-services

# Or manually
docker-compose -f docker-compose.local.yml up -d
```

#### Test Timeouts
```bash
# Solution: Increase timeout
pytest --timeout=600

# Or skip slow tests
pytest -m "not slow"
```

#### Database Errors
```bash
# Solution: Use in-memory database
export DATABASE_URL=:memory:

# Or reset test database
rm -f test.db
```

### Debug Mode

Enable debug mode for detailed output:

```bash
# Verbose pytest output
pytest -vvv --tb=long

# Debug logging
LOG_LEVEL=DEBUG python run_tests.py --unit

# Keep test artifacts
pytest --keep-artifacts
```

### Test Data

Test data is generated dynamically:
- In-memory: Temporary test data created during test execution
- Dynamic fixtures: Test data generated using pytest fixtures
- Mock data: Simulated responses for external service testing

## Best Practices

### Writing Tests

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use descriptive names**: `test_api_returns_error_for_invalid_input`
3. **Test one thing**: Each test should verify one behavior
4. **Use fixtures**: Share setup code with pytest fixtures
5. **Mock external dependencies**: Keep tests isolated
6. **Test edge cases**: Empty inputs, large inputs, error conditions

### Test Organization

1. **Group related tests**: Use test classes
2. **Use markers**: Categorize tests appropriately
3. **Separate concerns**: Unit vs integration vs end-to-end
4. **Keep tests fast**: Mock expensive operations
5. **Make tests deterministic**: Avoid random data

### Maintenance

1. **Update tests with code changes**: Keep tests in sync
2. **Remove obsolete tests**: Clean up unused tests
3. **Refactor test code**: Apply DRY principles
4. **Monitor test performance**: Keep test suite fast
5. **Review test coverage**: Ensure adequate coverage

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Locust Documentation](https://docs.locust.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Bandit Security Linter](https://bandit.readthedocs.io/)

## Contributing

When contributing tests:

1. Follow the existing test structure
2. Add appropriate markers
3. Update documentation
4. Ensure tests pass in CI
5. Maintain or improve coverage