#!/usr/bin/env python3
"""
View Cluster Data
Script để xem dữ liệu trong cluster trước và sau khi test
"""

## Tiện ích xem dữ liệu trên Primary, Replica và so sánh record-by-record; có menu tạo dữ liệu mẫu.
##Mục tiêu: Quan sát thực tế đồng bộ dữ liệu giữa Primary/Replica.

import time
from datetime import datetime
from sqlalchemy import text
from app.database.connection import primary_engine, replica_engine

def log(message, level="INFO"):
    """Log với timestamp và màu sắc"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    colors = {
        "PRIMARY": "\033[94m",  # Blue
        "REPLICA": "\033[92m",  # Green
        "INFO": "\033[96m",     # Cyan
        "SUCCESS": "\033[92m",  # Green
        "ERROR": "\033[91m",    # Red
        "WARNING": "\033[93m",  # Yellow
        "RESET": "\033[0m"      # Reset
    }
    color = colors.get(level, colors["INFO"])
    print(f"{color}[{timestamp}] [{level}] {message}{colors['RESET']}")

def view_primary_data():
    """Xem dữ liệu trên PRIMARY"""
    log("\n" + "="*60, "INFO")
    log("📊 PRIMARY DATABASE DATA", "PRIMARY")
    log("="*60, "INFO")
    
    try:
        with primary_engine.connect() as conn:
            # Đếm tổng số records
            count_result = conn.execute(text("SELECT COUNT(*) FROM cluster_test_table")).scalar_one()
            log(f"📈 Total records on PRIMARY: {count_result}", "PRIMARY")
            
            if count_result > 0:
                # Hiển thị tất cả dữ liệu
                result = conn.execute(text("""
                    SELECT 
                        id,
                        name,
                        email,
                        age,
                        status,
                        created_at,
                        updated_at
                    FROM cluster_test_table 
                    ORDER BY id
                """)).fetchall()
                
                log("\n📋 All records on PRIMARY:", "PRIMARY")
                log("-" * 80, "PRIMARY")
                log(f"{'ID':<3} {'Name':<15} {'Email':<25} {'Age':<3} {'Status':<8} {'Created':<19} {'Updated':<19}", "PRIMARY")
                log("-" * 80, "PRIMARY")
                
                for row in result:
                    created_str = row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "N/A"
                    updated_str = row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else "N/A"
                    log(f"{row[0]:<3} {row[1]:<15} {row[2]:<25} {row[3]:<3} {row[4]:<8} {created_str:<19} {updated_str:<19}", "PRIMARY")
                
                # Thống kê
                stats_result = conn.execute(text("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        AVG(age) as avg_age,
                        MIN(age) as min_age,
                        MAX(age) as max_age
                    FROM cluster_test_table 
                    GROUP BY status
                    ORDER BY count DESC
                """)).fetchall()
                
                log("\n📊 Statistics on PRIMARY:", "PRIMARY")
                log("-" * 50, "PRIMARY")
                log(f"{'Status':<10} {'Count':<5} {'Avg Age':<8} {'Min Age':<8} {'Max Age':<8}", "PRIMARY")
                log("-" * 50, "PRIMARY")
                
                for stat in stats_result:
                    log(f"{stat[0]:<10} {stat[1]:<5} {float(stat[2]):<8.1f} {stat[3]:<8} {stat[4]:<8}", "PRIMARY")
            else:
                log("📭 No data found on PRIMARY", "WARNING")
                
    except Exception as e:
        log(f"❌ Error reading PRIMARY data: {str(e)}", "ERROR")

def view_replica_data():
    """Xem dữ liệu trên REPLICA"""
    log("\n" + "="*60, "INFO")
    log("📊 REPLICA DATABASE DATA", "REPLICA")
    log("="*60, "INFO")
    
    try:
        with replica_engine.connect() as conn:
            # Đếm tổng số records
            count_result = conn.execute(text("SELECT COUNT(*) FROM cluster_test_table")).scalar_one()
            log(f"📈 Total records on REPLICA: {count_result}", "REPLICA")
            
            if count_result > 0:
                # Hiển thị tất cả dữ liệu
                result = conn.execute(text("""
                    SELECT 
                        id,
                        name,
                        email,
                        age,
                        status,
                        created_at,
                        updated_at
                    FROM cluster_test_table 
                    ORDER BY id
                """)).fetchall()
                
                log("\n📋 All records on REPLICA:", "REPLICA")
                log("-" * 80, "REPLICA")
                log(f"{'ID':<3} {'Name':<15} {'Email':<25} {'Age':<3} {'Status':<8} {'Created':<19} {'Updated':<19}", "REPLICA")
                log("-" * 80, "REPLICA")
                
                for row in result:
                    created_str = row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else "N/A"
                    updated_str = row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else "N/A"
                    log(f"{row[0]:<3} {row[1]:<15} {row[2]:<25} {row[3]:<3} {row[4]:<8} {created_str:<19} {updated_str:<19}", "REPLICA")
                
                # Thống kê
                stats_result = conn.execute(text("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        AVG(age) as avg_age,
                        MIN(age) as min_age,
                        MAX(age) as max_age
                    FROM cluster_test_table 
                    GROUP BY status
                    ORDER BY count DESC
                """)).fetchall()
                
                log("\n📊 Statistics on REPLICA:", "REPLICA")
                log("-" * 50, "REPLICA")
                log(f"{'Status':<10} {'Count':<5} {'Avg Age':<8} {'Min Age':<8} {'Max Age':<8}", "REPLICA")
                log("-" * 50, "REPLICA")
                
                for stat in stats_result:
                    log(f"{stat[0]:<10} {stat[1]:<5} {float(stat[2]):<8.1f} {stat[3]:<8} {stat[4]:<8}", "REPLICA")
            else:
                log("📭 No data found on REPLICA", "WARNING")
                
    except Exception as e:
        log(f"❌ Error reading REPLICA data: {str(e)}", "ERROR")

def compare_data():
    """So sánh dữ liệu giữa PRIMARY và REPLICA"""
    log("\n" + "="*60, "INFO")
    log("🔍 DATA COMPARISON", "INFO")
    log("="*60, "INFO")
    
    try:
        # Đọc từ PRIMARY
        with primary_engine.connect() as conn:
            primary_data = conn.execute(text("""
                SELECT id, name, email, age, status, created_at, updated_at
                FROM cluster_test_table 
                ORDER BY id
            """)).fetchall()
        
        # Đọc từ REPLICA
        with replica_engine.connect() as conn:
            replica_data = conn.execute(text("""
                SELECT id, name, email, age, status, created_at, updated_at
                FROM cluster_test_table 
                ORDER BY id
            """)).fetchall()
        
        log(f"📊 PRIMARY records: {len(primary_data)}", "PRIMARY")
        log(f"📊 REPLICA records: {len(replica_data)}", "REPLICA")
        
        if primary_data == replica_data:
            log("✅ Data is CONSISTENT between PRIMARY and REPLICA", "SUCCESS")
        else:
            log("❌ Data is INCONSISTENT between PRIMARY and REPLICA", "ERROR")
            
            # Chi tiết sự khác biệt
            log("\n🔍 Differences found:", "ERROR")
            max_len = max(len(primary_data), len(replica_data))
            
            for i in range(max_len):
                p_row = primary_data[i] if i < len(primary_data) else None
                r_row = replica_data[i] if i < len(replica_data) else None
                
                if p_row != r_row:
                    log(f"  Row {i+1}:", "ERROR")
                    log(f"    PRIMARY: {p_row}", "PRIMARY")
                    log(f"    REPLICA: {r_row}", "REPLICA")
    
    except Exception as e:
        log(f"❌ Comparison error: {str(e)}", "ERROR")

def create_sample_data():
    """Tạo dữ liệu mẫu để test"""
    log("\n" + "="*60, "INFO")
    log("🔧 CREATING SAMPLE DATA", "INFO")
    log("="*60, "INFO")
    
    try:
        with primary_engine.begin() as conn:
            # Tạo bảng nếu chưa có
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cluster_test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    age INTEGER,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Xóa dữ liệu cũ
            conn.execute(text("TRUNCATE cluster_test_table RESTART IDENTITY;"))
            
            # Thêm dữ liệu mẫu
            conn.execute(text("""
                INSERT INTO cluster_test_table (name, email, age, status) VALUES 
                ('John Doe', 'john.doe@example.com', 30, 'active'),
                ('Jane Smith', 'jane.smith@example.com', 25, 'active'),
                ('Bob Johnson', 'bob.johnson@example.com', 35, 'inactive'),
                ('Alice Brown', 'alice.brown@example.com', 28, 'active'),
                ('Charlie Wilson', 'charlie.wilson@example.com', 42, 'pending');
            """))
            
            log("✅ Sample data created successfully", "SUCCESS")
            
            # Đợi replication
            log("⏳ Waiting for replication...", "INFO")
            time.sleep(2)
            
    except Exception as e:
        log(f"❌ Error creating sample data: {str(e)}", "ERROR")

def main():
    """Main function"""
    log("🔍 CLUSTER DATA VIEWER", "INFO")
    log("="*60, "INFO")
    
    print("\nChọn chức năng:")
    print("1. Tạo dữ liệu mẫu")
    print("2. Xem dữ liệu PRIMARY")
    print("3. Xem dữ liệu REPLICA")
    print("4. So sánh dữ liệu PRIMARY vs REPLICA")
    print("5. Xem tất cả")
    
    choice = input("\nNhập lựa chọn (1-5): ").strip()
    
    if choice == "1":
        create_sample_data()
    elif choice == "2":
        view_primary_data()
    elif choice == "3":
        view_replica_data()
    elif choice == "4":
        compare_data()
    elif choice == "5":
        create_sample_data()
        view_primary_data()
        view_replica_data()
        compare_data()
    else:
        log("❌ Lựa chọn không hợp lệ", "ERROR")

if __name__ == "__main__":
    main()
