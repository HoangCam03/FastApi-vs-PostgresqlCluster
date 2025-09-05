#!/usr/bin/env python3
"""
Advanced PostgreSQL Cluster Testing Suite
Bộ test nâng cao cho PostgreSQL cluster với các scenario phức tạp
Bổ sung các trường hợp test còn thiếu từ các file test hiện tại
Mục tiêu: Chứng minh dưới tải nặng/transaction dài/DDL thì ghi vẫn đi Primary, đọc vẫn từ Replica; Replica luôn read-only; replication bắt kịp sau sự cố.
"""

import time
import json
import docker
import threading
import concurrent.futures
import psutil
from datetime import datetime, timedelta
from sqlalchemy import text, create_engine
from app.database.connection import primary_engine, replica_engine
import psycopg2
from psycopg2.extras import RealDictCursor

class AdvancedClusterTester:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.primary_container = "postgres-primary"
        self.replica_container = "postgres-replica"
        self.test_results = []
        
        # Test table
        self.table_sql = """
        CREATE TABLE IF NOT EXISTS advanced_cluster_test (
            id SERIAL PRIMARY KEY,
            test_type VARCHAR(50) NOT NULL,
            payload TEXT NOT NULL,
            thread_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
    def log_test(self, test_name, status, details, duration=None):
        """Ghi log test result"""
        test_result = {
            "test_name": test_name,
            "status": status,  # PASS, FAIL, SKIP
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "duration": duration
        }
        self.test_results.append(test_result)
        
        # Print to console
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        print(f"{status_icon} [{test_name}] {status}: {details}")
    
    def setup_test_environment(self):
        """Thiết lập môi trường test"""
        try:
            with primary_engine.begin() as conn:
                conn.execute(text(self.table_sql))
                conn.execute(text("TRUNCATE advanced_cluster_test RESTART IDENTITY;"))
            self.log_test("SETUP", "PASS", "Advanced test environment setup completed")
            return True
        except Exception as e:
            self.log_test("SETUP", "FAIL", f"Failed to setup test environment: {str(e)}")
            return False
    
    def test_connection_pooling_stress(self):
        """Test 1: Connection Pooling Stress Test"""
        test_name = "CONNECTION_POOLING_STRESS"
        
        try:
            num_threads = 50
            operations_per_thread = 10
            start_time = time.time()
            
            def worker_thread(thread_id):
                """Worker thread để test connection pooling"""
                results = []
                try:
                    for i in range(operations_per_thread):
                        with primary_engine.begin() as conn:
                            result = conn.execute(
                                text("INSERT INTO advanced_cluster_test (test_type, payload, thread_id) VALUES (:type, :payload, :thread_id) RETURNING id"),
                                {"type": "POOL_STRESS", "payload": f"thread_{thread_id}_op_{i}", "thread_id": thread_id}
                            )
                            row_id = result.scalar_one()
                            results.append(row_id)
                except Exception as e:
                    results.append(f"ERROR: {str(e)}")
                return results
            
            # Chạy concurrent threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
                all_results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            duration = time.time() - start_time
            total_operations = num_threads * operations_per_thread
            
            # Kiểm tra kết quả
            successful_operations = sum(1 for result in all_results for item in result if isinstance(item, int))
            
            if successful_operations >= total_operations * 0.95:  # 95% success rate
                self.log_test(test_name, "PASS", f"Connection pooling stress test: {successful_operations}/{total_operations} operations successful in {duration:.2f}s")
            else:
                self.log_test(test_name, "FAIL", f"Connection pooling stress test failed: {successful_operations}/{total_operations} operations successful")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Connection pooling stress test failed: {str(e)}")
    
    def test_replication_lag_monitoring(self):
        """Test 2: Replication Lag Monitoring"""
        test_name = "REPLICATION_LAG_MONITORING"
        
        try:
            lag_measurements = []
            
            for i in range(10):
                # Insert on primary
                start_time = time.time()
                with primary_engine.begin() as conn:
                    result = conn.execute(
                        text("INSERT INTO advanced_cluster_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                        {"type": "LAG_TEST", "payload": f"lag_test_{i}"}
                    )
                    row_id = result.scalar_one()
                
                # Wait for replication
                deadline = datetime.utcnow() + timedelta(seconds=10)
                replicated = False
                while datetime.utcnow() < deadline:
                    try:
                        with replica_engine.connect() as conn:
                            result = conn.execute(
                                text("SELECT COUNT(*) FROM advanced_cluster_test WHERE id = :id"),
                                {"id": row_id}
                            ).scalar_one()
                            if result > 0:
                                replicated = True
                                break
                    except:
                        pass
                    time.sleep(0.1)
                
                if replicated:
                    lag_time = time.time() - start_time
                    lag_measurements.append(lag_time)
                
                time.sleep(0.5)  # Pause between measurements
            
            if lag_measurements:
                avg_lag = sum(lag_measurements) / len(lag_measurements)
                max_lag = max(lag_measurements)
                min_lag = min(lag_measurements)
                
                self.log_test(test_name, "PASS", f"Replication lag monitoring: avg={avg_lag:.3f}s, max={max_lag:.3f}s, min={min_lag:.3f}s")
            else:
                self.log_test(test_name, "FAIL", "No replication lag measurements collected")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Replication lag monitoring failed: {str(e)}")
    
    def test_long_running_transaction(self):
        """Test 3: Long Running Transaction Test"""
        test_name = "LONG_RUNNING_TRANSACTION"
        
        try:
            # Start long transaction on primary
            def long_transaction():
                try:
                    with primary_engine.begin() as conn:
                        # Insert initial record
                        result = conn.execute(
                            text("INSERT INTO advanced_cluster_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                            {"type": "LONG_TX", "payload": "long_transaction_start"}
                        )
                        row_id = result.scalar_one()
                        
                        # Simulate long operation
                        for i in range(5):
                            time.sleep(2)  # 2 seconds per step
                            conn.execute(
                                text("UPDATE advanced_cluster_test SET payload = :payload WHERE id = :id"),
                                {"payload": f"long_transaction_step_{i}", "id": row_id}
                            )
                        
                        # Final update
                        conn.execute(
                            text("UPDATE advanced_cluster_test SET payload = :payload WHERE id = :id"),
                            {"payload": "long_transaction_complete", "id": row_id}
                        )
                    return row_id
                except Exception as e:
                    return f"ERROR: {str(e)}"
            
            # Run long transaction in separate thread
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(long_transaction)
                
                # Monitor replication during long transaction
                replication_checks = []
                while not future.done():
                    time.sleep(1)
                    # Check if any intermediate updates are visible on replica
                    try:
                        with replica_engine.connect() as conn:
                            result = conn.execute(
                                text("SELECT COUNT(*) FROM advanced_cluster_test WHERE test_type = 'LONG_TX'")
                            ).scalar_one()
                            replication_checks.append(result)
                    except:
                        pass
                
                result = future.result()
                duration = time.time() - start_time
            
            if isinstance(result, int):
                # Check final replication
                time.sleep(2)
                try:
                    with replica_engine.connect() as conn:
                        final_payload = conn.execute(
                            text("SELECT payload FROM advanced_cluster_test WHERE id = :id"),
                            {"id": result}
                        ).scalar_one()
                    
                    if final_payload == "long_transaction_complete":
                        self.log_test(test_name, "PASS", f"Long running transaction completed and replicated in {duration:.2f}s")
                    else:
                        self.log_test(test_name, "FAIL", f"Long transaction completed but final state not replicated: {final_payload}")
                except Exception as e:
                    self.log_test(test_name, "FAIL", f"Long transaction completed but replication check failed: {str(e)}")
            else:
                self.log_test(test_name, "FAIL", f"Long running transaction failed: {result}")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Long running transaction test failed: {str(e)}")
    
    def test_transaction_rollback_scenarios(self):
        """Test 4: Transaction Rollback Scenarios"""
        test_name = "TRANSACTION_ROLLBACK"
        
        try:
            # Test rollback on primary
            initial_count = 0
            with primary_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM advanced_cluster_test")).scalar_one()
                initial_count = result
            
            # Start transaction and rollback
            try:
                with primary_engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO advanced_cluster_test (test_type, payload) VALUES (:type, :payload)"),
                        {"type": "ROLLBACK_TEST", "payload": "should_be_rolled_back"}
                    )
                    # Force rollback by raising exception
                    raise Exception("Forced rollback")
            except:
                pass  # Expected rollback
            
            # Check that rollback worked
            time.sleep(1)
            with primary_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM advanced_cluster_test")).scalar_one()
                if result == initial_count:
                    self.log_test(test_name, "PASS", "Transaction rollback on primary worked correctly")
                else:
                    self.log_test(test_name, "FAIL", f"Transaction rollback failed: count changed from {initial_count} to {result}")
            
            # Test that rollback doesn't affect replica
            time.sleep(2)
            with replica_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM advanced_cluster_test")).scalar_one()
                if result == initial_count:
                    self.log_test(test_name, "PASS", "Rollback correctly not replicated to replica")
                else:
                    self.log_test(test_name, "FAIL", f"Rollback incorrectly affected replica: count is {result}")
                    
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Transaction rollback test failed: {str(e)}")
    
    def test_schema_changes_replication(self):
        """Test 5: Schema Changes Replication (DDL Operations)"""
        test_name = "SCHEMA_CHANGES_REPLICATION"
        
        try:
            # Create new table on primary
            with primary_engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_test_table (
                        id SERIAL PRIMARY KEY,
                        test_column VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            
            # Insert test data
            with primary_engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO schema_test_table (test_column) VALUES (:value)"),
                    {"value": "schema_test_data"}
                )
            
            # Wait for schema and data replication
            time.sleep(5)
            
            # Check if table exists on replica
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(text("SELECT test_column FROM schema_test_table LIMIT 1")).scalar_one()
                    if result == "schema_test_data":
                        self.log_test(test_name, "PASS", "Schema changes and data replicated to replica")
                    else:
                        self.log_test(test_name, "FAIL", f"Schema replicated but data incorrect: {result}")
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Schema changes not replicated to replica: {str(e)}")
            
            # Cleanup
            with primary_engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS schema_test_table"))
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Schema changes replication test failed: {str(e)}")
    
    def test_memory_cpu_stress(self):
        """Test 6: Memory/CPU Stress Test"""
        test_name = "MEMORY_CPU_STRESS"
        
        try:
            # Get initial system stats
            initial_memory = psutil.virtual_memory().percent
            initial_cpu = psutil.cpu_percent(interval=1)
            
            # Create memory/CPU intensive operations
            def stress_worker(worker_id):
                results = []
                try:
                    for i in range(20):  # 20 operations per worker
                        # Memory intensive: large payload
                        large_payload = "x" * 10000  # 10KB payload
                        with primary_engine.begin() as conn:
                            result = conn.execute(
                                text("INSERT INTO advanced_cluster_test (test_type, payload, thread_id) VALUES (:type, :payload, :thread_id) RETURNING id"),
                                {"type": "STRESS_TEST", "payload": large_payload, "thread_id": worker_id}
                            )
                            row_id = result.scalar_one()
                            results.append(row_id)
                        
                        # CPU intensive: complex query
                        with primary_engine.begin() as conn:
                            conn.execute(
                                text("UPDATE advanced_cluster_test SET payload = :payload WHERE id = :id"),
                                {"payload": f"stress_updated_{i}", "id": row_id}
                            )
                        
                        time.sleep(0.1)  # Small delay
                except Exception as e:
                    results.append(f"ERROR: {str(e)}")
                return results
            
            # Run stress test with multiple workers
            num_workers = 10
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(stress_worker, i) for i in range(num_workers)]
                all_results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            duration = time.time() - start_time
            
            # Get final system stats
            final_memory = psutil.virtual_memory().percent
            final_cpu = psutil.cpu_percent(interval=1)
            
            # Check results
            successful_operations = sum(1 for result in all_results for item in result if isinstance(item, int))
            total_operations = num_workers * 20
            
            memory_increase = final_memory - initial_memory
            cpu_increase = final_cpu - initial_cpu
            
            if successful_operations >= total_operations * 0.9:  # 90% success rate
                self.log_test(test_name, "PASS", f"Stress test completed: {successful_operations}/{total_operations} operations in {duration:.2f}s, Memory: +{memory_increase:.1f}%, CPU: +{cpu_increase:.1f}%")
            else:
                self.log_test(test_name, "FAIL", f"Stress test failed: {successful_operations}/{total_operations} operations successful")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Memory/CPU stress test failed: {str(e)}")
    
    def test_replica_promotion_simulation(self):
        """Test 7: Replica Promotion Simulation"""
        test_name = "REPLICA_PROMOTION_SIMULATION"
        
        try:
            # Create data before promotion simulation
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO advanced_cluster_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                    {"type": "PRE_PROMOTION", "payload": "data_before_promotion"}
                )
                row_id = result.scalar_one()
            
            # Wait for replication
            time.sleep(3)
            
            # Simulate replica promotion by stopping primary
            self.docker_client.containers.get(self.primary_container).stop()
            time.sleep(5)
            
            # Test replica read-only during "promotion"
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM advanced_cluster_test")).scalar_one()
                    self.log_test(test_name, "PASS", f"Replica readable during promotion simulation: {result} rows")
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Replica not readable during promotion: {str(e)}")
            
            # Restart primary (simulate promotion complete)
            self.docker_client.containers.get(self.primary_container).start()
            time.sleep(10)
            
            # Test replication resume
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO advanced_cluster_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                    {"type": "POST_PROMOTION", "payload": "data_after_promotion"}
                )
                new_row_id = result.scalar_one()
            
            # Wait for replication
            time.sleep(5)
            
            try:
                with replica_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT payload FROM advanced_cluster_test WHERE id = :id"),
                        {"id": new_row_id}
                    ).scalar_one()
                    if result == "data_after_promotion":
                        self.log_test(test_name, "PASS", "Replication resumed after promotion simulation")
                    else:
                        self.log_test(test_name, "FAIL", f"Replication not resumed correctly: {result}")
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Replication check after promotion failed: {str(e)}")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Replica promotion simulation failed: {str(e)}")
    
    def test_concurrent_read_write_operations(self):
        """Test 8: Concurrent Read/Write Operations"""
        test_name = "CONCURRENT_READ_WRITE"
        
        try:
            def writer_worker(worker_id):
                """Worker để ghi dữ liệu"""
                results = []
                try:
                    for i in range(10):
                        with primary_engine.begin() as conn:
                            result = conn.execute(
                                text("INSERT INTO advanced_cluster_test (test_type, payload, thread_id) VALUES (:type, :payload, :thread_id) RETURNING id"),
                                {"type": "CONCURRENT_WRITE", "payload": f"writer_{worker_id}_op_{i}", "thread_id": worker_id}
                            )
                            row_id = result.scalar_one()
                            results.append(row_id)
                        time.sleep(0.1)
                except Exception as e:
                    results.append(f"ERROR: {str(e)}")
                return results
            
            def reader_worker(worker_id):
                """Worker để đọc dữ liệu từ replica"""
                results = []
                try:
                    for i in range(20):
                        with replica_engine.connect() as conn:
                            result = conn.execute(
                                text("SELECT COUNT(*) FROM advanced_cluster_test WHERE test_type = 'CONCURRENT_WRITE'")
                            ).scalar_one()
                            results.append(result)
                        time.sleep(0.05)
                except Exception as e:
                    results.append(f"ERROR: {str(e)}")
                return results
            
            # Run concurrent readers and writers
            num_writers = 5
            num_readers = 10
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
                # Submit writers
                writer_futures = [executor.submit(writer_worker, i) for i in range(num_writers)]
                # Submit readers
                reader_futures = [executor.submit(reader_worker, i) for i in range(num_readers)]
                
                # Collect results
                writer_results = [future.result() for future in concurrent.futures.as_completed(writer_futures)]
                reader_results = [future.result() for future in concurrent.futures.as_completed(reader_futures)]
            
            duration = time.time() - start_time
            
            # Analyze results
            successful_writes = sum(1 for result in writer_results for item in result if isinstance(item, int))
            total_writes = num_writers * 10
            
            successful_reads = sum(1 for result in reader_results for item in result if isinstance(item, int))
            total_reads = num_readers * 20
            
            if successful_writes >= total_writes * 0.95 and successful_reads >= total_reads * 0.95:
                self.log_test(test_name, "PASS", f"Concurrent operations: {successful_writes}/{total_writes} writes, {successful_reads}/{total_reads} reads in {duration:.2f}s")
            else:
                self.log_test(test_name, "FAIL", f"Concurrent operations failed: {successful_writes}/{total_writes} writes, {successful_reads}/{total_reads} reads")
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Concurrent read/write test failed: {str(e)}")
    
    def run_advanced_tests(self):
        """Chạy tất cả các test nâng cao"""
        print("🚀 Bắt đầu Advanced PostgreSQL Cluster Testing")
        print("=" * 60)
        
        if not self.setup_test_environment():
            return False
        
        # Danh sách các test nâng cao
        advanced_tests = [
            ("Connection Pooling Stress", self.test_connection_pooling_stress),
            ("Replication Lag Monitoring", self.test_replication_lag_monitoring),
            ("Long Running Transaction", self.test_long_running_transaction),
            ("Transaction Rollback", self.test_transaction_rollback_scenarios),
            ("Schema Changes Replication", self.test_schema_changes_replication),
            ("Memory/CPU Stress", self.test_memory_cpu_stress),
            ("Replica Promotion Simulation", self.test_replica_promotion_simulation),
            ("Concurrent Read/Write", self.test_concurrent_read_write_operations)
        ]
        
        for test_name, test_func in advanced_tests:
            print(f"\n🔄 Running: {test_name}")
            print("-" * 40)
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name.upper().replace(" ", "_"), "FAIL", f"Test failed: {str(e)}")
            time.sleep(2)  # Pause between tests
        
        # Lưu kết quả
        self.save_results()
        
        # In summary
        self.print_summary()
        
        return self.get_success_rate() >= 0.8  # 80% success rate
    
    def save_results(self):
        """Lưu kết quả test"""
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "passed_tests": len([r for r in self.test_results if r["status"] == "PASS"]),
                "failed_tests": len([r for r in self.test_results if r["status"] == "FAIL"])
            },
            "test_results": self.test_results
        }
        
        with open("advanced_cluster_test_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 Báo cáo đã được lưu vào: advanced_cluster_test_report.json")
    
    def print_summary(self):
        """In summary kết quả"""
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        total = len(self.test_results)
        
        print("\n" + "=" * 60)
        print("📊 ADVANCED TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%")
    
    def get_success_rate(self):
        """Tính tỷ lệ thành công"""
        if not self.test_results:
            return 0
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        return passed / len(self.test_results)

def main():
    tester = AdvancedClusterTester()
    success = tester.run_advanced_tests()
    
    if success:
        print("\n🎉 Advanced tests completed successfully!")
    else:
        print("\n⚠️ Some advanced tests failed. Check the report for details.")
    
    return success

if __name__ == "__main__":
    main()
