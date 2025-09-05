#!/usr/bin/env python3
"""
Network & Performance Testing Suite for PostgreSQL Cluster
Bộ test chuyên về network scenarios và performance testing
"""

##tion, high-frequency ops, memory under load, interruption recovery.
##Output: network_performance_test_report.json.
##Mục tiêu: Đo độ trễ và khả năng phục hồi khi mạng/replica có vấn đề; đọc vẫn dùng Replica, ghi chỉ Primary.

import time
import json
import docker
import threading
import concurrent.futures
import requests
import socket
import subprocess
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database.connection import primary_engine, replica_engine
import psutil
import statistics

class NetworkPerformanceTester:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.primary_container = "postgres-primary"
        self.replica_container = "postgres-replica"
        self.test_results = []
        
        # Test table
        self.table_sql = """
        CREATE TABLE IF NOT EXISTS network_performance_test (
            id SERIAL PRIMARY KEY,
            test_type VARCHAR(50) NOT NULL,
            payload TEXT NOT NULL,
            size_bytes INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
    def log_test(self, test_name, status, details, duration=None, metrics=None):
        """Ghi log test result với metrics"""
        test_result = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "metrics": metrics or {}
        }
        self.test_results.append(test_result)
        
        # Print to console
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        print(f"{status_icon} [{test_name}] {status}: {details}")
        if metrics:
            print(f"    📊 Metrics: {metrics}")
    
    def setup_test_environment(self):
        """Thiết lập môi trường test"""
        try:
            with primary_engine.begin() as conn:
                conn.execute(text(self.table_sql))
                conn.execute(text("TRUNCATE network_performance_test RESTART IDENTITY;"))
            self.log_test("SETUP", "PASS", "Network performance test environment setup completed")
            return True
        except Exception as e:
            self.log_test("SETUP", "FAIL", f"Failed to setup test environment: {str(e)}")
            return False
    
    def test_network_latency_measurement(self):
        """Test 1: Network Latency Measurement"""
        test_name = "NETWORK_LATENCY_MEASUREMENT"
        
        try:
            latencies = []
            
            for i in range(20):
                # Measure primary latency
                start_time = time.time()
                with primary_engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO network_performance_test (test_type, payload) VALUES (:type, :payload)"),
                        {"type": "LATENCY_TEST", "payload": f"latency_test_{i}"}
                    )
                primary_latency = time.time() - start_time
                
                # Measure replica read latency
                start_time = time.time()
                with replica_engine.connect() as conn:
                    conn.execute(text("SELECT COUNT(*) FROM network_performance_test"))
                replica_latency = time.time() - start_time
                
                latencies.append({
                    "primary_latency": primary_latency,
                    "replica_latency": replica_latency,
                    "difference": abs(primary_latency - replica_latency)
                })
                
                time.sleep(0.1)
            
            # Calculate statistics
            primary_latencies = [l["primary_latency"] for l in latencies]
            replica_latencies = [l["replica_latency"] for l in latencies]
            
            metrics = {
                "primary_avg_latency": statistics.mean(primary_latencies),
                "primary_max_latency": max(primary_latencies),
                "primary_min_latency": min(primary_latencies),
                "replica_avg_latency": statistics.mean(replica_latencies),
                "replica_max_latency": max(replica_latencies),
                "replica_min_latency": min(replica_latencies),
                "avg_difference": statistics.mean([l["difference"] for l in latencies])
            }
            
            self.log_test(test_name, "PASS", f"Network latency measured: Primary avg={metrics['primary_avg_latency']:.3f}s, Replica avg={metrics['replica_avg_latency']:.3f}s", metrics=metrics)
            
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Network latency measurement failed: {str(e)}")
    
    def test_network_partition_scenarios(self):
        """Test 2: Network Partition Scenarios"""
        test_name = "NETWORK_PARTITION_SCENARIOS"
        
        try:
            # Scenario 1: Stop replica (simulate network partition)
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO network_performance_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                    {"type": "PRE_PARTITION", "payload": "before_partition"}
                )
                row_id = result.scalar_one()
            
            # Stop replica
            self.docker_client.containers.get(self.replica_container).stop()
            time.sleep(2)
            
            # Continue writing to primary during partition
            partition_writes = []
            for i in range(5):
                with primary_engine.begin() as conn:
                    result = conn.execute(
                        text("INSERT INTO network_performance_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                        {"type": "DURING_PARTITION", "payload": f"during_partition_{i}"}
                    )
                    partition_writes.append(result.scalar_one())
                time.sleep(1)
            
            # Restart replica
            self.docker_client.containers.get(self.replica_container).start()
            time.sleep(15)  # Wait for replica to catch up
            
            # Check if all writes are replicated
            replicated_count = 0
            for write_id in partition_writes:
                try:
                    with replica_engine.connect() as conn:
                        result = conn.execute(
                            text("SELECT COUNT(*) FROM network_performance_test WHERE id = :id"),
                            {"id": write_id}
                        ).scalar_one()
                        if result > 0:
                            replicated_count += 1
                except:
                    pass
            
            metrics = {
                "partition_writes": len(partition_writes),
                "replicated_writes": replicated_count,
                "replication_rate": replicated_count / len(partition_writes) if partition_writes else 0
            }
            
            if replicated_count >= len(partition_writes) * 0.8:  # 80% replication rate
                self.log_test(test_name, "PASS", f"Network partition recovery: {replicated_count}/{len(partition_writes)} writes replicated", metrics=metrics)
            else:
                self.log_test(test_name, "FAIL", f"Network partition recovery failed: {replicated_count}/{len(partition_writes)} writes replicated", metrics=metrics)
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Network partition scenarios failed: {str(e)}")
    
    def test_bandwidth_utilization(self):
        """Test 3: Bandwidth Utilization Test"""
        test_name = "BANDWIDTH_UTILIZATION"
        
        try:
            # Test with different payload sizes
            payload_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB
            results = []
            
            for size in payload_sizes:
                payload = "x" * size
                
                # Measure write time
                start_time = time.time()
                with primary_engine.begin() as conn:
                    result = conn.execute(
                        text("INSERT INTO network_performance_test (test_type, payload, size_bytes) VALUES (:type, :payload, :size) RETURNING id"),
                        {"type": "BANDWIDTH_TEST", "payload": payload, "size": size}
                    )
                    row_id = result.scalar_one()
                write_time = time.time() - start_time
                
                # Wait for replication
                time.sleep(2)
                
                # Measure read time from replica
                start_time = time.time()
                with replica_engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT payload FROM network_performance_test WHERE id = :id"),
                        {"id": row_id}
                    ).scalar_one()
                read_time = time.time() - start_time
                
                # Calculate bandwidth
                write_bandwidth = size / write_time if write_time > 0 else 0
                read_bandwidth = size / read_time if read_time > 0 else 0
                
                results.append({
                    "size_bytes": size,
                    "write_time": write_time,
                    "read_time": read_time,
                    "write_bandwidth": write_bandwidth,
                    "read_bandwidth": read_bandwidth
                })
            
            metrics = {
                "payload_sizes": payload_sizes,
                "avg_write_bandwidth": statistics.mean([r["write_bandwidth"] for r in results]),
                "avg_read_bandwidth": statistics.mean([r["read_bandwidth"] for r in results]),
                "max_write_bandwidth": max([r["write_bandwidth"] for r in results]),
                "max_read_bandwidth": max([r["read_bandwidth"] for r in results])
            }
            
            self.log_test(test_name, "PASS", f"Bandwidth utilization tested: Write avg={metrics['avg_write_bandwidth']:.2f} bytes/s, Read avg={metrics['avg_read_bandwidth']:.2f} bytes/s", metrics=metrics)
            
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Bandwidth utilization test failed: {str(e)}")
    
    def test_connection_pool_exhaustion(self):
        """Test 4: Connection Pool Exhaustion Test"""
        test_name = "CONNECTION_POOL_EXHAUSTION"
        
        try:
            # Test with many concurrent connections
            num_connections = 100
            results = []
            
            def connection_worker(worker_id):
                try:
                    # Create new engine for this worker
                    engine = create_engine(
                        "postgresql://blink_user:12345@postgres-primary:5432/blink_db",
                        pool_size=1,
                        max_overflow=0
                    )
                    
                    with engine.begin() as conn:
                        result = conn.execute(
                            text("INSERT INTO network_performance_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                            {"type": "POOL_TEST", "payload": f"worker_{worker_id}"}
                        )
                        row_id = result.scalar_one()
                    
                    engine.dispose()
                    return row_id
                except Exception as e:
                    return f"ERROR: {str(e)}"
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
                futures = [executor.submit(connection_worker, i) for i in range(num_connections)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            duration = time.time() - start_time
            
            successful_connections = len([r for r in results if isinstance(r, int)])
            
            metrics = {
                "total_connections": num_connections,
                "successful_connections": successful_connections,
                "success_rate": successful_connections / num_connections,
                "duration": duration
            }
            
            if successful_connections >= num_connections * 0.9:  # 90% success rate
                self.log_test(test_name, "PASS", f"Connection pool exhaustion test: {successful_connections}/{num_connections} connections successful", metrics=metrics)
            else:
                self.log_test(test_name, "FAIL", f"Connection pool exhaustion test failed: {successful_connections}/{num_connections} connections successful", metrics=metrics)
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Connection pool exhaustion test failed: {str(e)}")
    
    def test_high_frequency_operations(self):
        """Test 5: High Frequency Operations"""
        test_name = "HIGH_FREQUENCY_OPERATIONS"
        
        try:
            # Test rapid insert/update/delete cycles
            num_cycles = 1000
            start_time = time.time()
            
            successful_operations = 0
            
            for i in range(num_cycles):
                try:
                    # Insert
                    with primary_engine.begin() as conn:
                        result = conn.execute(
                            text("INSERT INTO network_performance_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                            {"type": "HIGH_FREQ", "payload": f"cycle_{i}"}
                        )
                        row_id = result.scalar_one()
                    
                    # Update
                    with primary_engine.begin() as conn:
                        conn.execute(
                            text("UPDATE network_performance_test SET payload = :payload WHERE id = :id"),
                            {"payload": f"updated_cycle_{i}", "id": row_id}
                        )
                    
                    # Delete
                    with primary_engine.begin() as conn:
                        conn.execute(
                            text("DELETE FROM network_performance_test WHERE id = :id"),
                            {"id": row_id}
                        )
                    
                    successful_operations += 1
                    
                except Exception as e:
                    pass  # Count as failed operation
            
            duration = time.time() - start_time
            operations_per_second = successful_operations / duration if duration > 0 else 0
            
            metrics = {
                "total_cycles": num_cycles,
                "successful_operations": successful_operations,
                "success_rate": successful_operations / num_cycles,
                "operations_per_second": operations_per_second,
                "duration": duration
            }
            
            if successful_operations >= num_cycles * 0.95:  # 95% success rate
                self.log_test(test_name, "PASS", f"High frequency operations: {successful_operations}/{num_cycles} operations at {operations_per_second:.1f} ops/sec", metrics=metrics)
            else:
                self.log_test(test_name, "FAIL", f"High frequency operations failed: {successful_operations}/{num_cycles} operations successful", metrics=metrics)
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"High frequency operations test failed: {str(e)}")
    
    def test_memory_usage_under_load(self):
        """Test 6: Memory Usage Under Load"""
        test_name = "MEMORY_USAGE_UNDER_LOAD"
        
        try:
            # Get initial memory usage
            initial_memory = psutil.virtual_memory().percent
            
            # Create memory-intensive load
            def memory_intensive_worker(worker_id):
                results = []
                try:
                    for i in range(50):
                        # Large payload to consume memory
                        large_payload = "x" * 50000  # 50KB per record
                        with primary_engine.begin() as conn:
                            result = conn.execute(
                                text("INSERT INTO network_performance_test (test_type, payload, size_bytes) VALUES (:type, :payload, :size) RETURNING id"),
                                {"type": "MEMORY_LOAD", "payload": large_payload, "size": len(large_payload)}
                            )
                            row_id = result.scalar_one()
                            results.append(row_id)
                        
                        # Read from replica to add more memory pressure
                        with replica_engine.connect() as conn:
                            conn.execute(
                                text("SELECT payload FROM network_performance_test WHERE id = :id"),
                                {"id": row_id}
                            )
                        
                        time.sleep(0.01)  # Small delay
                except Exception as e:
                    results.append(f"ERROR: {str(e)}")
                return results
            
            # Run multiple workers
            num_workers = 5
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(memory_intensive_worker, i) for i in range(num_workers)]
                all_results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            duration = time.time() - start_time
            
            # Get final memory usage
            final_memory = psutil.virtual_memory().percent
            memory_increase = final_memory - initial_memory
            
            # Count successful operations
            successful_operations = sum(1 for result in all_results for item in result if isinstance(item, int))
            total_operations = num_workers * 50
            
            metrics = {
                "initial_memory_percent": initial_memory,
                "final_memory_percent": final_memory,
                "memory_increase": memory_increase,
                "successful_operations": successful_operations,
                "total_operations": total_operations,
                "success_rate": successful_operations / total_operations,
                "duration": duration
            }
            
            if successful_operations >= total_operations * 0.9 and memory_increase < 20:  # 90% success and <20% memory increase
                self.log_test(test_name, "PASS", f"Memory usage under load: {successful_operations}/{total_operations} operations, memory +{memory_increase:.1f}%", metrics=metrics)
            else:
                self.log_test(test_name, "FAIL", f"Memory usage under load failed: {successful_operations}/{total_operations} operations, memory +{memory_increase:.1f}%", metrics=metrics)
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Memory usage under load test failed: {str(e)}")
    
    def test_network_interruption_recovery(self):
        """Test 7: Network Interruption Recovery"""
        test_name = "NETWORK_INTERRUPTION_RECOVERY"
        
        try:
            # Create initial data
            with primary_engine.begin() as conn:
                result = conn.execute(
                    text("INSERT INTO network_performance_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                    {"type": "PRE_INTERRUPTION", "payload": "before_interruption"}
                )
                row_id = result.scalar_one()
            
            # Simulate network interruption by stopping both containers briefly
            self.docker_client.containers.get(self.primary_container).stop()
            self.docker_client.containers.get(self.replica_container).stop()
            time.sleep(5)
            
            # Restart containers
            self.docker_client.containers.get(self.primary_container).start()
            self.docker_client.containers.get(self.replica_container).start()
            time.sleep(15)  # Wait for services to be ready
            
            # Test recovery
            recovery_writes = []
            for i in range(10):
                try:
                    with primary_engine.begin() as conn:
                        result = conn.execute(
                            text("INSERT INTO network_performance_test (test_type, payload) VALUES (:type, :payload) RETURNING id"),
                            {"type": "POST_INTERRUPTION", "payload": f"recovery_{i}"}
                        )
                        recovery_writes.append(result.scalar_one())
                except Exception as e:
                    recovery_writes.append(f"ERROR: {str(e)}")
                time.sleep(0.5)
            
            # Check replication recovery
            time.sleep(5)
            replicated_count = 0
            for write_id in recovery_writes:
                if isinstance(write_id, int):
                    try:
                        with replica_engine.connect() as conn:
                            result = conn.execute(
                                text("SELECT COUNT(*) FROM network_performance_test WHERE id = :id"),
                                {"id": write_id}
                            ).scalar_one()
                            if result > 0:
                                replicated_count += 1
                    except:
                        pass
            
            metrics = {
                "recovery_writes": len([w for w in recovery_writes if isinstance(w, int)]),
                "replicated_writes": replicated_count,
                "recovery_rate": replicated_count / len([w for w in recovery_writes if isinstance(w, int)]) if recovery_writes else 0
            }
            
            if replicated_count >= len([w for w in recovery_writes if isinstance(w, int)]) * 0.8:
                self.log_test(test_name, "PASS", f"Network interruption recovery: {replicated_count}/{len([w for w in recovery_writes if isinstance(w, int)])} writes recovered", metrics=metrics)
            else:
                self.log_test(test_name, "FAIL", f"Network interruption recovery failed: {replicated_count}/{len([w for w in recovery_writes if isinstance(w, int)])} writes recovered", metrics=metrics)
                
        except Exception as e:
            self.log_test(test_name, "FAIL", f"Network interruption recovery test failed: {str(e)}")
    
    def run_network_performance_tests(self):
        """Chạy tất cả các test network và performance"""
        print("🚀 Bắt đầu Network & Performance Testing")
        print("=" * 60)
        
        if not self.setup_test_environment():
            return False
        
        # Danh sách các test
        tests = [
            ("Network Latency Measurement", self.test_network_latency_measurement),
            ("Network Partition Scenarios", self.test_network_partition_scenarios),
            ("Bandwidth Utilization", self.test_bandwidth_utilization),
            ("Connection Pool Exhaustion", self.test_connection_pool_exhaustion),
            ("High Frequency Operations", self.test_high_frequency_operations),
            ("Memory Usage Under Load", self.test_memory_usage_under_load),
            ("Network Interruption Recovery", self.test_network_interruption_recovery)
        ]
        
        for test_name, test_func in tests:
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
        
        with open("network_performance_test_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 Báo cáo đã được lưu vào: network_performance_test_report.json")
    
    def print_summary(self):
        """In summary kết quả"""
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        total = len(self.test_results)
        
        print("\n" + "=" * 60)
        print("📊 NETWORK & PERFORMANCE TEST SUMMARY")
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
    tester = NetworkPerformanceTester()
    success = tester.run_network_performance_tests()
    
    if success:
        print("\n🎉 Network & Performance tests completed successfully!")
    else:
        print("\n⚠️ Some network & performance tests failed. Check the report for details.")
    
    return success

if __name__ == "__main__":
    main()
