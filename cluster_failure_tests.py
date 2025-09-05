#!/usr/bin/env python3

###PostgreSQL Cluster Failure Testing Suite
###Bộ test kiểm tra các trường hợp bất thường giữa primary và replica
## Test các sự cố điển hình (stop/start Primary; stop/start Replica; restart cả hai; rapid restart).
##Mục tiêu: Khi Primary tắt: ghi hỏng nhưng đọc từ Replica vẫn OK; Replica vẫn chặn ghi; khi bật lại Primary, replication tiếp tục.
###

import time
import docker
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database.connection import primary_engine, replica_engine

class ClusterFailureTester:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.primary_container = "postgres-primary"
        self.replica_container = "postgres-replica-1"
        # Test table
        self.table_sql = """
        CREATE TABLE IF NOT EXISTS cluster_failure_test (
            id SERIAL PRIMARY KEY,
            test_scenario VARCHAR(50) NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
    def log(self, message, level="INFO"):
        """Log message với timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️" if level == "INFO" else "⚠️"
        print(f"[{timestamp}] {icon} {message}")
    
    def setup_test_environment(self):
        """Thiết lập môi trường test"""
        try:
            with primary_engine.begin() as conn:
                conn.execute(text(self.table_sql))
                conn.execute(text("TRUNCATE cluster_failure_test RESTART IDENTITY;"))
            self.log("Test environment setup completed", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Failed to setup test environment: {str(e)}", "ERROR")
            return False

    
    def wait_for_replica_sync(self, row_id, expected_payload, timeout=20):
        """Đợi replica sync với primary"""
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        while datetime.utcnow() < deadline:
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT payload FROM cluster_failure_test WHERE id = :id"),
                        {"id": row_id}
                    ).scalar_one_or_none()
                    if result == expected_payload:
                        return True
            except:
                pass
            time.sleep(0.5)
        return False
    
    def wait_for_replica_delete(self, row_id, timeout=20):
        """Đợi replica xóa record"""
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        while datetime.utcnow() < deadline:
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM cluster_failure_test WHERE id = :id"),
                        {"id": row_id}
                    ).scalar_one()
                    if result == 0:
                        return True
            except:
                pass
            time.sleep(0.5)
        return False
    
    def test_primary_stop_and_restart(self):
        """Test 1: Primary container stop và restart"""
        self.log("=== TEST 1: PRIMARY STOP AND RESTART ===", "INFO")
        
        try:
            # Tạo dữ liệu trước khi stop primary
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                    {"scenario": "BEFORE_PRIMARY_STOP", "payload": "data_before_primary_stop"}
                )
                row_id = result.scalar_one()
            
            self.log(f"Created data before primary stop: row {row_id}", "INFO")
            
            # Đợi replication
            if self.wait_for_replica_sync(row_id, "data_before_primary_stop"):
                self.log("Data synced to replica before primary stop", "SUCCESS")
            else:
                self.log("Data did not sync to replica before primary stop", "ERROR")
                return False
            
            # Stop primary container
            self.log("Stopping primary container...", "INFO")
            self.docker_client.containers.get(self.primary_container).stop()
            time.sleep(3)
            self.log("Primary container stopped", "SUCCESS")
            
            # Test replica read-only during primary down
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM cluster_failure_test")).scalar_one()
                self.log(f"Replica still readable during primary down: {result} rows", "SUCCESS")
            except Exception as e:
                self.log(f"Replica not readable during primary down: {str(e)}", "ERROR")
            
            # Test replica write blocking during primary down
            try:
                with replica_engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload)"),
                        {"scenario": "REPLICA_WRITE_DURING_PRIMARY_DOWN", "payload": "should_fail"}
                    )
                self.log("Replica accepted write during primary down - THIS IS BAD!", "ERROR")
            except Exception as e:
                self.log(f"Replica correctly blocked write during primary down: {str(e).splitlines()[0]}", "SUCCESS")
            
            # Restart primary
            self.log("Starting primary container...", "INFO")
            self.docker_client.containers.get(self.primary_container).start()
            time.sleep(10)  # Wait for primary to be ready
            self.log("Primary container started", "SUCCESS")
            
            # Test replication resume
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                    {"scenario": "AFTER_PRIMARY_RESTART", "payload": "data_after_primary_restart"}
                )
                new_row_id = result.scalar_one()
            
            if self.wait_for_replica_sync(new_row_id, "data_after_primary_restart"):
                self.log(f"Replication resumed after primary restart: row {new_row_id}", "SUCCESS")
            else:
                self.log("Replication did not resume after primary restart", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"Primary stop/restart test failed: {str(e)}", "ERROR")
            return False
    
    def test_replica_stop_and_restart(self):
        """Test 2: Replica container stop và restart"""
        self.log("=== TEST 2: REPLICA STOP AND RESTART ===", "INFO")
        
        try:
            # Tạo dữ liệu trước khi stop replica
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                    {"scenario": "BEFORE_REPLICA_STOP", "payload": "data_before_replica_stop"}
                )
                row_id = result.scalar_one()
            
            self.log(f"Created data before replica stop: row {row_id}", "INFO")
            
            # Đợi replication
            if self.wait_for_replica_sync(row_id, "data_before_replica_stop"):
                self.log("Data synced to replica before replica stop", "SUCCESS")
            else:
                self.log("Data did not sync to replica before replica stop", "ERROR")
                return False
            
            # Stop replica container
            self.log("Stopping replica container...", "INFO")
            self.docker_client.containers.get(self.replica_container).stop()
            time.sleep(3)
            self.log("Replica container stopped", "SUCCESS")
            
            # Continue writing to primary during replica down
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                    {"scenario": "DURING_REPLICA_DOWN", "payload": "data_during_replica_down"}
                )
                partition_row_id = result.scalar_one()
            
            self.log(f"Primary continued writing during replica down: row {partition_row_id}", "SUCCESS")
            
            # Restart replica
            self.log("Starting replica container...", "INFO")
            self.docker_client.containers.get(self.replica_container).start()
            time.sleep(15)  # Wait for replica to catch up
            self.log("Replica container started", "SUCCESS")
            
            # Check if replica caught up
            if self.wait_for_replica_sync(partition_row_id, "data_during_replica_down", timeout=30):
                self.log("Replica caught up after restart", "SUCCESS")
            else:
                self.log("Replica did not catch up after restart", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"Replica stop/restart test failed: {str(e)}", "ERROR")
            return False
    
    def test_both_containers_restart(self):
        """Test 3: Restart cả primary và replica"""
        self.log("=== TEST 3: BOTH CONTAINERS RESTART ===", "INFO")
        
        try:
            # Tạo dữ liệu trước khi restart
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                    {"scenario": "BEFORE_BOTH_RESTART", "payload": "data_before_both_restart"}
                )
                row_id = result.scalar_one()
            
            self.log(f"Created data before both restart: row {row_id}", "INFO")
            
            # Đợi replication
            if self.wait_for_replica_sync(row_id, "data_before_both_restart"):
                self.log("Data synced to replica before both restart", "SUCCESS")
            else:
                self.log("Data did not sync to replica before both restart", "ERROR")
                return False
            
            # Stop both containers
            self.log("Stopping both containers...", "INFO")
            self.docker_client.containers.get(self.primary_container).stop()
            self.docker_client.containers.get(self.replica_container).stop()
            time.sleep(5)
            self.log("Both containers stopped", "SUCCESS")
            # Start primary first
            self.log("Starting primary container...", "INFO")
            self.docker_client.containers.get(self.primary_container).start()
            time.sleep(10)
            self.log("Primary container started", "SUCCESS")
            # Start replica
            self.log("Starting replica container...", "INFO")
            self.docker_client.containers.get(self.replica_container).start()
            time.sleep(15)
            self.log("Replica container started", "SUCCESS")
            # Test replication after both restart
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                    {"scenario": "AFTER_BOTH_RESTART", "payload": "data_after_both_restart"}
                )
                new_row_id = result.scalar_one()
            if self.wait_for_replica_sync(new_row_id, "data_after_both_restart", timeout=30):
                self.log(f"Replication working after both restart: row {new_row_id}", "SUCCESS")
            else:
                self.log("Replication not working after both restart", "ERROR")
                return False
            return True  
        except Exception as e:
            self.log(f"Both containers restart test failed: {str(e)}", "ERROR")
            return False
    
    def test_rapid_primary_restart(self):
        """Test 4: Rapid primary restart (stress test)"""
        self.log("=== TEST 4: RAPID PRIMARY RESTART (STRESS TEST) ===", "INFO") 
        try:
            restart_count = 3
            for i in range(restart_count):
                self.log(f"Rapid restart cycle {i+1}/{restart_count}", "INFO")
                # Create data
                with primary_engine.begin() as conn:
                    result = conn.execute(
                        text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                        {"scenario": f"RAPID_RESTART_CYCLE_{i+1}", "payload": f"data_cycle_{i+1}"}
                    )
                    row_id = result.scalar_one()
                
                # Quick stop and start
                self.docker_client.containers.get(self.primary_container).stop()
                time.sleep(2)
                self.docker_client.containers.get(self.primary_container).start()
                time.sleep(8)
                
                # Check if data is still there
                with primary_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT payload FROM cluster_failure_test WHERE id = :id"),
                        {"id": row_id}
                    ).scalar_one_or_none()
                
                if result == f"data_cycle_{i+1}":
                    self.log(f"Data persisted through rapid restart cycle {i+1}", "SUCCESS")
                else:
                    self.log(f"Data lost during rapid restart cycle {i+1}", "ERROR")
                    return False
            
            self.log(f"Completed {restart_count} rapid restart cycles successfully", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Rapid primary restart test failed: {str(e)}", "ERROR")
            return False
    
    def test_replica_read_only_enforcement(self):
        """Test 5: Replica read-only enforcement"""
        self.log("=== TEST 5: REPLICA READ-ONLY ENFORCEMENT ===", "INFO")
        try:    # Test INSERT on replica
            try:
                with replica_engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload)"),
                        {"scenario": "REPLICA_INSERT_TEST", "payload": "should_fail"}
                    )
                self.log("Replica accepted INSERT - THIS IS BAD!", "ERROR")
                return False
            except Exception as e:
                self.log(f"Replica correctly blocked INSERT: {str(e).splitlines()[0]}", "SUCCESS")
            
            # Test UPDATE on replica
            try:
                with replica_engine.begin() as conn:
                    conn.execute(text("UPDATE cluster_failure_test SET payload='should_fail' WHERE id=1"))
                self.log("Replica accepted UPDATE - THIS IS BAD!", "ERROR")
                return False
            except Exception as e:
                self.log(f"Replica correctly blocked UPDATE: {str(e).splitlines()[0]}", "SUCCESS")
            # Test DELETE on replica
            try:
                with replica_engine.begin() as conn:
                    conn.execute(text("DELETE FROM cluster_failure_test WHERE id=1"))
                self.log("Replica accepted DELETE - THIS IS BAD!", "ERROR")
                return False
            except Exception as e:
                self.log(f"Replica correctly blocked DELETE: {str(e).splitlines()[0]}", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Replica read-only enforcement test failed: {str(e)}", "ERROR")
            return False
    
    def test_data_consistency_after_failures(self):
        """Test 6: Data consistency after various failures"""
        self.log("=== TEST 6: DATA CONSISTENCY AFTER FAILURES ===", "INFO")     
        try:
            # Create test data
            test_records = []
            with primary_engine.begin() as conn:
                for i in range(5):
                    result = conn.execute(
                        text("INSERT INTO cluster_failure_test (test_scenario, payload) VALUES (:scenario, :payload) RETURNING id"),
                        {"scenario": "CONSISTENCY_TEST", "payload": f"consistency_record_{i}"}
                    )
                    test_records.append(result.scalar_one())
            
            self.log(f"Created {len(test_records)} test records", "INFO")      
            # Wait for replication
            time.sleep(5)   
            # Compare data between primary and replica
            primary_data = []
            replica_data = []
            with primary_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, payload FROM cluster_failure_test WHERE test_scenario = 'CONSISTENCY_TEST' ORDER BY id")
                )
                primary_data = [dict(row) for row in result.mappings()]
            with replica_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, payload FROM cluster_failure_test WHERE test_scenario = 'CONSISTENCY_TEST' ORDER BY id")
                )
                replica_data = [dict(row) for row in result.mappings()]
            if primary_data == replica_data:
                self.log(f"Data consistent: {len(primary_data)} records match between primary and replica", "SUCCESS")
                return True
            else:
                self.log(f"Data inconsistent: Primary {len(primary_data)} vs Replica {len(replica_data)}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Data consistency test failed: {str(e)}", "ERROR")
            return False
    
    def run_all_failure_tests(self):
        """Chạy tất cả các test failure"""
        self.log("�� Bắt đầu PostgreSQL Cluster Failure Testing", "INFO")
        self.log("=" * 60, "INFO")
        
        if not self.setup_test_environment():
            return False
        
        # Danh sách các test
        tests = [
            ("Primary Stop and Restart", self.test_primary_stop_and_restart),
            ("Replica Stop and Restart", self.test_replica_stop_and_restart),
            ("Both Containers Restart", self.test_both_containers_restart),
            ("Rapid Primary Restart", self.test_rapid_primary_restart),
            ("Replica Read-Only Enforcement", self.test_replica_read_only_enforcement),
            ("Data Consistency After Failures", self.test_data_consistency_after_failures)
        ]
        
        results = []
        for test_name, test_func in tests:
            self.log(f"\n🔄 Running: {test_name}", "INFO")
            self.log("-" * 40, "INFO")
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    self.log(f"✅ {test_name} - PASSED", "SUCCESS")
                else:
                    self.log(f"❌ {test_name} - FAILED", "ERROR")
            except Exception as e:
                self.log(f"❌ {test_name} - ERROR: {str(e)}", "ERROR")
                results.append((test_name, False))
            time.sleep(2)  # Pause between tests
        
        # Tổng kết
        self.log("\n" + "=" * 60, "INFO")
        self.log("📊 TEST SUMMARY", "INFO")
        self.log("=" * 60, "INFO")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} - {test_name}", "INFO")
        
        self.log(f"\nTotal Tests: {total}", "INFO")
        self.log(f"Passed: {passed} ✅", "SUCCESS" if passed == total else "INFO")
        self.log(f"Failed: {total - passed} ❌", "ERROR" if total - passed > 0 else "INFO")
        self.log(f"Success Rate: {(passed/total*100):.1f}%", "SUCCESS" if passed == total else "WARNING")
        
        return passed == total

def main():
    tester = ClusterFailureTester()
    success = tester.run_all_failure_tests()
    
    if success:
        print("\n🎉 All failure tests passed! Cluster is resilient to failures.")
    else:
        print("\n⚠️ Some failure tests failed. Check the cluster configuration.")
    
    return success

if __name__ == "__main__":
    main()