#!/usr/bin/env python3

###Simple PostgreSQL Cluster Test
###Test đơn giản để kiểm tra hoạt động cơ bản của cluster
###

import time
import docker
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database.connection import primary_engine, replica_engine

def log(message, level="INFO"):
    """Log message với timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icon = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️"
    print(f"[{timestamp}] {icon} {message}")

def setup_test_table():
    """Tạo bảng test"""
    table_sql = """
    CREATE TABLE IF NOT EXISTS simple_cluster_test (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        with primary_engine.begin() as conn:
            conn.execute(text(table_sql))
            conn.execute(text("TRUNCATE simple_cluster_test RESTART IDENTITY;"))
        log("Test table created and cleaned", "SUCCESS")
        return True
    except Exception as e:
        log(f"Failed to setup test table: {str(e)}", "ERROR")
        return False

def wait_for_replica_sync(row_id, expected_message, timeout=20):
    """Đợi replica sync"""
    deadline = datetime.utcnow() + timedelta(seconds=timeout)
    while datetime.utcnow() < deadline:
        try:
            with replica_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT message FROM simple_cluster_test WHERE id = :id"),
                    {"id": row_id}
                ).scalar_one_or_none()
                if result == expected_message:
                    return True
        except:
            pass
        time.sleep(0.5)
    return False

def test_basic_crud():
    """Test CRUD cơ bản"""
    log("=== TEST: BASIC CRUD OPERATIONS ===", "INFO")
    
    try:
        # CREATE
        with primary_engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO simple_cluster_test (message) VALUES (:msg) RETURNING id"),
                {"msg": "Hello from primary"}
            )
            row_id = result.scalar_one()
        
        log(f"Created record {row_id} on primary", "SUCCESS")
        
        # Wait for replication
        if wait_for_replica_sync(row_id, "Hello from primary"):
            log("Record replicated to replica", "SUCCESS")
        else:
            log("Record did not replicate to replica", "ERROR")
            return False
        
        # UPDATE
        with primary_engine.begin() as conn:
            conn.execute(
                text("UPDATE simple_cluster_test SET message = :msg WHERE id = :id"),
                {"msg": "Updated from primary", "id": row_id}
            )
        
        log("Updated record on primary", "SUCCESS")
        
        if wait_for_replica_sync(row_id, "Updated from primary"):
            log("Update replicated to replica", "SUCCESS")
        else:
            log("Update did not replicate to replica", "ERROR")
            return False
        
        # DELETE
        with primary_engine.begin() as conn:
            conn.execute(text("DELETE FROM simple_cluster_test WHERE id = :id"), {"id": row_id})
        
        log("Deleted record on primary", "SUCCESS")
        
        # Wait for delete replication
        deadline = datetime.utcnow() + timedelta(seconds=20)
        while datetime.utcnow() < deadline:
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM simple_cluster_test WHERE id = :id"),
                        {"id": row_id}
                    ).scalar_one()
                    if result == 0:
                        log("Delete replicated to replica", "SUCCESS")
                        return True
            except:
                pass
            time.sleep(0.5)
        
        log("Delete did not replicate to replica", "ERROR")
        return False
        
    except Exception as e:
        log(f"Basic CRUD test failed: {str(e)}", "ERROR")
        return False

def test_replica_read_only():
    """Test replica read-only"""
    log("=== TEST: REPLICA READ-ONLY ===", "INFO")
    
    try:
        # Test INSERT on replica
        try:
            with replica_engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO simple_cluster_test (message) VALUES (:msg)"),
                    {"msg": "This should fail"}
                )
            log("Replica accepted INSERT - THIS IS BAD!", "ERROR")
            return False
        except Exception as e:
            log(f"Replica correctly blocked INSERT: {str(e).splitlines()[0]}", "SUCCESS")
        
        return True
        
    except Exception as e:
        log(f"Replica read-only test failed: {str(e)}", "ERROR")
        return False

def test_primary_failover():
    """Test primary failover"""
    log("=== TEST: PRIMARY FAILOVER ===", "INFO")
    
    try:
        docker_client = docker.from_env()
        primary_container = "postgres-primary"
        
        # Create data before failover
        with primary_engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO simple_cluster_test (message) VALUES (:msg) RETURNING id"),
                {"msg": "Before failover"}
            )
            row_id = result.scalar_one()
        
        log(f"Created record {row_id} before failover", "SUCCESS")
        
        # Wait for replication
        if wait_for_replica_sync(row_id, "Before failover"):
            log("Data synced before failover", "SUCCESS")
        else:
            log("Data did not sync before failover", "ERROR")
            return False
        
        # Stop primary
        log("Stopping primary container...", "INFO")
        docker_client.containers.get(primary_container).stop()
        time.sleep(3)
        log("Primary container stopped", "SUCCESS")
        
        # Test replica read during primary down
        try:
            with replica_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM simple_cluster_test")).scalar_one()
            log(f"Replica still readable during primary down: {result} rows", "SUCCESS")
        except Exception as e:
            log(f"Replica not readable during primary down: {str(e)}", "ERROR")
        
        # Restart primary
        log("Starting primary container...", "INFO")
        docker_client.containers.get(primary_container).start()
        time.sleep(10)
        log("Primary container started", "SUCCESS")
        
        # Test replication resume
        with primary_engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO simple_cluster_test (message) VALUES (:msg) RETURNING id"),
                {"msg": "After failover"}
            )
            new_row_id = result.scalar_one()
        
        if wait_for_replica_sync(new_row_id, "After failover"):
            log(f"Replication resumed after failover: record {new_row_id}", "SUCCESS")
            return True
        else:
            log("Replication did not resume after failover", "ERROR")
            return False
        
    except Exception as e:
        log(f"Primary failover test failed: {str(e)}", "ERROR")
        return False

def main():
    log("🚀 Starting Simple PostgreSQL Cluster Test", "INFO")
    log("=" * 50, "INFO")
    
    if not setup_test_table():
        return False
    
    tests = [
        ("Basic CRUD Operations", test_basic_crud),
        ("Replica Read-Only", test_replica_read_only),
        ("Primary Failover", test_primary_failover)
    ]
    
    results = []
    for test_name, test_func in tests:
        log(f"\n🔄 Running: {test_name}", "INFO")
        log("-" * 30, "INFO")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            log(f"Test {test_name} failed with error: {str(e)}", "ERROR")
            results.append((test_name, False))
        time.sleep(1)
    
    # Summary
    log("\n" + "=" * 50, "INFO")
    log("📊 TEST SUMMARY", "INFO")
    log("=" * 50, "INFO")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        log(f"{status} - {test_name}", "INFO")
    
    log(f"\nTotal: {total} | Passed: {passed} | Failed: {total - passed}", "INFO")
    log(f"Success Rate: {(passed/total*100):.1f}%", "SUCCESS" if passed == total else "WARNING")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed!")