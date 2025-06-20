#!/usr/bin/env python3
"""
Agent CAG System Requirements Checker

This script analyzes the host system to determine if it can run the Agent CAG framework
and provides recommendations for optimal deployment configuration.
"""

import os
import sys
import json
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import psutil


class SystemChecker:
    """System requirements checker for Agent CAG framework."""

    def __init__(self):
        self.results = {
            "system_info": {},
            "requirements": {},
            "recommendations": [],
            "warnings": [],
            "errors": [],
            "deployment_profiles": {},
        }

        # Define minimum requirements for different profiles
        self.profiles = {
            "lightweight": {
                "name": "Lightweight Profile",
                "description": "DuckDB + Containerized Ollama",
                "min_ram_gb": 8,
                "recommended_ram_gb": 16,
                "min_disk_gb": 20,
                "recommended_disk_gb": 50,
                "min_cpu_cores": 4,
                "gpu_required": False,
                "gpu_recommended": True,
                "services": [
                    "api",
                    "asr",
                    "llm",
                    "tts",
                    "sardaukar-translator",
                    "ollama",
                ],
            },
            "full": {
                "name": "Full Profile",
                "description": "ChromaDB + Neo4j + Containerized Ollama",
                "min_ram_gb": 16,
                "recommended_ram_gb": 32,
                "min_disk_gb": 40,
                "recommended_disk_gb": 100,
                "min_cpu_cores": 6,
                "gpu_required": False,
                "gpu_recommended": True,
                "services": [
                    "api",
                    "asr",
                    "llm",
                    "tts",
                    "sardaukar-translator",
                    "ollama",
                    "chromadb",
                    "neo4j",
                ],
            },
            "monitoring": {
                "name": "Monitoring Profile",
                "description": "Adds Prometheus + Grafana",
                "additional_ram_gb": 2,
                "additional_disk_gb": 10,
                "additional_services": ["prometheus", "grafana"],
            },
            "local_ollama": {
                "name": "Local Ollama Mode",
                "description": "Uses host-installed Ollama",
                "ram_savings_gb": 4,
                "disk_savings_gb": 10,
                "requires_host_ollama": True,
            },
        }

    def check_system_info(self):
        """Gather basic system information."""
        try:
            self.results["system_info"] = {
                "platform": platform.platform(),
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(logical=False),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(
                    psutil.virtual_memory().available / (1024**3), 2
                ),
                "disk_total_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage("/").free / (1024**3), 2),
            }
        except Exception as e:
            self.results["errors"].append(f"Failed to gather system info: {e}")

    def check_docker(self):
        """Check Docker installation and configuration."""
        docker_info = {
            "installed": False,
            "version": None,
            "compose_installed": False,
            "compose_version": None,
            "daemon_running": False,
            "user_in_group": False,
            "gpu_support": False,
        }

        try:
            # Check Docker installation
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                docker_info["installed"] = True
                docker_info["version"] = result.stdout.strip()

            # Check Docker daemon
            result = subprocess.run(
                ["docker", "info"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                docker_info["daemon_running"] = True

            # Check Docker Compose
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                docker_info["compose_installed"] = True
                docker_info["compose_version"] = result.stdout.strip()

            # Check user in docker group
            try:
                import grp

                docker_group = grp.getgrnam("docker")
                current_user = os.getenv("USER")
                if current_user in docker_group.gr_mem:
                    docker_info["user_in_group"] = True
            except KeyError:
                pass

            # Check GPU support (NVIDIA Container Toolkit)
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "nvidia/cuda:11.0-base",
                    "nvidia-smi",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                docker_info["gpu_support"] = True

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.results["warnings"].append(f"Docker check failed: {e}")

        self.results["requirements"]["docker"] = docker_info

    def check_ollama(self):
        """Check if Ollama is installed locally."""
        ollama_info = {
            "installed": False,
            "version": None,
            "running": False,
            "models": [],
        }

        try:
            # Check Ollama installation
            result = subprocess.run(
                ["ollama", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                ollama_info["installed"] = True
                ollama_info["version"] = result.stdout.strip()

            # Check if Ollama is running
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                ollama_info["running"] = True
                try:
                    models_data = json.loads(result.stdout)
                    ollama_info["models"] = [
                        model["name"] for model in models_data.get("models", [])
                    ]
                except json.JSONDecodeError:
                    pass

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            pass  # Ollama not required for containerized mode

        self.results["requirements"]["ollama"] = ollama_info

    def check_gpu(self):
        """Check GPU availability and capabilities."""
        gpu_info = {
            "nvidia_gpu": False,
            "nvidia_driver": None,
            "cuda_version": None,
            "gpu_memory_gb": 0,
            "gpu_count": 0,
        }

        try:
            # Check NVIDIA GPU
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                gpu_info["nvidia_gpu"] = True
                lines = result.stdout.strip().split("\n")
                gpu_info["gpu_count"] = len(lines)

                total_memory = 0
                for line in lines:
                    if "," in line:
                        _, memory = line.split(",")
                        total_memory += int(memory.strip())
                gpu_info["gpu_memory_gb"] = round(total_memory / 1024, 2)

            # Check NVIDIA driver version
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                gpu_info["nvidia_driver"] = result.stdout.strip()

            # Check CUDA version
            result = subprocess.run(
                ["nvcc", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "release" in line.lower():
                        gpu_info["cuda_version"] = line.strip()
                        break

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass  # GPU not required but recommended

        self.results["requirements"]["gpu"] = gpu_info

    def analyze_profiles(self):
        """Analyze which deployment profiles are suitable for this system."""
        system_ram = self.results["system_info"]["memory_total_gb"]
        system_disk = self.results["system_info"]["disk_free_gb"]
        system_cpu = self.results["system_info"]["cpu_count"]

        for profile_name, profile in self.profiles.items():
            if profile_name == "monitoring":
                continue  # Skip monitoring as it's an add-on

            analysis = {
                "suitable": True,
                "performance": "good",
                "issues": [],
                "estimated_resources": {},
            }

            # Calculate resource requirements
            if profile_name == "local_ollama":
                # Local Ollama mode modifies lightweight requirements
                base_profile = self.profiles["lightweight"].copy()
                base_profile["min_ram_gb"] -= profile["ram_savings_gb"]
                base_profile["recommended_ram_gb"] -= profile["ram_savings_gb"]
                base_profile["min_disk_gb"] -= profile["disk_savings_gb"]
                base_profile["recommended_disk_gb"] -= profile["disk_savings_gb"]
                profile_reqs = base_profile

                # Check if Ollama is available locally
                if not self.results["requirements"]["ollama"]["installed"]:
                    analysis["issues"].append("Ollama not installed locally")
                    analysis["suitable"] = False
            else:
                profile_reqs = profile

            # Check RAM requirements
            if system_ram < profile_reqs["min_ram_gb"]:
                analysis["suitable"] = False
                analysis["issues"].append(
                    f"Insufficient RAM: {system_ram}GB < {profile_reqs['min_ram_gb']}GB required"
                )
            elif system_ram < profile_reqs["recommended_ram_gb"]:
                analysis["performance"] = "limited"
                analysis["issues"].append(
                    f"RAM below recommended: {system_ram}GB < {profile_reqs['recommended_ram_gb']}GB"
                )

            # Check disk space
            if system_disk < profile_reqs["min_disk_gb"]:
                analysis["suitable"] = False
                analysis["issues"].append(
                    f"Insufficient disk space: {system_disk}GB < {profile_reqs['min_disk_gb']}GB required"
                )
            elif system_disk < profile_reqs["recommended_disk_gb"]:
                analysis["performance"] = "limited"
                analysis["issues"].append(
                    f"Disk space below recommended: {system_disk}GB < {profile_reqs['recommended_disk_gb']}GB"
                )

            # Check CPU cores
            if system_cpu < profile_reqs["min_cpu_cores"]:
                analysis["suitable"] = False
                analysis["issues"].append(
                    f"Insufficient CPU cores: {system_cpu} < {profile_reqs['min_cpu_cores']} required"
                )

            # Check GPU requirements
            has_gpu = self.results["requirements"]["gpu"]["nvidia_gpu"]
            if profile_reqs.get("gpu_required") and not has_gpu:
                analysis["suitable"] = False
                analysis["issues"].append("GPU required but not available")
            elif profile_reqs.get("gpu_recommended") and not has_gpu:
                analysis["performance"] = "limited"
                analysis["issues"].append("GPU recommended for optimal performance")

            # Estimate resource usage
            analysis["estimated_resources"] = {
                "ram_usage_gb": profile_reqs["min_ram_gb"],
                "disk_usage_gb": profile_reqs["min_disk_gb"],
                "cpu_cores_used": min(profile_reqs["min_cpu_cores"], system_cpu),
            }

            self.results["deployment_profiles"][profile_name] = analysis

    def generate_recommendations(self):
        """Generate deployment recommendations based on system analysis."""
        recommendations = []
        warnings = []

        # Docker recommendations
        docker = self.results["requirements"]["docker"]
        if not docker["installed"]:
            recommendations.append(
                "Install Docker: https://docs.docker.com/get-docker/"
            )
        elif not docker["daemon_running"]:
            recommendations.append("Start Docker daemon: sudo systemctl start docker")

        if not docker["compose_installed"]:
            recommendations.append(
                "Install Docker Compose: https://docs.docker.com/compose/install/"
            )

        if not docker["user_in_group"]:
            recommendations.append(
                "Add user to docker group: sudo usermod -aG docker $USER"
            )
            recommendations.append(
                "Log out and back in for group changes to take effect"
            )

        # GPU recommendations
        gpu = self.results["requirements"]["gpu"]
        if not gpu["nvidia_gpu"]:
            warnings.append(
                "No NVIDIA GPU detected. LLM inference will be slower on CPU."
            )
            recommendations.append(
                "Consider using local Ollama mode for better CPU performance"
            )
        elif not docker["gpu_support"]:
            recommendations.append(
                "Install NVIDIA Container Toolkit for GPU support in Docker"
            )
            recommendations.append(
                "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
            )

        # Profile recommendations
        suitable_profiles = [
            name
            for name, analysis in self.results["deployment_profiles"].items()
            if analysis["suitable"]
        ]

        if not suitable_profiles:
            recommendations.append(
                "System does not meet minimum requirements for any profile"
            )
            recommendations.append(
                "Consider upgrading hardware or using a cloud deployment"
            )
        else:
            best_profile = self.get_best_profile(suitable_profiles)
            recommendations.append(
                f"Recommended deployment: make up-{best_profile.replace('_', '-')}"
            )

        # Resource optimization
        system_ram = self.results["system_info"]["memory_total_gb"]
        if system_ram < 16:
            recommendations.append(
                "Consider closing other applications to free up memory"
            )
            recommendations.append("Use lightweight profile to minimize resource usage")

        self.results["recommendations"] = recommendations
        self.results["warnings"].extend(warnings)

    def get_best_profile(self, suitable_profiles: List[str]) -> str:
        """Determine the best profile for the system."""
        # Priority order: full > lightweight > local_ollama
        if "full" in suitable_profiles:
            full_analysis = self.results["deployment_profiles"]["full"]
            if full_analysis["performance"] == "good":
                return "full"

        if "lightweight" in suitable_profiles:
            lightweight_analysis = self.results["deployment_profiles"]["lightweight"]
            if lightweight_analysis["performance"] == "good":
                return "lightweight"

        if "local_ollama" in suitable_profiles:
            return "local"

        # Return the first suitable profile as fallback
        return suitable_profiles[0] if suitable_profiles else "lightweight"

    def run_all_checks(self):
        """Run all system checks."""
        print("🔍 Analyzing system requirements for Agent CAG...")

        self.check_system_info()
        print("✓ System information gathered")

        self.check_docker()
        print("✓ Docker configuration checked")

        self.check_ollama()
        print("✓ Ollama availability checked")

        self.check_gpu()
        print("✓ GPU capabilities analyzed")

        self.analyze_profiles()
        print("✓ Deployment profiles analyzed")

        self.generate_recommendations()
        print("✓ Recommendations generated")

    def print_report(self):
        """Print a comprehensive system report."""
        print("\n" + "=" * 80)
        print("🚀 AGENT CAG SYSTEM REQUIREMENTS REPORT")
        print("=" * 80)

        # System Information
        print("\n📊 SYSTEM INFORMATION")
        print("-" * 40)
        info = self.results["system_info"]
        print(f"Platform: {info.get('platform', 'Unknown')}")
        print(
            f"CPU: {info.get('processor', 'Unknown')} ({info.get('cpu_count', 0)} cores)"
        )
        print(
            f"Memory: {info.get('memory_total_gb', 0):.1f}GB total, {info.get('memory_available_gb', 0):.1f}GB available"
        )
        print(
            f"Disk: {info.get('disk_free_gb', 0):.1f}GB free of {info.get('disk_total_gb', 0):.1f}GB total"
        )

        # Docker Status
        print("\n🐳 DOCKER STATUS")
        print("-" * 40)
        docker = self.results["requirements"]["docker"]
        print(f"Docker Installed: {'✓' if docker['installed'] else '✗'}")
        if docker["version"]:
            print(f"Docker Version: {docker['version']}")
        print(f"Docker Daemon Running: {'✓' if docker['daemon_running'] else '✗'}")
        print(f"Docker Compose: {'✓' if docker['compose_installed'] else '✗'}")
        print(f"User in Docker Group: {'✓' if docker['user_in_group'] else '✗'}")
        print(f"GPU Support: {'✓' if docker['gpu_support'] else '✗'}")

        # GPU Status
        print("\n🎮 GPU STATUS")
        print("-" * 40)
        gpu = self.results["requirements"]["gpu"]
        if gpu["nvidia_gpu"]:
            print(
                f"NVIDIA GPU: ✓ ({gpu['gpu_count']} GPU(s), {gpu['gpu_memory_gb']:.1f}GB total)"
            )
            if gpu["nvidia_driver"]:
                print(f"Driver Version: {gpu['nvidia_driver']}")
        else:
            print("NVIDIA GPU: ✗ (CPU-only mode)")

        # Ollama Status
        print("\n🦙 OLLAMA STATUS")
        print("-" * 40)
        ollama = self.results["requirements"]["ollama"]
        print(f"Ollama Installed: {'✓' if ollama['installed'] else '✗'}")
        if ollama["version"]:
            print(f"Ollama Version: {ollama['version']}")
        print(f"Ollama Running: {'✓' if ollama['running'] else '✗'}")
        if ollama["models"]:
            print(f"Available Models: {', '.join(ollama['models'])}")

        # Deployment Profiles
        print("\n🎯 DEPLOYMENT PROFILE ANALYSIS")
        print("-" * 40)
        for profile_name, analysis in self.results["deployment_profiles"].items():
            profile = self.profiles[profile_name]
            status = "✓" if analysis["suitable"] else "✗"
            performance = analysis["performance"].upper()

            print(f"\n{status} {profile['name']} ({performance})")
            print(f"   {profile['description']}")

            if analysis["estimated_resources"]:
                resources = analysis["estimated_resources"]
                print(
                    f"   Estimated Usage: {resources['ram_usage_gb']}GB RAM, {resources['disk_usage_gb']}GB disk"
                )

            if analysis["issues"]:
                for issue in analysis["issues"]:
                    print(f"   ⚠️  {issue}")

        # Recommendations
        if self.results["recommendations"]:
            print("\n💡 RECOMMENDATIONS")
            print("-" * 40)
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"{i}. {rec}")

        # Warnings
        if self.results["warnings"]:
            print("\n⚠️  WARNINGS")
            print("-" * 40)
            for warning in self.results["warnings"]:
                print(f"• {warning}")

        # Errors
        if self.results["errors"]:
            print("\n❌ ERRORS")
            print("-" * 40)
            for error in self.results["errors"]:
                print(f"• {error}")

        print("\n" + "=" * 80)

    def save_report(self, filename: str = "system_check_report.json"):
        """Save the detailed report to a JSON file."""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 Detailed report saved to {filename}")


def main():
    """Main function to run system checks."""
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("Agent CAG System Requirements Checker")
        print("Usage: python check_system.py [--save-report]")
        print("       python check_system.py --help")
        return

    checker = SystemChecker()

    try:
        checker.run_all_checks()
        checker.print_report()

        if "--save-report" in sys.argv:
            checker.save_report()

        # Exit with appropriate code
        suitable_profiles = [
            name
            for name, analysis in checker.results["deployment_profiles"].items()
            if analysis["suitable"]
        ]

        if not suitable_profiles:
            print("\n❌ System does not meet minimum requirements")
            sys.exit(1)
        elif checker.results["errors"]:
            print("\n⚠️  System check completed with errors")
            sys.exit(2)
        else:
            print("\n✅ System check completed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⏹️  System check interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ System check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
