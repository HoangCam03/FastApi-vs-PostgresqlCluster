#!/usr/bin/env python3
"""
Script test đơn giản cho auto failover
"""

import psycopg2
import time
import subprocess
from datetime import datetime

def test_connection():
    """Test kết nối database"""
    try:
        conn = psycopg2.connect("postgresql://blink_user:12345@localhost:5434/blink_db")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Kết nối database thành công: {version}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        return False

def test_write():
    """Test ghi dữ liệu"""
    try:
        conn = psycopg2.connect("postgresql://blink_user:12345@localhost:5434/blink_db")
        cursor = conn.cursor()
        
        # Tạo bảng test
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_failover (
                id SERIAL PRIMARY KEY,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Thêm dữ liệu test
        test_message = f"Test failover at {datetime.now()}"
        cursor.execute("""
            INSERT INTO test_failover (message) 
            VALUES (%s) 
            RETURNING id, message, created_at;
        """, (test_message,))
        
        result = cursor.fetchone()
        print(f"✅ Ghi dữ liệu thành công: ID={result[0]}, Message={result[1]}")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Lỗi ghi dữ liệu: {e}")
        return False

def get_cluster_status():
    """Lấy trạng thái cluster"""
    try:
        result = subprocess.run([
            "docker", "exec", "pg_auto_failover_monitor", 
            "pg_autoctl", "show", "state"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("📊 Trạng thái cluster:")
            print(result.stdout)
            return True
        else:
            print(f"❌ Lỗi lấy trạng thái cluster: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Lỗi chạy lệnh cluster status: {e}")
        return False

def main():
    print("🧪 Test Auto Failover đơn giản")
    print("=" * 40)
    
    # Test 1: Kết nối database
    print("\n1️⃣ Test kết nối database:")
    if not test_connection():
        print("❌ Không thể kết nối database. Vui lòng kiểm tra cluster.")
        return
    
    # Test 2: Ghi dữ liệu
    print("\n2️⃣ Test ghi dữ liệu:")
    if not test_write():
        print("❌ Không thể ghi dữ liệu. Vui lòng kiểm tra cluster.")
        return
    
    # Test 3: Trạng thái cluster
    print("\n3️⃣ Trạng thái cluster:")
    get_cluster_status()
    
    print("\n✅ Test cơ bản thành công!")
    print("🎯 Bây giờ bạn có thể:")
    print("   - Mở pgAdmin và kết nối với localhost:5434")
    print("   - Đăng ký người dùng mới ở giao diện")
    print("   - Kiểm tra dữ liệu trong pgAdmin")

if __name__ == "__main__":
    main()
