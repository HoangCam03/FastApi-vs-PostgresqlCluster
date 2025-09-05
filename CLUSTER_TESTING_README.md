# PostgreSQL Cluster Testing Suite

Tài liệu hướng dẫn chạy toàn bộ các test suite, prerequisite, cách chạy từng file, ma trận coverage.

Mục tiêu: Làm căn cứ quy trình kiểm thử cho báo cáo.

Bộ test toàn diện cho PostgreSQL cluster với primary-replica setup.

## 📋 Tổng quan

Dự án này bao gồm 7 file test chính để kiểm tra các trường hợp hoạt động giữa replica và primary:

### 🧪 Các file test hiện có:

1. **`simple_cluster_test.py`** - Test cơ bản
   - CRUD operations
   - Replica read-only enforcement
   - Primary failover scenarios

2. **`test_primary_replica_flow.py`** - Test flow
   - Primary/Replica data flow
   - Replication timing
   - Read-only enforcement

3. **`cluster_scenarios_test.py`** - Test scenarios
   - CRUD + Replication
   - Failover scenarios
   - Docker container control

4. **`test_crud_operations.py`** - API testing
   - HTTP API CRUD operations
   - Bulk operations
   - Authentication testing

5. **`comprehensive_cluster_test.py`** - Test toàn diện
   - 6 scenarios chính
   - Báo cáo chi tiết JSON
   - Performance testing

6. **`advanced_cluster_test.py`** - Test nâng cao (MỚI)
   - Connection pooling stress test
   - Replication lag monitoring
   - Long running transaction test
   - Transaction rollback scenarios
   - Schema changes replication
   - Memory/CPU stress test
   - Replica promotion simulation
   - Concurrent read/write operations

7. **`network_performance_test.py`** - Test network & performance (MỚI)
   - Network latency measurement
   - Network partition scenarios
   - Bandwidth utilization test
   - Connection pool exhaustion
   - High frequency operations
   - Memory usage under load
   - Network interruption recovery

8. **`master_cluster_test.py`** - Master test suite (MỚI)
   - Chạy tất cả test suites
   - Báo cáo tổng hợp
   - Quản lý test execution

## 🚀 Cách sử dụng

### 1. Chạy tất cả tests:
```bash
python3 master_cluster_test.py
```

### 2. Chạy test cụ thể:
```bash
python3 simple_cluster_test.py
python3 advanced_cluster_test.py
python3 network_performance_test.py
```

### 3. Sử dụng script bash (Linux/Mac):
```bash
chmod +x run_cluster_tests.sh
./run_cluster_tests.sh all          # Chạy tất cả
./run_cluster_tests.sh quick        # Chạy test nhanh
./run_cluster_tests.sh advanced     # Chạy test nâng cao
./run_cluster_tests.sh network      # Chạy test network
```

### 4. Chạy test suites cụ thể:
```bash
python3 master_cluster_test.py --suites "Simple Cluster Test" "Advanced Cluster Test"
```

### 5. Liệt kê các test suites có sẵn:
```bash
python3 master_cluster_test.py --list
```

## 📊 Các trường hợp test được cover:

### ✅ Đã có trong các file test hiện tại:
- ✅ Basic CRUD operations
- ✅ Replica read-only enforcement
- ✅ Primary failover scenarios
- ✅ Network partition simulation
- ✅ Data consistency verification
- ✅ High load replication
- ✅ API CRUD operations
- ✅ Bulk operations
- ✅ Authentication testing

### 🆕 Đã bổ sung trong file test mới:
- ✅ Connection pooling stress test
- ✅ Replication lag monitoring
- ✅ Long running transaction test
- ✅ Transaction rollback scenarios
- ✅ Schema changes replication (DDL)
- ✅ Memory/CPU stress test
- ✅ Replica promotion simulation
- ✅ Concurrent read/write operations
- ✅ Network latency measurement
- ✅ Bandwidth utilization test
- ✅ Connection pool exhaustion
- ✅ High frequency operations
- ✅ Memory usage under load
- ✅ Network interruption recovery

## 🔧 Prerequisites

### 1. Python dependencies:
```bash
pip install sqlalchemy psycopg2-binary docker requests psutil
```

### 2. Docker containers:
```bash
# Start PostgreSQL cluster
docker-compose up -d postgres-primary postgres-replica
```

### 3. Environment variables:
```bash
# Đảm bảo các biến môi trường được set:
PRIMARY_DATABASE_URL=postgresql://blink_user:12345@postgres-primary:5432/blink_db
REPLICA_DATABASE_URL=postgresql://blink_user:12345@postgres-replica-1:5432/blink_db
```

## 📈 Báo cáo kết quả

### 1. Console output:
- Real-time test progress
- Colored status indicators
- Detailed error messages
- Performance metrics

### 2. JSON reports:
- `comprehensive_cluster_test_report.json`
- `advanced_cluster_test_report.json`
- `network_performance_test_report.json`
- `master_cluster_test_report_YYYYMMDD_HHMMSS.json`

### 3. Test metrics:
- Success/failure rates
- Performance benchmarks
- Latency measurements
- Memory usage statistics
- Network bandwidth utilization

## 🎯 Test Coverage Matrix

| Test Scenario | Simple | Flow | Scenarios | CRUD | Comprehensive | Advanced | Network |
|---------------|--------|------|-----------|------|---------------|----------|---------|
| Basic CRUD | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| Replica Read-Only | ✅ | ✅ | ✅ | - | ✅ | ✅ | - |
| Primary Failover | ✅ | - | ✅ | - | ✅ | ✅ | ✅ |
| Network Partition | - | - | ✅ | - | ✅ | - | ✅ |
| Data Consistency | - | - | - | - | ✅ | - | - |
| High Load | - | - | - | ✅ | ✅ | ✅ | ✅ |
| API Testing | - | - | - | ✅ | - | - | - |
| Connection Pooling | - | - | - | - | - | ✅ | ✅ |
| Replication Lag | - | - | - | - | - | ✅ | ✅ |
| Long Transactions | - | - | - | - | - | ✅ | - |
| Schema Changes | - | - | - | - | - | ✅ | - |
| Memory/CPU Stress | - | - | - | - | - | ✅ | ✅ |
| Network Latency | - | - | - | - | - | - | ✅ |
| Bandwidth Test | - | - | - | - | - | - | ✅ |

## 🚨 Troubleshooting

### 1. Container không chạy:
```bash
docker ps
docker-compose up -d
```

### 2. Connection refused:
- Kiểm tra database URLs
- Đảm bảo containers đang chạy
- Kiểm tra network connectivity

### 3. Test timeout:
- Tăng timeout trong test
- Kiểm tra system resources
- Đảm bảo cluster healthy

### 4. Permission denied:
```bash
chmod +x run_cluster_tests.sh
```

## 📝 Ghi chú

- Tất cả tests đều có error handling
- Tests tự động cleanup data sau khi chạy
- Có thể chạy individual tests hoặc full suite
- Báo cáo chi tiết được lưu dưới dạng JSON
- Support cho cả Windows và Linux/Mac

## 🔄 Cập nhật

Để thêm test cases mới:
1. Tạo file test mới hoặc modify file hiện có
2. Thêm vào `master_cluster_test.py` nếu cần
3. Update documentation này
4. Test thoroughly trước khi deploy

---

**Tác giả**: AI Assistant  
**Ngày tạo**: $(date)  
**Version**: 1.0
