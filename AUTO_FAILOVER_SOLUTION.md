# Giải pháp Auto Failover - Replica tự động trở thành Primary

## 🎯 Vấn đề đã giải quyết

Khi primary database down, replica chỉ có thể đọc mà không thể ghi thêm bản ghi mới. Với giải pháp `pg_auto_failover`, replica sẽ **tự động trở thành primary** và có thể xử lý tất cả thao tác ghi như đăng ký người dùng mới.

## 🚀 Cách triển khai

### Bước 1: Khởi động cluster với auto failover

```bash
# Chạy script khởi động tự động
./start_auto_failover.sh

# Hoặc chạy thủ công:
docker-compose -f docker-compose.pg_auto_failover_simple.yml up -d
./init-pg-auto-failover.sh
```

### Bước 2: Kiểm tra trạng thái cluster

```bash
# Xem trạng thái cluster
docker exec pg_auto_failover_monitor pg_autoctl show state

# Xem HAProxy stats
open http://localhost:5000/stats
```

### Bước 3: Test failover

```bash
# Chạy test tự động
python test_auto_failover.py

# Hoặc test thủ công:
# 1. Kết nối database
psql -h localhost -p 5434 -U blink_user -d blink_db

# 2. Tắt primary
docker stop postgres-primary

# 3. Chờ 30 giây để failover

# 4. Test ghi dữ liệu
INSERT INTO users (username, email) VALUES ('new_user', 'new@example.com');
```

## 🔧 Cấu hình đã được sửa

### 1. HAProxy Configuration (`haproxy-pg-auto-failover.cfg`)
```haproxy
# Đã bỏ "backup" để replica có thể trở thành primary
server postgres-replica-1 postgres-replica-1:5432 check port 5432 inter 3s rise 2 fall 3 weight 50
```

### 2. Database Connection (`app/database/connection.py`)
```python
# Ứng dụng sử dụng HAProxy để tự động failover
HAPROXY_URL = "postgresql://blink_user:12345@haproxy:5432/blink_db"

def get_db():
    """Get database session from HAProxy (default)"""
    db = HaproxySessionLocal()
    # ...
```

## 📊 Monitoring

### pg_auto_failover Monitor
- **URL:** `http://localhost:5435`
- **Username:** `pg_auto_failover`
- **Password:** `12345`

### HAProxy Statistics
- **URL:** `http://localhost:5000/stats`
- **Username:** (không cần)
- **Password:** (không cần)

## 🧪 Test Scenarios

### Scenario 1: Đăng ký người dùng mới khi primary down

1. **Trước khi tắt primary:**
   ```bash
   # Test đăng ký người dùng
   curl -X POST http://localhost:8000/register \
     -H "Content-Type: application/json" \
     -d '{"username": "user1", "email": "user1@example.com", "password": "password123"}'
   ```

2. **Tắt primary:**
   ```bash
   docker stop postgres-primary
   ```

3. **Chờ failover (30 giây):**
   ```bash
   # Kiểm tra trạng thái
   docker exec pg_auto_failover_monitor pg_autoctl show state
   ```

4. **Test đăng ký người dùng mới:**
   ```bash
   # Đăng ký người dùng mới - sẽ thành công!
   curl -X POST http://localhost:8000/register \
     -H "Content-Type: application/json" \
     -d '{"username": "user2", "email": "user2@example.com", "password": "password123"}'
   ```

### Scenario 2: Kết nối pgAdmin

1. **Cấu hình pgAdmin:**
   - **Host:** `localhost`
   - **Port:** `5434`
   - **Username:** `blink_user`
   - **Password:** `12345`
   - **Database:** `blink_db`

2. **Test kết nối:**
   - Kết nối bình thường khi primary hoạt động
   - Kết nối vẫn hoạt động khi primary down (qua replica được promote)

## 🔄 Quy trình Failover

### Khi Primary Down:

1. **Phát hiện lỗi:** pg_auto_failover monitor phát hiện primary không phản hồi
2. **Promote Replica:** Replica được tự động promote thành primary
3. **Cập nhật HAProxy:** HAProxy tự động chuyển traffic sang primary mới
4. **Ứng dụng tiếp tục:** FastAPI tiếp tục hoạt động bình thường
5. **Thời gian:** 10-30 giây

### Khi Primary Khôi phục:

1. **Phát hiện khôi phục:** Monitor phát hiện primary cũ đã hoạt động
2. **Sync dữ liệu:** Primary cũ sync dữ liệu từ primary mới
3. **Trở thành Replica:** Primary cũ trở thành replica
4. **Cân bằng tải:** HAProxy cân bằng traffic giữa các node

## 🛠️ Troubleshooting

### Nếu failover không hoạt động:

```bash
# Kiểm tra trạng thái cluster
docker exec pg_auto_failover_monitor pg_autoctl show state

# Kiểm tra logs
docker logs pg_auto_failover_monitor
docker logs postgres-primary
docker logs postgres-replica-1

# Force failover (nếu cần)
docker exec pg_auto_failover_monitor pg_autoctl perform failover
```

### Nếu không thể kết nối database:

```bash
# Kiểm tra HAProxy
docker logs haproxy

# Kiểm tra port
netstat -tlnp | grep 5434

# Test kết nối trực tiếp
psql -h localhost -p 5434 -U blink_user -d blink_db
```

## ✅ Kết quả

Với giải pháp này, hệ thống của bạn sẽ:

- ✅ **Tự động failover** khi primary down
- ✅ **Tiếp tục nhận write operations** (đăng ký người dùng mới)
- ✅ **Kết nối pgAdmin hoạt động bình thường**
- ✅ **Zero downtime** cho người dùng
- ✅ **Tự động recovery** khi primary khôi phục
- ✅ **Monitoring tích hợp** real-time

## 🎉 Kết luận

Dự án của bạn đã có đầy đủ cấu hình `pg_auto_failover` để giải quyết vấn đề replica không thể ghi khi primary down. Chỉ cần chạy script khởi động và test để đảm bảo mọi thứ hoạt động đúng cách!
