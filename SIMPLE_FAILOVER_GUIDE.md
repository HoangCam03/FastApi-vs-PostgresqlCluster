# Hướng dẫn triển khai Simple Failover cho PostgreSQL

## Vấn đề hiện tại
Khi tắt primary database, hệ thống không thể:
- Đăng ký bản ghi mới
- Kết nối với pgAdmin
- Chỉ có thể đăng nhập với dữ liệu có sẵn

## Giải pháp: Simple Failover với HAProxy + Auto-failover Script

### 1. Cấu hình đã được tạo

#### Docker Compose (docker-compose.simple-failover.yml)
- ✅ PostgreSQL Primary với health checks
- ✅ PostgreSQL Replica với health checks  
- ✅ HAProxy với failover configuration
- ✅ FastAPI Backend

#### HAProxy Configuration (haproxy-simple-failover.cfg)
- ✅ Load balancing với failover tự động
- ✅ Health checks cho PostgreSQL nodes
- ✅ Statistics dashboard

#### Auto-failover Script (auto-failover.py)
- ✅ Monitor primary database health
- ✅ Tự động promote replica khi primary down
- ✅ Tự động restore primary khi khôi phục

### 2. Cách triển khai

#### Bước 1: Dừng cluster hiện tại
```bash
docker-compose -f docker-compose.pg_auto_failover.yml down
```

#### Bước 2: Khởi động cluster mới
```bash
docker-compose -f docker-compose.simple-failover.yml up -d
```

#### Bước 3: Kiểm tra trạng thái
```bash
# Kiểm tra containers
docker ps

# Kiểm tra logs
docker logs postgres-primary
docker logs postgres-replica-1
docker logs haproxy
```

#### Bước 4: Chạy auto-failover monitor
```bash
python auto-failover.py
```

### 3. Test failover

#### Test thủ công
1. **Kiểm tra kết nối ban đầu:**
   ```bash
   psql -h localhost -p 5434 -U blink_user -d blink_db
   ```

2. **Tắt primary:**
   ```bash
   docker stop postgres-primary
   ```

3. **Kiểm tra failover (tự động trong 10-30 giây):**
   - Script sẽ tự động detect primary down
   - Tự động promote replica thành primary
   - Update HAProxy configuration

4. **Test kết nối mới:**
   ```bash
   psql -h localhost -p 5434 -U blink_user -d blink_db
   ```

5. **Test write operation:**
   ```sql
   INSERT INTO users (username, email) VALUES ('test_user', 'test@example.com');
   ```

### 4. Monitoring

#### HAProxy Statistics
- **URL:** `http://localhost:5000/stats`
- **Username:** (không cần)
- **Password:** (không cần)

#### Auto-failover Logs
- **File:** `failover.log`
- **Console:** Real-time output

### 5. Cấu hình ứng dụng

Ứng dụng FastAPI đã được cấu hình để sử dụng HAProxy:
```python
# Trong app/database/connection.py
HAPROXY_URL = "postgresql://blink_user:12345@haproxy:5432/blink_db"
```

### 6. Lợi ích của Simple Failover

1. **Tự động failover:** Script monitor và tự động promote replica
2. **Zero downtime:** Ứng dụng tiếp tục hoạt động bình thường
3. **Tự động recovery:** Khi primary khôi phục, tự động restore
4. **Đơn giản:** Dễ hiểu và maintain
5. **Reliable:** Sử dụng HAProxy + health checks

### 7. So sánh các giải pháp

| Giải pháp | Ưu điểm | Nhược điểm | Độ phức tạp |
|-----------|---------|------------|-------------|
| **Simple Failover** | ✅ Đơn giản, dễ hiểu | ⚠️ Cần script monitor | 🟢 Thấp |
| **pg_auto_failover** | ✅ Tự động, chính thức | ⚠️ Phức tạp, nhiều dependencies | 🟡 Trung bình |
| **Patroni** | ✅ Rất mạnh, nhiều tính năng | ⚠️ Rất phức tạp | 🔴 Cao |

### 8. Troubleshooting

#### Nếu failover không hoạt động:
```bash
# Kiểm tra logs
tail -f failover.log

# Kiểm tra HAProxy stats
curl http://localhost:5000/stats

# Kiểm tra container status
docker ps
```

#### Nếu cần restore manual:
```bash
# Stop replica
docker stop postgres-replica-1

# Start primary
docker start postgres-primary

# Restart HAProxy
docker restart haproxy
```

### 9. Kết luận

Với Simple Failover solution:
- ✅ **Đăng ký bản ghi mới sẽ hoạt động** khi primary down
- ✅ **Kết nối pgAdmin sẽ hoạt động** thông qua HAProxy
- ✅ **Zero downtime** cho người dùng
- ✅ **Tự động recovery** khi primary khôi phục
- ✅ **Đơn giản và dễ maintain**

Đây là giải pháp phù hợp cho hầu hết các dự án vừa và nhỏ, đảm bảo high availability mà không quá phức tạp.
