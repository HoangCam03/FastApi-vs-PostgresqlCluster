#!/usr/bin/env python3
"""
Test script for pg_auto_failover functionality
"""

import psycopg2
import time
import requests
import json
from datetime import datetime

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,  # HAProxy port
    'database': 'blink_db',
    'user': 'blink_user',
    'password': '12345'
}

def test_database_connection():
    """Test database connection through HAProxy"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Database connection successful: {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_write_operation():
    """Test write operation (should work on primary)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create test table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failover_test (
                id SERIAL PRIMARY KEY,
                test_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Insert test data
        cursor.execute("""
            INSERT INTO failover_test (test_data) 
            VALUES (%s) RETURNING id;
        """, (f"Test data at {datetime.now()}",))
        
        test_id = cursor.fetchone()[0]
        print(f"✅ Write operation successful. Test ID: {test_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Write operation failed: {e}")
        return False

def test_read_operation():
    """Test read operation"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM failover_test;")
        count = cursor.fetchone()[0]
        print(f"✅ Read operation successful. Total records: {count}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Read operation failed: {e}")
        return False

def check_pg_auto_failover_status():
    """Check pg_auto_failover cluster status"""
    try:
        # This would require connecting to the monitor directly
        # For now, we'll check HAProxy stats
        response = requests.get("http://localhost:5000/stats")
        if response.status_code == 200:
            print("✅ HAProxy stats accessible")
            return True
        else:
            print("❌ HAProxy stats not accessible")
            return False
    except Exception as e:
        print(f"❌ Cannot check pg_auto_failover status: {e}")
        return False

def simulate_primary_failure():
    """Simulate primary failure by stopping primary container"""
    print("\n🔄 Simulating primary failure...")
    print("⚠️  Please manually stop the postgres-primary container:")
    print("   docker stop postgres-primary")
    print("⏳ Waiting 30 seconds for failover...")
    
    for i in range(30, 0, -1):
        print(f"   {i} seconds remaining...", end='\r')
        time.sleep(1)
    
    print("\n✅ Failover simulation complete")

def main():
    print("🧪 pg_auto_failover Test Suite")
    print("=" * 50)
    
    # Test 1: Basic connection
    print("\n1. Testing database connection...")
    if not test_database_connection():
        print("❌ Cannot proceed without database connection")
        return
    
    # Test 2: Write operation
    print("\n2. Testing write operation...")
    test_write_operation()
    
    # Test 3: Read operation
    print("\n3. Testing read operation...")
    test_read_operation()
    
    # Test 4: Check cluster status
    print("\n4. Checking cluster status...")
    check_pg_auto_failover_status()
    
    # Test 5: Simulate failure
    print("\n5. Simulating primary failure...")
    simulate_primary_failure()
    
    # Test 6: Test after failover
    print("\n6. Testing after failover...")
    print("   Testing connection after failover...")
    test_database_connection()
    print("   Testing write after failover...")
    test_write_operation()
    print("   Testing read after failover...")
    test_read_operation()
    
    print("\n🎉 Test suite completed!")

if __name__ == "__main__":
    main()
