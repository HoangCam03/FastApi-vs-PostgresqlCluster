#!/usr/bin/env python3
"""
Test script for pg_auto_failover scenarios
"""
import requests
import time
import subprocess
import json
from datetime import datetime

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def test_api_endpoint(endpoint, method="GET", data=None):
    """Test API endpoint"""
    try:
        if method == "GET":
            response = requests.get(f"https://localhost:8443{endpoint}", verify=False, timeout=5)
        elif method == "POST":
            response = requests.post(f"https://localhost:8443{endpoint}", 
                                   json=data, verify=False, timeout=5)
        
        log(f"✅ {method} {endpoint}: {response.status_code}")
        return True, response.status_code
    except Exception as e:
        log(f"❌ {method} {endpoint}: {e}")
        return False, str(e)

def docker_stop(container_name):
    """Stop Docker container"""
    try:
        subprocess.run(f"docker stop {container_name}", shell=True, check=True)
        log(f"🛑 Stopped container: {container_name}")
        return True
    except Exception as e:
        log(f"❌ Failed to stop {container_name}: {e}")
        return False

def docker_start(container_name):
    """Start Docker container"""
    try:
        subprocess.run(f"docker start {container_name}", shell=True, check=True)
        log(f"🚀 Started container: {container_name}")
        return True
    except Exception as e:
        log(f"❌ Failed to start {container_name}: {e}")
        return False

def check_cluster_status():
    """Check pg_auto_failover cluster status"""
    try:
        result = subprocess.run("docker exec postgres-primary pg_autoctl show state", 
                              shell=True, capture_output=True, text=True)
        log(f"📊 Cluster status:\n{result.stdout}")
        return result.stdout
    except Exception as e:
        log(f"❌ Failed to check cluster status: {e}")
        return None

def main():
    log("=== pg_auto_failover Test Suite ===")
    
    # Test 1: Normal operation
    log("\n--- Test 1: Normal Operation ---")
    test_api_endpoint("/health")
    test_api_endpoint("/api/users/all")
    
    # Test 2: Stop Primary (should auto-failover)
    log("\n--- Test 2: Stop Primary (Auto-failover) ---")
    docker_stop("postgres-primary")
    time.sleep(10)  # Wait for failover
    
    check_cluster_status()
    
    # Test API after failover
    log("Testing API after failover...")
    test_api_endpoint("/health")
    test_api_endpoint("/api/users/all")
    
    # Test write operation
    test_data = {
        "username": f"testuser_{int(time.time())}",
        "email": f"test_{int(time.time())}@test.com",
        "password": "123456"
    }
    test_api_endpoint("/api/users/create", "POST", test_data)
    
    # Test 3: Start Primary back (should become replica)
    log("\n--- Test 3: Start Primary back ---")
    docker_start("postgres-primary")
    time.sleep(15)  # Wait for rejoin
    
    check_cluster_status()
    
    # Test 4: Stop Replica
    log("\n--- Test 4: Stop Replica ---")
    docker_stop("postgres-replica-1")
    time.sleep(5)
    
    test_api_endpoint("/health")
    test_api_endpoint("/api/users/all")
    
    log("\n=== Test Complete ===")

if __name__ == "__main__":
    main()

