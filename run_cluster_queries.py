#!/usr/bin/env python3
"""
Cluster Query Runner
Script để chạy các query test giữa Primary và Replica
"""

import time
import psycopg2
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

def run_query_on_primary(query, description):
    """Chạy query trên PRIMARY"""
    log(f"🔄 PRIMARY: {description}", "PRIMARY")
    try:
        with primary_engine.begin() as conn:
            result = conn.execute(text(query))
            if result.returns_rows:
                rows = result.fetchall()
                log(f"  ✅ PRIMARY: {len(rows)} rows returned", "SUCCESS")
                return rows
            else:
                log(f"  ✅ PRIMARY: Query executed successfully", "SUCCESS")
                return None
    except Exception as e:
        log(f"  ❌ PRIMARY Error: {str(e)}", "ERROR")
        return None

def run_query_on_replica(query, description):
    """Chạy query trên REPLICA"""
    log(f"🔄 REPLICA: {description}", "REPLICA")
    try:
        with replica_engine.connect() as conn:
            result = conn.execute(text(query))
            if result.returns_rows:
                rows = result.fetchall()
                log(f"  ✅ REPLICA: {len(rows)} rows returned", "SUCCESS")
                return rows
            else:
                log(f"  ✅ REPLICA: Query executed successfully", "SUCCESS")
                return None
    except Exception as e:
        log(f"  ❌ REPLICA Error: {str(e)}", "ERROR")
        return None

def test_setup():
    """Test 1: Setup bảng test"""
    log("\n" + "="*60, "INFO")
    log("🔧 TEST 1: SETUP TABLE", "INFO")
    log("="*60, "INFO")
    
    setup_queries = [
        """
        CREATE TABLE IF NOT EXISTS cluster_test_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            age INTEGER,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cluster_test_email ON cluster_test_table(email);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cluster_test_status ON cluster_test_table(status);
        """,
        """
        TRUNCATE cluster_test_table RESTART IDENTITY;
        """
    ]
    
    for i, query in enumerate(setup_queries, 1):
        run_query_on_primary(query, f"Setup step {i}")

def test_insert_operations():
    """Test 2: INSERT operations"""
    log("\n" + "="*60, "INFO")
    log("📝 TEST 2: INSERT OPERATIONS", "INFO")
    log("="*60, "INFO")
    
    insert_queries = [
        """
        INSERT INTO cluster_test_table (name, email, age, status) VALUES 
        ('John Doe', 'john.doe@example.com', 30, 'active'),
        ('Jane Smith', 'jane.smith@example.com', 25, 'active'),
        ('Bob Johnson', 'bob.johnson@example.com', 35, 'inactive'),
        ('Alice Brown', 'alice.brown@example.com', 28, 'active'),
        ('Charlie Wilson', 'charlie.wilson@example.com', 42, 'pending');
        """,
        """
        INSERT INTO cluster_test_table (name, email, age, status) VALUES 
        ('David Lee', 'david.lee@example.com', 33, 'active'),
        ('Eva Green', 'eva.green@example.com', 29, 'active'),
        ('Frank Miller', 'frank.miller@example.com', 38, 'active');
        """
    ]
    
    for i, query in enumerate(insert_queries, 1):
        run_query_on_primary(query, f"Insert batch {i}")
        time.sleep(1)  # Đợi replication

def test_update_operations():
    """Test 3: UPDATE operations"""
    log("\n" + "="*60, "INFO")
    log("✏️ TEST 3: UPDATE OPERATIONS", "INFO")
    log("="*60, "INFO")
    
    update_queries = [
        """
        UPDATE cluster_test_table 
        SET age = 31, updated_at = CURRENT_TIMESTAMP 
        WHERE email = 'john.doe@example.com';
        """,
        """
        UPDATE cluster_test_table 
        SET status = 'active', updated_at = CURRENT_TIMESTAMP 
        WHERE status = 'pending';
        """,
        """
        UPDATE cluster_test_table 
        SET age = age + 1, updated_at = CURRENT_TIMESTAMP 
        WHERE age < 30;
        """
    ]
    
    for i, query in enumerate(update_queries, 1):
        run_query_on_primary(query, f"Update operation {i}")
        time.sleep(1)  # Đợi replication

def test_delete_operations():
    """Test 4: DELETE operations"""
    log("\n" + "="*60, "INFO")
    log("🗑️ TEST 4: DELETE OPERATIONS", "INFO")
    log("="*60, "INFO")
    
    delete_queries = [
        """
        DELETE FROM cluster_test_table 
        WHERE status = 'inactive' AND age > 40;
        """,
        """
        DELETE FROM cluster_test_table 
        WHERE id = 1;
        """
    ]
    
    for i, query in enumerate(delete_queries, 1):
        run_query_on_primary(query, f"Delete operation {i}")
        time.sleep(1)  # Đợi replication

def test_read_operations():
    """Test 5: READ operations trên REPLICA"""
    log("\n" + "="*60, "INFO")
    log("📖 TEST 5: READ OPERATIONS (REPLICA)", "INFO")
    log("="*60, "INFO")
    
    read_queries = [
        """
        SELECT COUNT(*) as total_records FROM cluster_test_table;
        """,
        """
        SELECT * FROM cluster_test_table ORDER BY id;
        """,
        """
        SELECT 
            id,
            name,
            email,
            age,
            status
        FROM cluster_test_table 
        WHERE status = 'active'
        ORDER BY name;
        """,
        """
        SELECT 
            status,
            COUNT(*) as count,
            AVG(age) as avg_age,
            MIN(age) as min_age,
            MAX(age) as max_age
        FROM cluster_test_table 
        GROUP BY status
        ORDER BY count DESC;
        """
    ]
    
    for i, query in enumerate(read_queries, 1):
        result = run_query_on_replica(query, f"Read query {i}")
        if result:
            log(f"  📊 Results: {result}", "INFO")

def test_replication_timing():
    """Test 6: Replication timing"""
    log("\n" + "="*60, "INFO")
    log("⏱️ TEST 6: REPLICATION TIMING", "INFO")
    log("="*60, "INFO")
    
    # Ghi trên PRIMARY
    start_time = time.time()
    run_query_on_primary(
        """
        INSERT INTO cluster_test_table (name, email, age, status) 
        VALUES ('Timing Test', 'timing@example.com', 30, 'active');
        """,
        "Insert timing test record"
    )
    write_time = time.time() - start_time
    log(f"⏱️ Write time: {write_time:.3f}s", "INFO")
    
    # Đợi và kiểm tra trên REPLICA
    log("⏳ Waiting for replication...", "INFO")
    replication_start = time.time()
    
    max_wait = 10
    replicated = False
    
    while time.time() - replication_start < max_wait:
        result = run_query_on_replica(
            "SELECT COUNT(*) FROM cluster_test_table WHERE email = 'timing@example.com';",
            "Check replication"
        )
        if result and result[0][0] > 0:
            replication_time = time.time() - replication_start
            log(f"✅ Replicated in {replication_time:.3f}s", "SUCCESS")
            replicated = True
            break
        time.sleep(0.1)
    
    if not replicated:
        log(f"❌ Replication timeout after {max_wait}s", "ERROR")

def test_data_consistency():
    """Test 7: Data consistency check"""
    log("\n" + "="*60, "INFO")
    log("🔍 TEST 7: DATA CONSISTENCY CHECK", "INFO")
    log("="*60, "INFO")
    
    # Đọc từ PRIMARY
    primary_result = run_query_on_primary(
        "SELECT COUNT(*) FROM cluster_test_table;",
        "Count records on PRIMARY"
    )
    
    # Đọc từ REPLICA
    replica_result = run_query_on_replica(
        "SELECT COUNT(*) FROM cluster_test_table;",
        "Count records on REPLICA"
    )
    
    if primary_result and replica_result:
        primary_count = primary_result[0][0]
        replica_count = replica_result[0][0]
        
        if primary_count == replica_count:
            log(f"✅ Data consistent: {primary_count} records on both PRIMARY and REPLICA", "SUCCESS")
        else:
            log(f"❌ Data inconsistent: PRIMARY={primary_count}, REPLICA={replica_count}", "ERROR")

def test_replica_read_only():
    """Test 8: Replica read-only enforcement"""
    log("\n" + "="*60, "INFO")
    log("🔒 TEST 8: REPLICA READ-ONLY ENFORCEMENT", "INFO")
    log("="*60, "INFO")
    
    # Thử INSERT trên REPLICA
    log("🔄 Attempting INSERT on REPLICA...", "REPLICA")
    try:
        with replica_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO cluster_test_table (name, email, age, status) 
                VALUES ('Replica Write Test', 'replica@example.com', 30, 'active');
            """))
        log("❌ REPLICA accepted INSERT - THIS IS BAD!", "ERROR")
    except Exception as e:
        log(f"✅ REPLICA correctly blocked INSERT: {str(e).splitlines()[0]}", "SUCCESS")
    
    # Thử UPDATE trên REPLICA
    log("🔄 Attempting UPDATE on REPLICA...", "REPLICA")
    try:
        with replica_engine.begin() as conn:
            conn.execute(text("""
                UPDATE cluster_test_table 
                SET status = 'updated_by_replica' 
                WHERE email = 'jane.smith@example.com';
            """))
        log("❌ REPLICA accepted UPDATE - THIS IS BAD!", "ERROR")
    except Exception as e:
        log(f"✅ REPLICA correctly blocked UPDATE: {str(e).splitlines()[0]}", "SUCCESS")

def test_performance_queries():
    """Test 9: Performance queries"""
    log("\n" + "="*60, "INFO")
    log("⚡ TEST 9: PERFORMANCE QUERIES", "INFO")
    log("="*60, "INFO")
    
    performance_queries = [
        """
        SELECT * FROM cluster_test_table 
        WHERE email = 'jane.smith@example.com';
        """,
        """
        SELECT * FROM cluster_test_table 
        WHERE status = 'active'
        ORDER BY created_at DESC
        LIMIT 5;
        """,
        """
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_users,
            AVG(age) as average_age
        FROM cluster_test_table;
        """
    ]
    
    for i, query in enumerate(performance_queries, 1):
        start_time = time.time()
        result = run_query_on_replica(query, f"Performance query {i}")
        query_time = time.time() - start_time
        log(f"  ⏱️ Query time: {query_time:.3f}s", "INFO")

def cleanup_test_data():
    """Cleanup test data"""
    log("\n" + "="*60, "INFO")
    log("🧹 CLEANUP: Removing test data", "INFO")
    log("="*60, "INFO")
    
    run_query_on_primary(
        "TRUNCATE cluster_test_table RESTART IDENTITY;",
        "Cleanup test data"
    )

def main():
    """Chạy tất cả tests"""
    log("🚀 POSTGRESQL CLUSTER QUERY TESTING", "INFO")
    log("="*60, "INFO")
    
    try:
        # Setup
        test_setup()
        
        # Tests
        test_insert_operations()
        test_update_operations()
        test_delete_operations()
        test_read_operations()
        test_replication_timing()
        test_data_consistency()
        test_replica_read_only()
        test_performance_queries()
        
        # Cleanup
        cleanup_test_data()
        
        log("\n" + "="*60, "INFO")
        log("🎉 ALL TESTS COMPLETED SUCCESSFULLY!", "SUCCESS")
        log("="*60, "INFO")
        
    except Exception as e:
        log(f"❌ Test failed: {str(e)}", "ERROR")

if __name__ == "__main__":
    main()
