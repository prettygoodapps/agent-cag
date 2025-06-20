#!/usr/bin/env python3
"""
Comprehensive test runner for Agent CAG system.
Runs unit tests, integration tests, security tests, and load tests.
"""

import os
import sys
import subprocess
import argparse
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
import concurrent.futures


class TestRunner:
    """Main test runner for Agent CAG system."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def setup_environment(self):
        """Set up test environment."""
        print("🔧 Setting up test environment...")
        
        # Set environment variables for testing
        test_env = {
            "PYTHONPATH": str(self.project_root),
            "DEPLOYMENT_PROFILE": "lightweight",
            "DATABASE_URL": ":memory:",
            "TESTING": "true",
            "LOG_LEVEL": "INFO"
        }
        
        for key, value in test_env.items():
            os.environ[key] = value
        
        print("✅ Test environment configured")
    
    def install_dependencies(self):
        """Install test dependencies."""
        print("📦 Installing test dependencies...")
        
        test_requirements = [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-xdist>=3.0.0",
            "httpx>=0.24.0",
            "locust>=2.0.0",
            "bandit>=1.7.0",
            "safety>=2.0.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "psutil>=5.9.0"
        ]
        
        try:
            for requirement in test_requirements:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", requirement
                ], check=True, capture_output=True)
            print("✅ Test dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
        
        return True
    
    def run_unit_tests(self, coverage: bool = True, parallel: bool = True) -> Dict:
        """Run unit tests."""
        print("🧪 Running unit tests...")
        
        cmd = [sys.executable, "-m", "pytest", "tests/unit/"]
        
        if coverage:
            cmd.extend(["--cov=api", "--cov=asr", "--cov=llm", "--cov=tts"])
            cmd.extend(["--cov-report=html:htmlcov", "--cov-report=term"])
        
        if parallel:
            cmd.extend(["-n", "auto"])
        
        cmd.extend(["-v", "--tb=short"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": 0  # Would be calculated from actual run
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "returncode": -1,
                "stdout": "",
                "stderr": "Unit tests timed out after 5 minutes",
                "duration": 300
            }
        except Exception as e:
            return {
                "status": "error",
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0
            }
    
    def run_integration_tests(self) -> Dict:
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/integration/", "integration_tests/",
            "-v", "--tb=short"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": 0
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "returncode": -1,
                "stdout": "",
                "stderr": "Integration tests timed out after 10 minutes",
                "duration": 600
            }
        except Exception as e:
            return {
                "status": "error",
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0
            }
    
    def run_security_tests(self) -> Dict:
        """Run security tests."""
        print("🔒 Running security tests...")
        
        # Run pytest security tests
        pytest_cmd = [
            sys.executable, "-m", "pytest", 
            "tests/security/",
            "-v", "--tb=short"
        ]
        
        try:
            pytest_result = subprocess.run(pytest_cmd, capture_output=True, text=True, timeout=300)
            
            # Run bandit security scan
            bandit_cmd = [
                sys.executable, "-m", "bandit", 
                "-r", "api/", "asr/", "llm/", "tts/",
                "-f", "json"
            ]
            
            try:
                bandit_result = subprocess.run(bandit_cmd, capture_output=True, text=True, timeout=120)
                bandit_output = bandit_result.stdout
            except:
                bandit_output = "Bandit scan failed or not available"
            
            # Run safety check
            safety_cmd = [sys.executable, "-m", "safety", "check", "--json"]
            
            try:
                safety_result = subprocess.run(safety_cmd, capture_output=True, text=True, timeout=60)
                safety_output = safety_result.stdout
            except:
                safety_output = "Safety check failed or not available"
            
            return {
                "status": "passed" if pytest_result.returncode == 0 else "failed",
                "returncode": pytest_result.returncode,
                "stdout": pytest_result.stdout,
                "stderr": pytest_result.stderr,
                "bandit_output": bandit_output,
                "safety_output": safety_output,
                "duration": 0
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "returncode": -1,
                "stdout": "",
                "stderr": "Security tests timed out",
                "duration": 300
            }
        except Exception as e:
            return {
                "status": "error",
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0
            }
    
    def run_monitoring_tests(self) -> Dict:
        """Run monitoring tests."""
        print("📊 Running monitoring tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/monitoring/",
            "-v", "--tb=short"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": 0
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "returncode": -1,
                "stdout": "",
                "stderr": "Monitoring tests timed out",
                "duration": 300
            }
        except Exception as e:
            return {
                "status": "error",
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0
            }
    
    def run_load_tests(self, users: int = 10, duration: str = "30s") -> Dict:
        """Run load tests using locust."""
        print(f"⚡ Running load tests ({users} users for {duration})...")
        
        # Check if services are running
        if not self.check_services_running():
            return {
                "status": "skipped",
                "returncode": 0,
                "stdout": "",
                "stderr": "Services not running, skipping load tests",
                "duration": 0
            }
        
        cmd = [
            sys.executable, "-m", "locust",
            "-f", "tests/load/test_load.py",
            "--headless",
            "--users", str(users),
            "--spawn-rate", "2",
            "--run-time", duration,
            "--host", "http://localhost:8000"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": 0
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "returncode": -1,
                "stdout": "",
                "stderr": "Load tests timed out",
                "duration": 300
            }
        except Exception as e:
            return {
                "status": "error",
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0
            }
    
    def run_code_quality_checks(self) -> Dict:
        """Run code quality checks."""
        print("🎯 Running code quality checks...")
        
        results = {}
        
        # Black formatting check
        try:
            black_result = subprocess.run([
                sys.executable, "-m", "black", "--check", "--diff", "."
            ], capture_output=True, text=True, timeout=60)
            results["black"] = {
                "status": "passed" if black_result.returncode == 0 else "failed",
                "output": black_result.stdout + black_result.stderr
            }
        except:
            results["black"] = {"status": "error", "output": "Black check failed"}
        
        # Flake8 linting
        try:
            flake8_result = subprocess.run([
                sys.executable, "-m", "flake8", "api/", "asr/", "llm/", "tts/", "tests/"
            ], capture_output=True, text=True, timeout=60)
            results["flake8"] = {
                "status": "passed" if flake8_result.returncode == 0 else "failed",
                "output": flake8_result.stdout + flake8_result.stderr
            }
        except:
            results["flake8"] = {"status": "error", "output": "Flake8 check failed"}
        
        # MyPy type checking
        try:
            mypy_result = subprocess.run([
                sys.executable, "-m", "mypy", "api/", "asr/", "llm/", "tts/"
            ], capture_output=True, text=True, timeout=120)
            results["mypy"] = {
                "status": "passed" if mypy_result.returncode == 0 else "failed",
                "output": mypy_result.stdout + mypy_result.stderr
            }
        except:
            results["mypy"] = {"status": "error", "output": "MyPy check failed"}
        
        overall_status = "passed" if all(r["status"] == "passed" for r in results.values()) else "failed"
        
        return {
            "status": overall_status,
            "returncode": 0 if overall_status == "passed" else 1,
            "results": results,
            "duration": 0
        }
    
    def check_services_running(self) -> bool:
        """Check if services are running for load tests."""
        try:
            import httpx
            response = httpx.get("http://localhost:8000/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_services_for_testing(self) -> bool:
        """Start services for integration and load testing."""
        print("🚀 Starting services for testing...")
        
        try:
            # Start lightweight profile for testing
            subprocess.run([
                "docker-compose", "-f", "docker-compose.local.yml", "up", "-d"
            ], check=True, capture_output=True)
            
            # Wait for services to be ready
            time.sleep(10)
            
            if self.check_services_running():
                print("✅ Services started successfully")
                return True
            else:
                print("❌ Services failed to start properly")
                return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start services: {e}")
            return False
    
    def stop_services(self):
        """Stop test services."""
        print("🛑 Stopping test services...")
        
        try:
            subprocess.run([
                "docker-compose", "-f", "docker-compose.local.yml", "down"
            ], check=True, capture_output=True)
            print("✅ Services stopped")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Failed to stop services: {e}")
    
    def generate_report(self, output_file: Optional[str] = None):
        """Generate test report."""
        print("📋 Generating test report...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r["status"] == "passed")
        failed_tests = sum(1 for r in self.test_results.values() if r["status"] == "failed")
        skipped_tests = sum(1 for r in self.test_results.values() if r["status"] == "skipped")
        
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        report = {
            "summary": {
                "total_test_suites": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "duration_seconds": duration,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "results": self.test_results
        }
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 TEST SUMMARY")
        print("="*60)
        print(f"Total Test Suites: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏭️  Skipped: {skipped_tests}")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print("="*60)
        
        # Print detailed results
        for test_name, result in self.test_results.items():
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️",
                "timeout": "⏰",
                "error": "💥"
            }.get(result["status"], "❓")
            
            print(f"{status_emoji} {test_name.upper()}: {result['status'].upper()}")
            
            if result["status"] in ["failed", "error", "timeout"] and result.get("stderr"):
                print(f"   Error: {result['stderr'][:200]}...")
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {output_file}")
        
        return report
    
    def run_all_tests(self, 
                     include_load: bool = False,
                     include_services: bool = False,
                     coverage: bool = True,
                     parallel: bool = True,
                     load_users: int = 10,
                     load_duration: str = "30s") -> Dict:
        """Run all test suites."""
        print("🚀 Starting comprehensive test run...")
        self.start_time = time.time()
        
        # Setup
        self.setup_environment()
        
        if not self.install_dependencies():
            print("❌ Failed to install dependencies, aborting")
            return {"status": "error", "message": "Dependency installation failed"}
        
        # Start services if needed
        services_started = False
        if include_services or include_load:
            services_started = self.start_services_for_testing()
        
        try:
            # Run test suites
            test_suites = [
                ("unit", lambda: self.run_unit_tests(coverage=coverage, parallel=parallel)),
                ("integration", self.run_integration_tests),
                ("security", self.run_security_tests),
                ("monitoring", self.run_monitoring_tests),
                ("code_quality", self.run_code_quality_checks),
            ]
            
            if include_load and services_started:
                test_suites.append(
                    ("load", lambda: self.run_load_tests(users=load_users, duration=load_duration))
                )
            
            # Run tests sequentially or in parallel
            for test_name, test_func in test_suites:
                print(f"\n{'='*20} {test_name.upper()} TESTS {'='*20}")
                self.test_results[test_name] = test_func()
                
                if self.test_results[test_name]["status"] == "failed":
                    print(f"❌ {test_name} tests failed")
                elif self.test_results[test_name]["status"] == "passed":
                    print(f"✅ {test_name} tests passed")
                else:
                    print(f"⚠️  {test_name} tests: {self.test_results[test_name]['status']}")
        
        finally:
            # Cleanup
            if services_started:
                self.stop_services()
        
        self.end_time = time.time()
        
        # Generate report
        report = self.generate_report("test_report.json")
        
        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agent CAG Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--security", action="store_true", help="Run security tests only")
    parser.add_argument("--monitoring", action="store_true", help="Run monitoring tests only")
    parser.add_argument("--load", action="store_true", help="Run load tests only")
    parser.add_argument("--code-quality", action="store_true", help="Run code quality checks only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--with-load", action="store_true", help="Include load tests in full run")
    parser.add_argument("--with-services", action="store_true", help="Start services for testing")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel test execution")
    parser.add_argument("--load-users", type=int, default=10, help="Number of users for load testing")
    parser.add_argument("--load-duration", default="30s", help="Duration for load testing")
    parser.add_argument("--output", help="Output file for test report")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Determine what to run
    if args.all or not any([args.unit, args.integration, args.security, args.monitoring, args.load, args.code_quality]):
        # Run all tests
        report = runner.run_all_tests(
            include_load=args.with_load,
            include_services=args.with_services,
            coverage=not args.no_coverage,
            parallel=not args.no_parallel,
            load_users=args.load_users,
            load_duration=args.load_duration
        )
    else:
        # Run specific test suites
        runner.setup_environment()
        runner.install_dependencies()
        
        if args.with_services:
            runner.start_services_for_testing()
        
        try:
            runner.start_time = time.time()
            
            if args.unit:
                runner.test_results["unit"] = runner.run_unit_tests(
                    coverage=not args.no_coverage,
                    parallel=not args.no_parallel
                )
            
            if args.integration:
                runner.test_results["integration"] = runner.run_integration_tests()
            
            if args.security:
                runner.test_results["security"] = runner.run_security_tests()
            
            if args.monitoring:
                runner.test_results["monitoring"] = runner.run_monitoring_tests()
            
            if args.load:
                runner.test_results["load"] = runner.run_load_tests(
                    users=args.load_users,
                    duration=args.load_duration
                )
            
            if args.code_quality:
                runner.test_results["code_quality"] = runner.run_code_quality_checks()
            
            runner.end_time = time.time()
            report = runner.generate_report(args.output)
        
        finally:
            if args.with_services:
                runner.stop_services()
    
    # Exit with appropriate code
    failed_tests = sum(1 for r in runner.test_results.values() if r["status"] == "failed")
    sys.exit(1 if failed_tests > 0 else 0)


if __name__ == "__main__":
    main()