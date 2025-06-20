#!/usr/bin/env python3
"""
Test script for the Agent CAG system
Demonstrates the complete pipeline functionality
"""

import requests
import time
import json
import sys


def wait_for_service(url, service_name, max_retries=30):
    """Wait for a service to become healthy"""
    print(f"Waiting for {service_name} to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {service_name} is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"  Attempt {i+1}/{max_retries} - {service_name} not ready yet...")
        time.sleep(10)

    print(f"✗ {service_name} failed to start after {max_retries * 10} seconds")
    return False


def test_api_query(
    text, user_id="test-user", generate_speech=False, use_sardaukar=False
):
    """Test the main API query endpoint"""
    url = "http://localhost:8000/query"
    payload = {
        "text": text,
        "user_id": user_id,
        "generate_speech": generate_speech,
        "use_sardaukar": use_sardaukar,
    }

    print(f"\n🔄 Testing query: '{text}'")
    if generate_speech:
        print(f"   Speech generation: {'Sardaukar' if use_sardaukar else 'English'}")

    try:
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()

        print(f"✓ Response received:")
        print(f"  Query ID: {result.get('query_id')}")
        print(f"  Response ID: {result.get('response_id')}")
        print(f"  Text: {result.get('text')[:100]}...")

        if result.get("audio_url"):
            print(f"  Audio URL: {result.get('audio_url')}")

        if result.get("metadata", {}).get("error"):
            print(f"  ⚠️  Service error: {result['metadata']['error']}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        return None


def test_health_endpoints():
    """Test all service health endpoints"""
    services = [
        ("API Gateway", "http://localhost:8000/health"),
        ("ASR Service", "http://localhost:8001/health"),
        ("LLM Service", "http://localhost:8002/health"),
        ("TTS Service", "http://localhost:8003/health"),
        ("Sardaukar Translator", "http://localhost:8004/api/health"),
    ]

    print("\n🏥 Health Check Results:")
    print("=" * 50)

    for service_name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {service_name}: Healthy")
            else:
                print(f"⚠️  {service_name}: Unhealthy (HTTP {response.status_code})")
        except requests.exceptions.RequestException:
            print(f"✗ {service_name}: Not responding")


def test_user_history(user_id="test-user"):
    """Test user history retrieval"""
    url = f"http://localhost:8000/history/{user_id}"

    print(f"\n📚 Testing user history for: {user_id}")

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            history = response.json()
            print(f"✓ Retrieved {len(history)} history entries")
            for i, entry in enumerate(history[:3]):  # Show first 3
                print(f"  {i+1}. {entry.get('query_text', 'N/A')[:50]}...")
        else:
            print(f"✗ Failed to retrieve history: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")


def main():
    """Main test function"""
    print("🚀 Agent CAG System Test")
    print("=" * 50)

    # Test health endpoints first
    test_health_endpoints()

    # Wait for critical services
    critical_services = [
        ("http://localhost:8000/health", "API Gateway"),
        ("http://localhost:8002/health", "LLM Service"),
    ]

    print("\n⏳ Waiting for critical services...")
    for url, name in critical_services:
        if not wait_for_service(url, name):
            print(f"✗ Critical service {name} failed to start. Exiting.")
            sys.exit(1)

    # Test basic queries
    print("\n🧪 Running System Tests")
    print("=" * 50)

    # Test 1: Basic text query
    test_api_query("What is artificial intelligence?")

    # Test 2: Query with speech generation
    test_api_query("Hello, how are you today?", generate_speech=True)

    # Test 3: Query with Sardaukar translation (if available)
    test_api_query(
        "Greetings from the desert planet!", generate_speech=True, use_sardaukar=True
    )

    # Test user history
    test_user_history()

    print("\n✅ System test completed!")
    print("\nNext steps:")
    print("- Check service logs: make logs")
    print("- Monitor with Grafana: make up-monitoring")
    print("- Run benchmarks: make benchmark")
    print("- API documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
