-- Khởi tạo replication cho PostgreSQL cluster
-- Chạy trên primary node

-- Tạo user replicator cho replication
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'replicator') THEN
        CREATE USER replicator WITH REPLICATION PASSWORD '12345';
    END IF;
END
$$;

-- Xóa replication slots cũ nếu tồn tại và tạo mới
DO $$
BEGIN
    -- Xóa slot cũ nếu tồn tại
    IF EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica1_slot') THEN
        SELECT pg_drop_replication_slot('replica1_slot');
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica2_slot') THEN
        SELECT pg_drop_replication_slot('replica2_slot');
    END IF;
    
    -- Tạo replication slot mới cho replica 1
    PERFORM pg_create_physical_replication_slot('replica1_slot', true);
    
    -- Tạo replication slot mới cho replica 2  
    PERFORM pg_create_physical_replication_slot('replica2_slot', true);
END
$$;

-- Cấp quyền cho user blink_user
GRANT ALL PRIVILEGES ON DATABASE blink_db TO blink_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO blink_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO blink_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO blink_user;

-- Tạo extension nếu cần
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


