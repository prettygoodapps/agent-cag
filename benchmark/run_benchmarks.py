"""
Performance benchmarking script for Agent CAG system.

This script runs performance tests and generates comparison reports
between lightweight and full deployment profiles.
"""

import asyncio
import time
import json
import statistics
from typing import List, Dict, Any
from datetime import datetime
import httpx
import argparse


class BenchmarkRunner:
    """Runs performance benchmarks against the Agent CAG system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "tests": {}
        }
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmark tests."""
        print("Starting Agent CAG Performance Benchmarks...")
        
        # Test individual endpoints
        await self.benchmark_health_checks()
        await self.benchmark_query_processing()
        await self.benchmark_speech_synthesis()
        await self.benchmark_search_functionality()
        await self.benchmark_concurrent_load()
        
        # Generate summary
        self.generate_summary()
        
        return self.results
    
    async def benchmark_health_checks(self):
        """Benchmark health check endpoints."""
        print("Benchmarking health checks...")
        
        endpoints = [
            ("API", f"{self.base_url}/health"),
            ("ASR", "http://localhost:8001/health"),
            ("LLM", "http://localhost:8002/health"),
            ("TTS", "http://localhost:8003/health"),
            ("Sardaukar", "http://localhost:8004/api/health"),
        ]
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            for service_name, url in endpoints:
                times = []
                success_count = 0
                
                for _ in range(10):
                    start_time = time.time()
                    try:
                        response = await client.get(url, timeout=5.0)
                        end_time = time.time()
                        
                        if response.status_code == 200:
                            success_count += 1
                            times.append(end_time - start_time)
                    except Exception:
                        pass
                
                if times:
                    results[service_name] = {
                        "avg_response_time": statistics.mean(times),
                        "min_response_time": min(times),
                        "max_response_time": max(times),
                        "success_rate": success_count / 10,
                        "total_requests": 10
                    }
        
        self.results["tests"]["health_checks"] = results
    
    async def benchmark_query_processing(self):
        """Benchmark query processing performance."""
        print("Benchmarking query processing...")
        
        test_queries = [
            "What is artificial intelligence?",
            "Explain machine learning in simple terms.",
            "How do neural networks work?",
            "What are the benefits of deep learning?",
            "Describe natural language processing."
        ]
        
        times = []
        success_count = 0
        
        async with httpx.AsyncClient() as client:
            for i, query in enumerate(test_queries):
                start_time = time.time()
                try:
                    response = await client.post(
                        f"{self.base_url}/query",
                        json={
                            "text": query,
                            "user_id": f"benchmark-user-{i}",
                            "generate_speech": False
                        },
                        timeout=30.0
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        success_count += 1
                        times.append(end_time - start_time)
                        
                        # Extract additional metrics
                        data = response.json()
                        print(f"Query {i+1}: {end_time - start_time:.2f}s")
                        
                except Exception as e:
                    print(f"Query {i+1} failed: {e}")
        
        if times:
            self.results["tests"]["query_processing"] = {
                "avg_response_time": statistics.mean(times),
                "min_response_time": min(times),
                "max_response_time": max(times),
                "p95_response_time": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                "success_rate": success_count / len(test_queries),
                "total_requests": len(test_queries)
            }
    
    async def benchmark_speech_synthesis(self):
        """Benchmark speech synthesis performance."""
        print("Benchmarking speech synthesis...")
        
        test_texts = [
            "Hello, this is a test.",
            "The quick brown fox jumps over the lazy dog.",
            "Artificial intelligence is transforming our world.",
        ]
        
        times = []
        success_count = 0
        
        async with httpx.AsyncClient() as client:
            for i, text in enumerate(test_texts):
                start_time = time.time()
                try:
                    response = await client.post(
                        "http://localhost:8003/synthesize",
                        json={
                            "text": text,
                            "use_sardaukar": False
                        },
                        timeout=20.0
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        success_count += 1
                        times.append(end_time - start_time)
                        print(f"TTS {i+1}: {end_time - start_time:.2f}s")
                        
                except Exception as e:
                    print(f"TTS {i+1} failed: {e}")
        
        if times:
            self.results["tests"]["speech_synthesis"] = {
                "avg_response_time": statistics.mean(times),
                "min_response_time": min(times),
                "max_response_time": max(times),
                "success_rate": success_count / len(test_texts),
                "total_requests": len(test_texts)
            }
    
    async def benchmark_search_functionality(self):
        """Benchmark search performance."""
        print("Benchmarking search functionality...")
        
        search_queries = [
            "machine learning",
            "artificial intelligence",
            "neural networks",
            "deep learning",
            "natural language"
        ]
        
        times = []
        success_count = 0
        
        async with httpx.AsyncClient() as client:
            for i, query in enumerate(search_queries):
                start_time = time.time()
                try:
                    response = await client.get(
                        f"{self.base_url}/search",
                        params={"query": query, "limit": 5},
                        timeout=10.0
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        success_count += 1
                        times.append(end_time - start_time)
                        print(f"Search {i+1}: {end_time - start_time:.2f}s")
                        
                except Exception as e:
                    print(f"Search {i+1} failed: {e}")
        
        if times:
            self.results["tests"]["search"] = {
                "avg_response_time": statistics.mean(times),
                "min_response_time": min(times),
                "max_response_time": max(times),
                "success_rate": success_count / len(search_queries),
                "total_requests": len(search_queries)
            }
    
    async def benchmark_concurrent_load(self):
        """Benchmark concurrent load handling."""
        print("Benchmarking concurrent load...")
        
        concurrent_users = [1, 5, 10]
        
        for user_count in concurrent_users:
            print(f"Testing with {user_count} concurrent users...")
            
            async def make_request(user_id: int):
                async with httpx.AsyncClient() as client:
                    start_time = time.time()
                    try:
                        response = await client.post(
                            f"{self.base_url}/query",
                            json={
                                "text": f"Test query from user {user_id}",
                                "user_id": f"load-test-user-{user_id}",
                                "generate_speech": False
                            },
                            timeout=30.0
                        )
                        end_time = time.time()
                        
                        return {
                            "success": response.status_code == 200,
                            "response_time": end_time - start_time,
                            "user_id": user_id
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "response_time": None,
                            "user_id": user_id,
                            "error": str(e)
                        }
            
            # Execute concurrent requests
            start_time = time.time()
            tasks = [make_request(i) for i in range(user_count)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in results if r["success"]]
            response_times = [r["response_time"] for r in successful_results if r["response_time"]]
            
            self.results["tests"][f"concurrent_load_{user_count}"] = {
                "concurrent_users": user_count,
                "total_time": end_time - start_time,
                "success_rate": len(successful_results) / user_count,
                "avg_response_time": statistics.mean(response_times) if response_times else None,
                "max_response_time": max(response_times) if response_times else None,
                "throughput": len(successful_results) / (end_time - start_time)
            }
    
    def generate_summary(self):
        """Generate benchmark summary."""
        summary = {
            "total_tests": len(self.results["tests"]),
            "overall_health": "healthy" if all(
                test.get("success_rate", 0) > 0.8 
                for test in self.results["tests"].values() 
                if isinstance(test, dict) and "success_rate" in test
            ) else "degraded"
        }
        
        # Calculate average response times across all tests
        all_response_times = []
        for test_name, test_data in self.results["tests"].items():
            if isinstance(test_data, dict) and "avg_response_time" in test_data:
                all_response_times.append(test_data["avg_response_time"])
        
        if all_response_times:
            summary["avg_response_time_across_all_tests"] = statistics.mean(all_response_times)
        
        self.results["summary"] = summary
    
    def save_results(self, filename: str = None):
        """Save benchmark results to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark/results/benchmark_results_{timestamp}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Results saved to {filename}")
        return filename


async def main():
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(description="Run Agent CAG benchmarks")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    runner = BenchmarkRunner(args.url)
    
    try:
        results = await runner.run_all_benchmarks()
        
        # Save results
        output_file = runner.save_results(args.output)
        
        # Print summary
        print("\n" + "="*50)
        print("BENCHMARK SUMMARY")
        print("="*50)
        print(f"Total tests: {results['summary']['total_tests']}")
        print(f"Overall health: {results['summary']['overall_health']}")
        
        if "avg_response_time_across_all_tests" in results["summary"]:
            avg_time = results["summary"]["avg_response_time_across_all_tests"]
            print(f"Average response time: {avg_time:.3f}s")
        
        print(f"Results saved to: {output_file}")
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"Benchmark failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())