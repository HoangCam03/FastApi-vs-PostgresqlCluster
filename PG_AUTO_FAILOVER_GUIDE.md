# Hướng dẫn triển khai pg_auto_failover chính thức

## Vấn đề hiện tại
Khi tắt primary database, hệ thống không thể:
- Đăng ký bản ghi mới
- Kết nối với pgAdmin
- Chỉ có thể đăng nhập với dữ liệu có sẵn

## Giải pháp: pg_auto_failover chính thức của PostgreSQL

### 1. Cấu hình đã được tạo

#### Dockerfile (Dockerfile.pg_auto_failover)
- ✅ Build image PostgreSQL 13 với pg_auto_failover
- ✅ Cài đặt postgresql-13-auto-failover package
- ✅ Tạo user pg_auto_failover

#### Docker Compose (docker-compose.pg_auto_failover.yml)
- ✅ Monitor node với pg_autoctl create monitor
- ✅ Primary node với pg_autoctl create postgres
- ✅ Replica node với pg_autoctl create postgres
- ✅ Tích hợp HAProxy với health checks

#### HAProxy Configuration (haproxy-pg-auto-failover.cfg)
- ✅ Load balancing với failover tự động
- ✅ Health checks cho PostgreSQL nodes
- ✅ Statistics dashboard

### 2. Cách triển khai

#### Bước 1: Dừng cluster hiện tại
```bash
docker-compose -f docker-compose.pg_auto_failover.yml down
```

#### Bước 2: Xóa volumes cũ (nếu cần)
```bash
docker volume rm fastapi_project_postgres_primary_data
docker volume rm fastapi_project_postgres_replica1_data
docker volume rm fastapi_project_pg_auto_failover_data
```

#### Bước 3: Build image pg_auto_failover
```bash
docker build -f Dockerfile.pg_auto_failover -t postgres-pg-auto-failover .
```

#### Bước 4: Khởi động cluster
```bash
docker-compose -f docker-compose.pg_auto_failover.yml up -d
```

#### Bước 5: Khởi tạo pg_auto_failover cluster
```bash
# Chạy script khởi tạo
./init-pg-auto-failover.sh

# Hoặc chạy thủ công:
# Chờ monitor khởi động
sleep 30
docker exec pg_auto_failover_monitor pg_autoctl show state

# Chờ primary khởi động
sleep 30
docker exec postgres-primary pg_autoctl show state

# Chờ replica khởi động
sleep 30
docker exec postgres-replica-1 pg_autoctl show state
```

#### Bước 6: Kiểm tra trạng thái
```bash
# Xem trạng thái cluster
docker exec pg_auto_failover_monitor pg_autoctl show state

# Xem logs
docker logs pg_auto_failover_monitor
docker logs postgres-primary
docker logs postgres-replica-1
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
   ```bash
   # Kiểm tra trạng thái cluster
   docker exec pg_auto_failover_monitor pg_autoctl show state
   
   # Test kết nối mới
   psql -h localhost -p 5434 -U blink_user -d blink_db
   ```

4. **Test write operation:**
   ```sql
   INSERT INTO users (username, email) VALUES ('test_user', 'test@example.com');
   ```

5. **Khôi phục primary:**
   ```bash
   docker start postgres-primary
   # Chờ 30 giây để tự động sync
   ```

### 4. Monitoring

#### pg_auto_failover Monitor
- **URL:** `http://localhost:5435`
- **Username:** `pg_auto_failover`
- **Password:** `12345`

#### HAProxy Statistics
- **URL:** `http://localhost:5000/stats`
- **Username:** (không cần)
- **Password:** (không cần)

### 5. Cấu hình ứng dụng

Ứng dụng FastAPI đã được cấu hình để sử dụng HAProxy:
```python
# Trong app/database/connection.py
HAPROXY_URL = "postgresql://blink_user:12345@haproxy:5432/blink_db"
```

### 6. Lợi ích của pg_auto_failover

1. **Tự động failover:** Khi primary down, replica tự động được promote thành primary
2. **Zero downtime:** Ứng dụng tiếp tục hoạt động bình thường
3. **Tự động recovery:** Khi primary khôi phục, nó tự động trở thành replica
4. **Monitoring tích hợp:** Theo dõi trạng thái cluster real-time
5. **Chính thức:** Tool chính thức từ PostgreSQL team

### 7. Troubleshooting

#### Nếu cluster không khởi tạo được:
```bash
# Kiểm tra logs
docker logs pg_auto_failover_monitor

# Reset cluster
docker exec pg_auto_failover_monitor pg_autoctl drop node --hostname postgres-primary --port 5432
docker exec pg_auto_failover_monitor pg_autoctl drop node --hostname postgres-replica-1 --port 5432
```

#### Nếu failover không hoạt động:
```bash
# Kiểm tra trạng thái
docker exec pg_auto_failover_monitor pg_autoctl show state

# Force failover (nếu cần)
docker exec pg_auto_failover_monitor pg_autoctl perform failover
```

### 8. So sánh với các giải pháp khác

| Giải pháp | Ưu điểm | Nhược điểm | Độ phức tạp |
|-----------|---------|------------|-------------|
| **pg_auto_failover** | ✅ Tự động, chính thức, đơn giản | ⚠️ Cần build image | 🟡 Trung bình |
| **Patroni** | ✅ Rất mạnh, nhiều tính năng | ⚠️ Rất phức tạp | 🔴 Cao |
| **Manual failover** | ✅ Đơn giản | ❌ Không tự động | 🟢 Thấp |

### 9. Kết luận

Với pg_auto_failover chính thức, hệ thống của bạn sẽ:
- ✅ **Tự động failover** khi primary down
- ✅ **Tiếp tục nhận write operations** 
- ✅ **Kết nối pgAdmin hoạt động bình thường**
- ✅ **Zero downtime** cho người dùng
- ✅ **Tool chính thức** từ PostgreSQL team

Đây là giải pháp được khuyến nghị cho PostgreSQL clustering trong production.
