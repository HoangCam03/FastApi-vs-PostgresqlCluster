# PostgreSQL Cluster Query Testing Guide

Hướng dẫn sử dụng các file query để test thêm sửa xóa giữa Primary và Replica.

## 📁 **CÁC FILE ĐÃ TẠO:**

### 1. **`cluster_test_queries.sql`** - File SQL thuần
- Chứa tất cả các query test
- Có thể chạy trực tiếp trên database
- Bao gồm 17 test cases khác nhau

### 2. **`run_cluster_queries.py`** - Script Python tự động
- Chạy các query một cách tự động
- Có logging và màu sắc
- Kiểm tra replication timing
- Test data consistency

## 🚀 **CÁCH SỬ DỤNG:**

### **Cách 1: Chạy Script Python (Khuyến nghị)**
```bash
# Kích hoạt venv
D:\fastapi_project\venv\Scripts\activate.bat

# Chạy script
python run_cluster_queries.py
```

### **Cách 2: Chạy SQL trực tiếp**
```bash
# Kết nối đến PRIMARY
psql -h localhost -p 5432 -U blink_user -d blink_db

# Copy và paste các query từ cluster_test_queries.sql
# Chạy từng section một
```

### **Cách 3: Chạy từng test riêng lẻ**
```python
# Trong Python shell
from run_cluster_queries import *
test_setup()
test_insert_operations()
test_read_operations()
```

## 📋 **CÁC TEST CASES BAO GỒM:**

### **1. Setup & Basic Operations**
- ✅ Tạo bảng test với indexes
- ✅ INSERT dữ liệu mẫu
- ✅ UPDATE dữ liệu
- ✅ DELETE dữ liệu

### **2. Advanced Operations**
- ✅ UPSERT (INSERT ON CONFLICT)
- ✅ BULK OPERATIONS
- ✅ TRANSACTIONS
- ✅ COMPLEX QUERIES

### **3. Replication Testing**
- ✅ READ operations trên REPLICA
- ✅ AGGREGATION queries
- ✅ PERFORMANCE queries
- ✅ REPLICATION TIMING

### **4. Consistency & Error Testing**
- ✅ DATA CONSISTENCY check
- ✅ REPLICA READ-ONLY enforcement
- ✅ CONSTRAINT VIOLATIONS
- ✅ INVALID DATA handling

### **5. Monitoring**
- ✅ Table size monitoring
- ✅ Index usage statistics
- ✅ Replication lag monitoring

## 🔍 **CHI TIẾT CÁC TEST:**

### **Test 1: INSERT Operations**
```sql
-- Thêm dữ liệu mẫu
INSERT INTO cluster_test_table (name, email, age, status) VALUES 
('John Doe', 'john.doe@example.com', 30, 'active'),
('Jane Smith', 'jane.smith@example.com', 25, 'active');
```

### **Test 2: UPDATE Operations**
```sql
-- Cập nhật thông tin
UPDATE cluster_test_table 
SET age = 31, updated_at = CURRENT_TIMESTAMP 
WHERE email = 'john.doe@example.com';
```

### **Test 3: DELETE Operations**
```sql
-- Xóa dữ liệu
DELETE FROM cluster_test_table 
WHERE status = 'inactive' AND age > 40;
```

### **Test 4: READ Operations (REPLICA)**
```sql
-- Đọc từ REPLICA
SELECT * FROM cluster_test_table ORDER BY id;
SELECT COUNT(*) as total_records FROM cluster_test_table;
```

### **Test 5: Replication Timing**
```sql
-- Kiểm tra thời gian replication
SELECT 
    name,
    email,
    created_at,
    updated_at,
    EXTRACT(EPOCH FROM (updated_at - created_at)) as seconds_diff
FROM cluster_test_table;
```

## 📊 **KẾT QUẢ MONG ĐỢI:**

### **Khi chạy thành công:**
```
[10:30:15] [PRIMARY] 🔄 PRIMARY: Insert batch 1
[10:30:15] [SUCCESS]   ✅ PRIMARY: Query executed successfully
[10:30:16] [REPLICA] 🔄 REPLICA: Read query 1
[10:30:16] [SUCCESS]   ✅ REPLICA: 5 rows returned
[10:30:16] [SUCCESS] ✅ Replicated in 0.250s
[10:30:16] [SUCCESS] ✅ Data consistent: 5 records on both PRIMARY and REPLICA
```

### **Khi có lỗi:**
```
[10:30:15] [ERROR]   ❌ REPLICA Error: cannot execute INSERT in a read-only transaction
[10:30:15] [SUCCESS] ✅ REPLICA correctly blocked INSERT: (psycopg2.errors.ReadOnlySqlTransaction)
```

## 🎯 **CÁC TRƯỜNG HỢP ĐƯỢC TEST:**

### **1. Normal Operations**
- ✅ INSERT → PRIMARY → Replication → REPLICA
- ✅ UPDATE → PRIMARY → Replication → REPLICA  
- ✅ DELETE → PRIMARY → Replication → REPLICA
- ✅ SELECT → REPLICA (read-only)

### **2. Error Scenarios**
- ✅ REPLICA blocks INSERT/UPDATE/DELETE
- ✅ Constraint violations
- ✅ Invalid data handling

### **3. Performance Testing**
- ✅ Query execution time
- ✅ Index usage
- ✅ Bulk operations

### **4. Consistency Testing**
- ✅ Data sync between PRIMARY and REPLICA
- ✅ Replication timing
- ✅ Transaction integrity

## 🔧 **TROUBLESHOOTING:**

### **Lỗi kết nối:**
```bash
# Kiểm tra containers
docker ps

# Kiểm tra ports
docker port postgres-primary 5432
docker port postgres-replica-1 5432
```

### **Lỗi replication:**
```bash
# Kiểm tra replication status
psql -h localhost -p 5432 -U blink_user -d blink_db -c "SELECT * FROM pg_stat_replication;"
```

### **Lỗi permissions:**
```bash
# Kiểm tra user permissions
psql -h localhost -p 5432 -U blink_user -d blink_db -c "\du"
```

## 📈 **MONITORING:**

### **Replication Lag:**
```sql
SELECT 
    client_addr,
    state,
    write_lag,
    flush_lag,
    replay_lag
FROM pg_stat_replication;
```

### **Table Statistics:**
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename = 'cluster_test_table';
```

## 🎉 **KẾT LUẬN:**

Với 2 file này, bạn có thể:
- ✅ Test đầy đủ các thao tác CRUD
- ✅ Kiểm tra replication hoạt động
- ✅ Verify data consistency
- ✅ Test performance
- ✅ Monitor cluster health

**Chạy `python run_cluster_queries.py` để bắt đầu test!** 🚀
