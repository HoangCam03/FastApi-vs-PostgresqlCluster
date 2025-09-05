-- =====================================================
-- PostgreSQL Cluster Test Queries
-- File để test các trường hợp thêm sửa xóa giữa Primary và Replica

--Chức năng: Bộ câu lệnh SQL thuần để chạy tay.
--Mục tiêu: Tách rõ phần chạy trên Primary (INSERT/UPDATE/DELETE/TRANSACTION/UPSERT/BULK) và phần chạy trên Replica (SELECT/AGGREGATION/PERFORMANCE); có truy vấn kiểm tra replication lag và monitoring.
-- =====================================================

-- 1. TẠO BẢNG TEST
-- =====================================================
CREATE TABLE IF NOT EXISTS cluster_test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    age INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo index để test performance
CREATE INDEX IF NOT EXISTS idx_cluster_test_email ON cluster_test_table(email);
CREATE INDEX IF NOT EXISTS idx_cluster_test_status ON cluster_test_table(status);

-- 2. TEST CASES - CHẠY TRÊN PRIMARY
-- =====================================================

-- Test 1: INSERT - Thêm dữ liệu mới
-- =====================================================
INSERT INTO cluster_test_table (name, email, age, status) VALUES 
('John Doe', 'john.doe@example.com', 30, 'active'),
('Jane Smith', 'jane.smith@example.com', 25, 'active'),
('Bob Johnson', 'bob.johnson@example.com', 35, 'inactive'),
('Alice Brown', 'alice.brown@example.com', 28, 'active'),
('Charlie Wilson', 'charlie.wilson@example.com', 42, 'pending');

-- Test 2: UPDATE - Cập nhật dữ liệu
-- =====================================================
-- Cập nhật thông tin cá nhân
UPDATE cluster_test_table 
SET age = 31, updated_at = CURRENT_TIMESTAMP 
WHERE email = 'john.doe@example.com';

-- Cập nhật trạng thái
UPDATE cluster_test_table 
SET status = 'active', updated_at = CURRENT_TIMESTAMP 
WHERE status = 'pending';

-- Cập nhật hàng loạt
UPDATE cluster_test_table 
SET age = age + 1, updated_at = CURRENT_TIMESTAMP 
WHERE age < 30;

-- Test 3: DELETE - Xóa dữ liệu
-- =====================================================
-- Xóa theo điều kiện
DELETE FROM cluster_test_table 
WHERE status = 'inactive' AND age > 40;

-- Xóa theo ID cụ thể
DELETE FROM cluster_test_table 
WHERE id = 1;

-- Test 4: UPSERT - Thêm hoặc cập nhật
-- =====================================================
INSERT INTO cluster_test_table (name, email, age, status) 
VALUES ('David Lee', 'david.lee@example.com', 33, 'active')
ON CONFLICT (email) 
DO UPDATE SET 
    name = EXCLUDED.name,
    age = EXCLUDED.age,
    status = EXCLUDED.status,
    updated_at = CURRENT_TIMESTAMP;

-- Test 5: BULK OPERATIONS - Thao tác hàng loạt
-- =====================================================
-- Insert nhiều records cùng lúc
INSERT INTO cluster_test_table (name, email, age, status) VALUES 
('Eva Green', 'eva.green@example.com', 29, 'active'),
('Frank Miller', 'frank.miller@example.com', 38, 'active'),
('Grace Taylor', 'grace.taylor@example.com', 26, 'pending'),
('Henry Davis', 'henry.davis@example.com', 45, 'active'),
('Ivy Chen', 'ivy.chen@example.com', 31, 'active');

-- Update hàng loạt
UPDATE cluster_test_table 
SET status = 'verified', updated_at = CURRENT_TIMESTAMP 
WHERE age BETWEEN 25 AND 35;

-- Test 6: TRANSACTION - Giao dịch
-- =====================================================
BEGIN;
    -- Thêm user mới
    INSERT INTO cluster_test_table (name, email, age, status) 
    VALUES ('Transaction User', 'transaction@example.com', 27, 'active');
    
    -- Cập nhật user khác
    UPDATE cluster_test_table 
    SET status = 'updated_in_transaction', updated_at = CURRENT_TIMESTAMP 
    WHERE email = 'jane.smith@example.com';
    
    -- Kiểm tra dữ liệu trước khi commit
    SELECT COUNT(*) as total_records FROM cluster_test_table;
COMMIT;

-- Test 7: COMPLEX QUERIES - Truy vấn phức tạp
-- =====================================================
-- Thống kê theo trạng thái
SELECT 
    status,
    COUNT(*) as count,
    AVG(age) as avg_age,
    MIN(age) as min_age,
    MAX(age) as max_age
FROM cluster_test_table 
GROUP BY status
ORDER BY count DESC;

-- Tìm kiếm với điều kiện phức tạp
SELECT 
    id,
    name,
    email,
    age,
    status,
    created_at,
    updated_at
FROM cluster_test_table 
WHERE 
    (age BETWEEN 25 AND 40) 
    AND (status IN ('active', 'verified'))
    AND (email LIKE '%@example.com')
ORDER BY created_at DESC;

-- 3. TEST CASES - CHẠY TRÊN REPLICA (READ ONLY)
-- =====================================================

-- Test 8: READ OPERATIONS - Đọc dữ liệu từ Replica
-- =====================================================
-- Đọc tất cả dữ liệu
SELECT * FROM cluster_test_table ORDER BY id;

-- Đếm tổng số records
SELECT COUNT(*) as total_records FROM cluster_test_table;

-- Đọc theo điều kiện
SELECT 
    id,
    name,
    email,
    age,
    status
FROM cluster_test_table 
WHERE status = 'active'
ORDER BY name;

-- Test 9: AGGREGATION - Thống kê
-- =====================================================
-- Thống kê tổng quan
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_users,
    COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_users,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_users,
    AVG(age) as average_age,
    MIN(age) as youngest,
    MAX(age) as oldest
FROM cluster_test_table;

-- Thống kê theo nhóm tuổi
SELECT 
    CASE 
        WHEN age < 25 THEN 'Under 25'
        WHEN age BETWEEN 25 AND 35 THEN '25-35'
        WHEN age BETWEEN 36 AND 45 THEN '36-45'
        WHEN age > 45 THEN 'Over 45'
        ELSE 'Unknown'
    END as age_group,
    COUNT(*) as count,
    AVG(age) as avg_age
FROM cluster_test_table 
GROUP BY 
    CASE 
        WHEN age < 25 THEN 'Under 25'
        WHEN age BETWEEN 25 AND 35 THEN '25-35'
        WHEN age BETWEEN 36 AND 45 THEN '36-45'
        WHEN age > 45 THEN 'Over 45'
        ELSE 'Unknown'
    END
ORDER BY count DESC;

-- Test 10: PERFORMANCE QUERIES - Truy vấn hiệu suất
-- =====================================================
-- Tìm kiếm nhanh với index
SELECT * FROM cluster_test_table 
WHERE email = 'jane.smith@example.com';

-- Tìm kiếm theo status (có index)
SELECT * FROM cluster_test_table 
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 10;

-- Pagination
SELECT * FROM cluster_test_table 
ORDER BY id
LIMIT 5 OFFSET 0;

-- 4. TEST CASES - KIỂM TRA REPLICATION
-- =====================================================

-- Test 11: REPLICATION CHECK - Kiểm tra đồng bộ
-- =====================================================
-- Chạy trên PRIMARY trước
INSERT INTO cluster_test_table (name, email, age, status) 
VALUES ('Replication Test', 'replication@example.com', 30, 'active');

-- Sau đó chạy trên REPLICA để kiểm tra
SELECT * FROM cluster_test_table 
WHERE email = 'replication@example.com';

-- Test 12: TIMESTAMP CHECK - Kiểm tra thời gian
-- =====================================================
-- Chạy trên PRIMARY
UPDATE cluster_test_table 
SET updated_at = CURRENT_TIMESTAMP 
WHERE email = 'replication@example.com';

-- Chạy trên REPLICA để xem thời gian cập nhật
SELECT 
    name,
    email,
    created_at,
    updated_at,
    EXTRACT(EPOCH FROM (updated_at - created_at)) as seconds_diff
FROM cluster_test_table 
WHERE email = 'replication@example.com';

-- 5. TEST CASES - ERROR SCENARIOS
-- =====================================================

-- Test 13: CONSTRAINT VIOLATIONS - Vi phạm ràng buộc
-- =====================================================
-- Thử insert email trùng (sẽ lỗi)
-- INSERT INTO cluster_test_table (name, email, age, status) 
-- VALUES ('Duplicate Email', 'jane.smith@example.com', 30, 'active');

-- Test 14: INVALID DATA - Dữ liệu không hợp lệ
-- =====================================================
-- Thử insert age âm (nếu có constraint)
-- INSERT INTO cluster_test_table (name, email, age, status) 
-- VALUES ('Invalid Age', 'invalid@example.com', -5, 'active');

-- 6. CLEANUP - Dọn dẹp dữ liệu test
-- =====================================================
-- Xóa tất cả dữ liệu test (chạy khi cần)
-- TRUNCATE cluster_test_table RESTART IDENTITY;

-- Xóa bảng test (chạy khi cần)
-- DROP TABLE IF EXISTS cluster_test_table;

-- 7. MONITORING QUERIES - Truy vấn giám sát
-- =====================================================

-- Kiểm tra kích thước bảng
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename = 'cluster_test_table';

-- Kiểm tra index usage
SELECT 
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE relname = 'cluster_test_table';

-- Kiểm tra replication lag (chạy trên PRIMARY)
SELECT 
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    write_lag,
    flush_lag,
    replay_lag
FROM pg_stat_replication;

-- =====================================================
-- HƯỚNG DẪN SỬ DỤNG:
-- =====================================================
-- 1. Chạy các query từ 1-7 trên PRIMARY (localhost:5432)
-- 2. Chạy các query từ 8-10 trên REPLICA (localhost:5433)
-- 3. Chạy query 11-12 để kiểm tra replication
-- 4. Chạy query 13-14 để test error handling
-- 5. Chạy query 15-17 để monitoring
-- =====================================================
