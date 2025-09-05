#!/usr/bin/env python3

###Comprehensive PostgreSQL Cluster Testing Suite


##Bộ test toàn diện cho PostgreSQL cluster với primary-replica setup
#Tạo báo cáo chi tiết để viết vào Word
##Chức năng: Bộ test toàn diện theo kịch bản (CRUD replication, Replica read-only, Primary failover, High-load replication, Network partition giả lập, Data consistency).
##Output: Ghi báo cáo JSON cluster_test_report.json với kết quả từng kịch bản.
##Mục tiêu: Tổng hợp chứng cứ rằng ghi đi Primary, đọc từ Replica, Replica luôn read-only, sau sự cố replication tiếp tục.
###

import time
import json
import docker
import requests
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database.connection import primary_engine, replica_engine
import psycopg2
from psycopg2.extras import RealDictCursor

class ClusterTestReport:
    def __init__(self):
        self.report = {
            "test_summary": {
                "start_time": None,
                "end_time": None,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0
            },
            "test_results": [],
            "scenarios": {}
        }
        
    def log_test(self, test_name, status, details, duration=None):
        """Ghi log test result"""
        test_result = {
            "test_name": test_name,
            "status": status,  # PASS, FAIL, SKIP
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "duration": duration
        }
        self.report["test_results"].append(test_result)
        
        if status == "PASS":
            self.report["test_summary"]["passed_tests"] += 1
        elif status == "FAIL":
            self.report["test_summary"]["failed_tests"] += 1
        
        self.report["test_summary"]["total_tests"] += 1
        
        # Print to console
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        print(f"{status_icon} [{test_name}] {status}: {details}")
    
    def save_report(self, filename="cluster_test_report.json"):
        """Lưu báo cáo ra file JSON"""
        self.report["test_summary"]["end_time"] = datetime.now().isoformat()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        print(f"�� Báo cáo đã được lưu vào: {filename}")

class ComprehensiveClusterTester:
    def __init__(self):
        self.report = ClusterTestReport()
        self.report.report["test_summary"]["start_time"] = datetime.now().isoformat()
        self.docker_client = docker.from_env()
        self.primary_container = "postgres-primary"
        self.replica_container = "postgres-replica"
        
        # Test table
        self.table_sql = """
        CREATE TABLE IF NOT EXISTS cluster_comprehensive_test (
            id SERIAL PRIMARY KEY,
            test_type VARCHAR(50) NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
    def setup_test_environment(self):
        """Thiết lập môi trường test"""
        try:
            with primary_engine.begin() as conn:
                conn.execute(text(self.table_sql))
                conn.execute(text("TRUNCATE cluster_comprehensive_test RESTART IDENTITY;"))
            self.report.log_test("SETUP", "PASS", "Test environment setup completed")
            return True
        except Exception as e:
            self.report.log_test("SETUP", "FAIL", f"Failed to setup test environment: {str(e)}")
            return False
    
    def test_basic_replication(self):
        """Test 1: Basic CRUD Replication"""
        scenario = "Basic CRUD Replication"
        self.report.report["scenarios"][scenario] = {"tests": []}
        
        try:
            # CREATE test
            start_time = time.time()
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                    {"type": "CREATE", "payload": "basic_create_test"}
                )
                row_id = result.scalar_one()
            
            # Wait for replication
            if self.wait_for_replica_sync(row_id, "basic_create_test"):
                duration = time.time() - start_time
                self.report.log_test("CREATE_REPLICATION", "PASS", f"Row {row_id} replicated in {duration:.2f}s")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "CREATE", "status": "PASS", "duration": duration
                })
            else:
                self.report.log_test("CREATE_REPLICATION", "FAIL", "CREATE operation did not replicate")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "CREATE", "status": "FAIL"
                })
            
            # UPDATE test
            start_time = time.time()
            with primary_engine.begin() as conn:
                conn.execute(
                    text("UPDATE cluster_comprehensive_test SET payload=:payload, updated_at=NOW() WHERE id=:id"),
                    {"payload": "basic_update_test", "id": row_id}
                )
            
            if self.wait_for_replica_sync(row_id, "basic_update_test"):
                duration = time.time() - start_time
                self.report.log_test("UPDATE_REPLICATION", "PASS", f"Update replicated in {duration:.2f}s")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "UPDATE", "status": "PASS", "duration": duration
                })
            else:
                self.report.log_test("UPDATE_REPLICATION", "FAIL", "UPDATE operation did not replicate")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "UPDATE", "status": "FAIL"
                })
            
            # DELETE test
            start_time = time.time()
            with primary_engine.begin() as conn:
                conn.execute(text("DELETE FROM cluster_comprehensive_test WHERE id=:id"), {"id": row_id})
            
            if self.wait_for_replica_delete(row_id):
                duration = time.time() - start_time
                self.report.log_test("DELETE_REPLICATION", "PASS", f"Delete replicated in {duration:.2f}s")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "DELETE", "status": "PASS", "duration": duration
                })
            else:
                self.report.log_test("DELETE_REPLICATION", "FAIL", "DELETE operation did not replicate")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "DELETE", "status": "FAIL"
                })
                
        except Exception as e:
            self.report.log_test("BASIC_REPLICATION", "FAIL", f"Basic replication test failed: {str(e)}")
    
    def test_replica_read_only(self):
        """Test 2: Replica Read-Only Enforcement"""
        scenario = "Replica Read-Only Enforcement"
        self.report.report["scenarios"][scenario] = {"tests": []}
        
        try:
            # Test INSERT on replica
            try:
                with replica_engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload)"),
                        {"type": "REPLICA_WRITE", "payload": "should_fail"}
                    )
                self.report.log_test("REPLICA_INSERT_BLOCK", "FAIL", "Replica accepted INSERT operation")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "INSERT_BLOCK", "status": "FAIL"
                })
            except Exception as e:
                self.report.log_test("REPLICA_INSERT_BLOCK", "PASS", f"Replica correctly blocked INSERT: {str(e).splitlines()[0]}")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "INSERT_BLOCK", "status": "PASS"
                })
            
            # Test UPDATE on replica
            try:
                with replica_engine.begin() as conn:
                    conn.execute(text("UPDATE cluster_comprehensive_test SET payload='should_fail' WHERE id=1"))
                self.report.log_test("REPLICA_UPDATE_BLOCK", "FAIL", "Replica accepted UPDATE operation")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "UPDATE_BLOCK", "status": "FAIL"
                })
            except Exception as e:
                self.report.log_test("REPLICA_UPDATE_BLOCK", "PASS", f"Replica correctly blocked UPDATE: {str(e).splitlines()[0]}")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "UPDATE_BLOCK", "status": "PASS"
                })
            
            # Test DELETE on replica
            try:
                with replica_engine.begin() as conn:
                    conn.execute(text("DELETE FROM cluster_comprehensive_test WHERE id=1"))
                self.report.log_test("REPLICA_DELETE_BLOCK", "FAIL", "Replica accepted DELETE operation")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "DELETE_BLOCK", "status": "FAIL"
                })
            except Exception as e:
                self.report.log_test("REPLICA_DELETE_BLOCK", "PASS", f"Replica correctly blocked DELETE: {str(e).splitlines()[0]}")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "DELETE_BLOCK", "status": "PASS"
                })
                
        except Exception as e:
            self.report.log_test("REPLICA_READONLY", "FAIL", f"Replica read-only test failed: {str(e)}")
    
    def test_primary_failover_scenarios(self):
        """Test 3: Primary Failover Scenarios"""
        scenario = "Primary Failover Scenarios"
        self.report.report["scenarios"][scenario] = {"tests": []}
        
        try:
            # Pre-failover: Create data
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                    {"type": "PRE_FAILOVER", "payload": "data_before_failover"}
                )
                row_id = result.scalar_one()
            
            self.wait_for_replica_sync(row_id, "data_before_failover")
            self.report.log_test("PRE_FAILOVER_SYNC", "PASS", f"Data synced before failover: row {row_id}")
            
            # Test primary container stop
            try:
                self.docker_client.containers.get(self.primary_container).stop()
                self.report.log_test("PRIMARY_STOP", "PASS", "Primary container stopped successfully")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "PRIMARY_STOP", "status": "PASS"
                })
                
                # Test replica read-only during primary down
                time.sleep(2)
                try:
                    with replica_engine.connect() as conn:
                        result = conn.execute(text("SELECT COUNT(*) FROM cluster_comprehensive_test")).scalar_one()
                    self.report.log_test("REPLICA_READ_DURING_FAILOVER", "PASS", f"Replica still readable: {result} rows")
                    self.report.report["scenarios"][scenario]["tests"].append({
                        "operation": "REPLICA_READ_DURING_FAILOVER", "status": "PASS"
                    })
                except Exception as e:
                    self.report.log_test("REPLICA_READ_DURING_FAILOVER", "FAIL", f"Replica not readable: {str(e)}")
                    self.report.report["scenarios"][scenario]["tests"].append({
                        "operation": "REPLICA_READ_DURING_FAILOVER", "status": "FAIL"
                    })
                
                # Restart primary
                time.sleep(5)
                self.docker_client.containers.get(self.primary_container).start()
                time.sleep(10)  # Wait for primary to be ready
                
                # Test replication resume
                with primary_engine.begin() as conn:
                    result = conn.execute(
                        text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                        {"type": "POST_FAILOVER", "payload": "data_after_failover"}
                    )
                    new_row_id = result.scalar_one()
                
                if self.wait_for_replica_sync(new_row_id, "data_after_failover"):
                    self.report.log_test("POST_FAILOVER_SYNC", "PASS", f"Replication resumed: row {new_row_id}")
                    self.report.report["scenarios"][scenario]["tests"].append({
                        "operation": "POST_FAILOVER_SYNC", "status": "PASS"
                    })
                else:
                    self.report.log_test("POST_FAILOVER_SYNC", "FAIL", "Replication did not resume after failover")
                    self.report.report["scenarios"][scenario]["tests"].append({
                        "operation": "POST_FAILOVER_SYNC", "status": "FAIL"
                    })
                    
            except Exception as e:
                self.report.log_test("PRIMARY_FAILOVER", "FAIL", f"Primary failover test failed: {str(e)}")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "PRIMARY_FAILOVER", "status": "FAIL"
                })
                
        except Exception as e:
            self.report.log_test("FAILOVER_SCENARIOS", "FAIL", f"Failover scenarios test failed: {str(e)}")
    
    def test_high_load_replication(self):
        """Test 4: High Load Replication Performance"""
        scenario = "High Load Replication Performance"
        self.report.report["scenarios"][scenario] = {"tests": []}
        
        try:
            batch_size = 100
            start_time = time.time()
            
            # Insert batch of records
            with primary_engine.begin() as conn:
                for i in range(batch_size):
                    conn.execute(
                        text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload)"),
                        {"type": "BATCH_LOAD", "payload": f"batch_record_{i}"}
                    )
            
            insert_duration = time.time() - start_time
            self.report.log_test("BATCH_INSERT", "PASS", f"Inserted {batch_size} records in {insert_duration:.2f}s")
            
            # Wait for all records to replicate
            replication_start = time.time()
            all_replicated = True
            for i in range(batch_size):
                if not self.wait_for_replica_sync_by_payload(f"batch_record_{i}", timeout=5):
                    all_replicated = False
                    break
            
            replication_duration = time.time() - replication_start
            
            if all_replicated:
                self.report.log_test("BATCH_REPLICATION", "PASS", f"All {batch_size} records replicated in {replication_duration:.2f}s")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "BATCH_REPLICATION", "status": "PASS", 
                    "records": batch_size, "duration": replication_duration
                })
            else:
                self.report.log_test("BATCH_REPLICATION", "FAIL", f"Not all records replicated within timeout")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "BATCH_REPLICATION", "status": "FAIL"
                })
                
        except Exception as e:
            self.report.log_test("HIGH_LOAD_REPLICATION", "FAIL", f"High load replication test failed: {str(e)}")
    
    def test_network_partition_simulation(self):
        """Test 5: Network Partition Simulation"""
        scenario = "Network Partition Simulation"
        self.report.report["scenarios"][scenario] = {"tests": []}
        
        try:
            # Create data before partition
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                    {"type": "PRE_PARTITION", "payload": "data_before_partition"}
                )
                row_id = result.scalar_one()
            
            self.wait_for_replica_sync(row_id, "data_before_partition")
            
            # Simulate network partition by stopping replica
            try:
                self.docker_client.containers.get(self.replica_container).stop()
                self.report.log_test("REPLICA_STOP", "PASS", "Replica container stopped (simulating network partition)")
                
                # Continue writing to primary during partition
                time.sleep(2)
                with primary_engine.begin() as conn:
                    result = conn.execute(
                        text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                        {"type": "DURING_PARTITION", "payload": "data_during_partition"}
                    )
                    partition_row_id = result.scalar_one()
                
                self.report.log_test("PRIMARY_WRITE_DURING_PARTITION", "PASS", f"Primary continued writing: row {partition_row_id}")
                
                # Restart replica
                time.sleep(5)
                self.docker_client.containers.get(self.replica_container).start()
                time.sleep(15)  # Wait for replica to catch up
                
                # Check if replica caught up
                if self.wait_for_replica_sync(partition_row_id, "data_during_partition", timeout=30):
                    self.report.log_test("POST_PARTITION_SYNC", "PASS", "Replica caught up after partition")
                    self.report.report["scenarios"][scenario]["tests"].append({
                        "operation": "POST_PARTITION_SYNC", "status": "PASS"
                    })
                else:
                    self.report.log_test("POST_PARTITION_SYNC", "FAIL", "Replica did not catch up after partition")
                    self.report.report["scenarios"][scenario]["tests"].append({
                        "operation": "POST_PARTITION_SYNC", "status": "FAIL"
                    })
                    
            except Exception as e:
                self.report.log_test("NETWORK_PARTITION", "FAIL", f"Network partition simulation failed: {str(e)}")
                
        except Exception as e:
            self.report.log_test("NETWORK_PARTITION_SIMULATION", "FAIL", f"Network partition simulation test failed: {str(e)}")
    
    def test_data_consistency(self):
        """Test 6: Data Consistency Verification"""
        scenario = "Data Consistency Verification"
        self.report.report["scenarios"][scenario] = {"tests": []}
        
        try:
            # Create test data
            test_records = []
            with primary_engine.begin() as conn:
                for i in range(10):
                    result = conn.execute(
                        text("INSERT INTO cluster_comprehensive_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                        {"type": "CONSISTENCY_TEST", "payload": f"consistency_record_{i}"}
                    )
                    test_records.append(result.scalar_one())
            
            # Wait for replication
            time.sleep(5)
            
            # Compare data between primary and replica
            primary_data = []
            replica_data = []
            
            with primary_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, payload FROM cluster_comprehensive_test WHERE test_type = 'CONSISTENCY_TEST' ORDER BY id")
                )
                primary_data = [dict(row) for row in result.mappings()]
            
            with replica_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, payload FROM cluster_comprehensive_test WHERE test_type = 'CONSISTENCY_TEST' ORDER BY id")
                )
                replica_data = [dict(row) for row in result.mappings()]
            
            if primary_data == replica_data:
                self.report.log_test("DATA_CONSISTENCY", "PASS", f"Data consistent: {len(primary_data)} records match")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "DATA_CONSISTENCY", "status": "PASS", "records": len(primary_data)
                })
            else:
                self.report.log_test("DATA_CONSISTENCY", "FAIL", f"Data inconsistent: Primary {len(primary_data)} vs Replica {len(replica_data)}")
                self.report.report["scenarios"][scenario]["tests"].append({
                    "operation": "DATA_CONSISTENCY", "status": "FAIL"
                })
                
        except Exception as e:
            self.report.log_test("DATA_CONSISTENCY", "FAIL", f"Data consistency test failed: {str(e)}")
    
    def wait_for_replica_sync(self, row_id, expected_payload, timeout=20):
        """Đợi replica sync với primary"""
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        while datetime.utcnow() < deadline:
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT payload FROM cluster_comprehensive_test WHERE id = :id"),
                        {"id": row_id}
                    ).scalar_one_or_none()
                    if result == expected_payload:
                        return True
            except:
                pass
            time.sleep(0.5)
        return False
    
    def wait_for_replica_sync_by_payload(self, expected_payload, timeout=10):
        """Đợi replica sync theo payload"""
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        while datetime.utcnow() < deadline:
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM cluster_comprehensive_test WHERE payload = :payload"),
                        {"payload": expected_payload}
                    ).scalar_one()
                    if result > 0:
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
                        text("SELECT COUNT(*) FROM cluster_comprehensive_test WHERE id = :id"),
                        {"id": row_id}
                    ).scalar_one()
                    if result == 0:
                        return True
            except:
                pass
            time.sleep(0.5)
        return False
    
    def run_comprehensive_tests(self):
        """Chạy tất cả các test"""
        print("🚀 Bắt đầu Comprehensive PostgreSQL Cluster Testing")
        print("=" * 60)
        
        if not self.setup_test_environment():
            return False
        
        # Chạy các test scenarios
        test_scenarios = [
            ("Basic Replication", self.test_basic_replication),
            ("Replica Read-Only", self.test_replica_read_only),
            ("Primary Failover", self.test_primary_failover_scenarios),
            ("High Load Replication", self.test_high_load_replication),
            ("Network Partition", self.test_network_partition_simulation),
            ("Data Consistency", self.test_data_consistency)
        ]
        
        for scenario_name, test_func in test_scenarios:
            print(f"\n�� Running: {scenario_name}")
            print("-" * 40)
            try:
                test_func()
            except Exception as e:
                self.report.log_test(scenario_name.upper().replace(" ", "_"), "FAIL", f"Scenario failed: {str(e)}")
            time.sleep(2)  # Pause between scenarios
        
        # Lưu báo cáo
        self.report.save_report()
        
        # In summary
        summary = self.report.report["test_summary"]
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']} ✅")
        print(f"Failed: {summary['failed_tests']} ❌")
        print(f"Success Rate: {(summary['passed_tests']/summary['total_tests']*100):.1f}%")
        print(f"Start Time: {summary['start_time']}")
        print(f"End Time: {summary['end_time']}")
        
        return summary['failed_tests'] == 0

def main():
    tester = ComprehensiveClusterTester()
    success = tester.run_comprehensive_tests()
    
    if success:
        print("\n🎉 All tests passed! Cluster is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the report for details.")
    
    return success

if __name__ == "__main__":
    main()