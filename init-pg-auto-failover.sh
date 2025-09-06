#!/bin/bash

echo "🚀 Khởi tạo pg_auto_failover cluster..."

# Chờ monitor khởi động
echo "⏳ Chờ pg_auto_failover monitor khởi động..."
sleep 30

# Kiểm tra trạng thái monitor
echo "🔍 Kiểm tra trạng thái monitor..."
docker exec pg_auto_failover_monitor pg_autoctl show state

# Chờ primary khởi động
echo "⏳ Chờ primary node khởi động..."
sleep 30

# Kiểm tra trạng thái primary
echo "🔍 Kiểm tra trạng thái primary..."
docker exec postgres-primary pg_autoctl show state

# Chờ replica khởi động
echo "⏳ Chờ replica node khởi động..."
sleep 30

# Kiểm tra trạng thái replica
echo "🔍 Kiểm tra trạng thái replica..."
docker exec postgres-replica-1 pg_autoctl show state

# Kiểm tra trạng thái cluster tổng thể
echo "✅ Kiểm tra trạng thái cluster tổng thể..."
docker exec pg_auto_failover_monitor pg_autoctl show state

echo "🎉 pg_auto_failover cluster đã được khởi tạo thành công!"
echo "📊 Monitor stats: http://localhost:5435"
echo "🔍 HAProxy stats: http://localhost:5000/stats"
