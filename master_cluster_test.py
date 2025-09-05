#!/usr/bin/env python3
"""
Master PostgreSQL Cluster Testing Suite
Script tổng hợp để chạy tất cả các test cluster
"""

## Trình điều phối chạy tất cả test suites (simple, flow, scenarios, CRUD API, comprehensive, advanced, network), gom kết quả và xuất report master_cluster_test_report_YYYYMMDD_HHMMSS.json.
##Mục tiêu: Một lệnh duy nhất để tạo toàn bộ chứng cứ cho báo cáo.


import time
import json
import subprocess
import sys
from datetime import datetime
import os

class MasterClusterTester:
    def __init__(self):
        self.test_suites = [
            {
                "name": "Simple Cluster Test",
                "file": "simple_cluster_test.py",
                "description": "Test cơ bản CRUD, replica read-only, primary failover"
            },
            {
                "name": "Primary Replica Flow Test", 
                "file": "test_primary_replica_flow.py",
                "description": "Test flow giữa primary và replica"
            },
            {
                "name": "Cluster Scenarios Test",
                "file": "cluster_scenarios_test.py", 
                "description": "Test các scenarios phức tạp"
            },
            {
                "name": "CRUD Operations Test",
                "file": "test_crud_operations.py",
                "description": "Test CRUD operations qua API"
            },
            {
                "name": "Comprehensive Cluster Test",
                "file": "comprehensive_cluster_test.py",
                "description": "Test toàn diện với 6 scenarios chính"
            },
            {
                "name": "Advanced Cluster Test",
                "file": "advanced_cluster_test.py",
                "description": "Test nâng cao với connection pooling, replication lag, etc."
            },
            {
                "name": "Network Performance Test",
                "file": "network_performance_test.py",
                "description": "Test network scenarios và performance"
            }
        ]
        
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def log(self, message, level="INFO"):
        """Log message với timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️" if level == "INFO" else "⚠️"
        print(f"[{timestamp}] {icon} {message}")
    
    def run_test_suite(self, suite):
        """Chạy một test suite"""
        self.log(f"🔄 Starting: {suite['name']}", "INFO")
        self.log(f"📝 Description: {suite['description']}", "INFO")
        
        start_time = time.time()
        
        try:
            # Chạy test suite
            result = subprocess.run(
                [sys.executable, suite['file']],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                status = "PASS"
                self.log(f"✅ {suite['name']} completed successfully in {duration:.2f}s", "SUCCESS")
            else:
                status = "FAIL"
                self.log(f"❌ {suite['name']} failed after {duration:.2f}s", "ERROR")
                if result.stderr:
                    self.log(f"Error output: {result.stderr[:200]}...", "ERROR")
            
            return {
                "suite_name": suite['name'],
                "file": suite['file'],
                "status": status,
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.log(f"⏰ {suite['name']} timed out after {duration:.2f}s", "ERROR")
            return {
                "suite_name": suite['name'],
                "file": suite['file'],
                "status": "TIMEOUT",
                "duration": duration,
                "return_code": -1,
                "stdout": "",
                "stderr": "Test suite timed out"
            }
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 {suite['name']} crashed: {str(e)}", "ERROR")
            return {
                "suite_name": suite['name'],
                "file": suite['file'],
                "status": "CRASH",
                "duration": duration,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    def check_prerequisites(self):
        """Kiểm tra prerequisites"""
        self.log("🔍 Checking prerequisites...", "INFO")
        
        # Kiểm tra các file test có tồn tại không
        missing_files = []
        for suite in self.test_suites:
            if not os.path.exists(suite['file']):
                missing_files.append(suite['file'])
        
        if missing_files:
            self.log(f"❌ Missing test files: {', '.join(missing_files)}", "ERROR")
            return False
        
        # Kiểm tra Docker containers
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                running_containers = result.stdout.strip().split('\n')
                required_containers = ["postgres-primary", "postgres-replica"]
                
                missing_containers = [c for c in required_containers if c not in running_containers]
                if missing_containers:
                    self.log(f"⚠️ Missing containers: {', '.join(missing_containers)}", "WARNING")
                    self.log("Some tests may fail. Please start the cluster first.", "WARNING")
                else:
                    self.log("✅ All required containers are running", "SUCCESS")
            else:
                self.log("⚠️ Cannot check Docker containers", "WARNING")
        except FileNotFoundError:
            self.log("⚠️ Docker not found. Some tests may fail.", "WARNING")
        
        return True
    
    def run_all_tests(self, selected_suites=None):
        """Chạy tất cả các test"""
        self.log("🚀 Starting Master PostgreSQL Cluster Testing", "INFO")
        self.log("=" * 60, "INFO")
        
        if not self.check_prerequisites():
            return False
        
        # Chọn test suites để chạy
        suites_to_run = self.test_suites
        if selected_suites:
            suites_to_run = [s for s in self.test_suites if s['name'] in selected_suites]
        
        self.start_time = datetime.now()
        
        # Chạy từng test suite
        for i, suite in enumerate(suites_to_run, 1):
            self.log(f"\n📋 Test Suite {i}/{len(suites_to_run)}: {suite['name']}", "INFO")
            self.log("-" * 50, "INFO")
            
            result = self.run_test_suite(suite)
            self.results.append(result)
            
            # Pause between test suites
            if i < len(suites_to_run):
                self.log("⏸️ Pausing 5 seconds before next test suite...", "INFO")
                time.sleep(5)
        
        self.end_time = datetime.now()
        
        # Generate summary
        self.generate_summary()
        
        return True
    
    def generate_summary(self):
        """Tạo summary report"""
        self.log("\n" + "=" * 60, "INFO")
        self.log("📊 MASTER TEST SUMMARY", "INFO")
        self.log("=" * 60, "INFO")
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.results if r['status'] == 'FAIL'])
        timeout_tests = len([r for r in self.results if r['status'] == 'TIMEOUT'])
        crash_tests = len([r for r in self.results if r['status'] == 'CRASH'])
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        self.log(f"📅 Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        self.log(f"📅 End Time: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        self.log(f"⏱️ Total Duration: {total_duration:.2f} seconds", "INFO")
        self.log(f"📊 Total Test Suites: {total_tests}", "INFO")
        self.log(f"✅ Passed: {passed_tests}", "SUCCESS" if passed_tests > 0 else "INFO")
        self.log(f"❌ Failed: {failed_tests}", "ERROR" if failed_tests > 0 else "INFO")
        self.log(f"⏰ Timeout: {timeout_tests}", "WARNING" if timeout_tests > 0 else "INFO")
        self.log(f"💥 Crashed: {crash_tests}", "ERROR" if crash_tests > 0 else "INFO")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.log(f"📈 Success Rate: {success_rate:.1f}%", "SUCCESS" if success_rate >= 80 else "WARNING" if success_rate >= 60 else "ERROR")
        
        # Detailed results
        self.log("\n📋 DETAILED RESULTS:", "INFO")
        self.log("-" * 50, "INFO")
        
        for result in self.results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⏰" if result['status'] == 'TIMEOUT' else "💥"
            self.log(f"{status_icon} {result['suite_name']}: {result['status']} ({result['duration']:.2f}s)", "INFO")
        
        # Save detailed report
        self.save_detailed_report()
        
        # Final verdict
        if success_rate >= 80:
            self.log("\n🎉 CLUSTER TESTING COMPLETED SUCCESSFULLY!", "SUCCESS")
            self.log("Your PostgreSQL cluster is working well!", "SUCCESS")
        elif success_rate >= 60:
            self.log("\n⚠️ CLUSTER TESTING COMPLETED WITH WARNINGS", "WARNING")
            self.log("Some issues detected. Check the detailed report.", "WARNING")
        else:
            self.log("\n💥 CLUSTER TESTING FAILED", "ERROR")
            self.log("Multiple issues detected. Check the detailed report.", "ERROR")
    
    def save_detailed_report(self):
        """Lưu báo cáo chi tiết"""
        report = {
            "test_summary": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "total_duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0,
                "total_test_suites": len(self.results),
                "passed_tests": len([r for r in self.results if r['status'] == 'PASS']),
                "failed_tests": len([r for r in self.results if r['status'] == 'FAIL']),
                "timeout_tests": len([r for r in self.results if r['status'] == 'TIMEOUT']),
                "crash_tests": len([r for r in self.results if r['status'] == 'CRASH']),
                "success_rate": (len([r for r in self.results if r['status'] == 'PASS']) / len(self.results) * 100) if self.results else 0
            },
            "test_suites": self.test_suites,
            "detailed_results": self.results
        }
        
        filename = f"master_cluster_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log(f"📄 Detailed report saved to: {filename}", "INFO")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Master PostgreSQL Cluster Testing Suite')
    parser.add_argument('--suites', nargs='+', help='Specific test suites to run')
    parser.add_argument('--list', action='store_true', help='List available test suites')
    
    args = parser.parse_args()
    
    tester = MasterClusterTester()
    
    if args.list:
        print("📋 Available Test Suites:")
        print("-" * 50)
        for i, suite in enumerate(tester.test_suites, 1):
            print(f"{i}. {suite['name']}")
            print(f"   File: {suite['file']}")
            print(f"   Description: {suite['description']}")
            print()
        return
    
    # Chạy tests
    selected_suites = args.suites if args.suites else None
    success = tester.run_all_tests(selected_suites)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
