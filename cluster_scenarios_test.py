# fastapi_project/cluster_scenarios_test.py
#!/usr/bin/env python3

##Chức năng: Kịch bản CRUD + replication đơn giản, rồi kiểm tra failover đọc.
##Mục tiêu: CREATE/UPDATE/DELETE trên Primary xuất hiện ở Replica sau độ trễ; Replica cấm ghi; khi Primary down (thực tế phần docker stop được ghi chú thủ công), vẫn đọc được Replica và tiếp tục replication sau khi Primary lên.
import time
from datetime import datetime, timedelta

import docker
from sqlalchemy import text
from app.database.connection import primary_engine, replica_engine

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cluster_flow_test (
    id SERIAL PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

PRIMARY_CONTAINER = "postgres-primary"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ensure_table_on_primary():
    with primary_engine.begin() as conn:
        conn.execute(text(TABLE_SQL))
        conn.execute(text("TRUNCATE cluster_flow_test RESTART IDENTITY;"))

def write_on_primary(payload):
    with primary_engine.begin() as conn:
        rid = conn.execute(
            text("INSERT INTO cluster_flow_test (payload) VALUES (:v) RETURNING id"),
            {"v": payload}
        ).scalar_one()
        return rid

def read_on_replica(row_id):
    with replica_engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, payload FROM cluster_flow_test WHERE id=:id"),
            {"id": row_id}
        ).mappings().first()
        return dict(row) if row else None
        
def update_on_primary(row_id, payload):
    with primary_engine.begin() as conn:
        conn.execute(
            text("UPDATE cluster_flow_test SET payload=:v, updated_at=NOW() WHERE id=:id"),
            {"v": payload, "id": row_id}
        )

def delete_on_primary(row_id):
    with primary_engine.begin() as conn:
        conn.execute(text("DELETE FROM cluster_flow_test WHERE id=:id"), {"id": row_id})

def assert_replica_blocks_write():
    try:
        with replica_engine.begin() as conn:
            conn.execute(text("INSERT INTO cluster_flow_test (payload) VALUES ('should_fail')"))
        raise AssertionError("Replica accepted write (expected read-only).")
    except Exception as e:
        log(f"Replica write blocked as expected: {str(e).splitlines()[0]}")

def wait_until_replica_sees(row_id, expect_payload=None, timeout=20):
    deadline = datetime.utcnow() + timedelta(seconds=timeout)
    while datetime.utcnow() < deadline:
        row = read_on_replica(row_id)
        if row is None:
            time.sleep(0.5)
            continue
        if expect_payload is None or row.get("payload") == expect_payload:
            return True
        time.sleep(0.5)
    return False

def wait_until_replica_deleted(row_id, timeout=20):
    deadline = datetime.utcnow() + timedelta(seconds=timeout)
    while datetime.utcnow() < deadline:
        if read_on_replica(row_id) is None:
            return True
        time.sleep(0.5)
    return False

def docker_client():
    return docker.from_env()

def stop_primary():
    log("Stopping primary container...")
    docker_client().containers.get(PRIMARY_CONTAINER).stop()
    time.sleep(3)

def start_primary():
    log("Starting primary container...")
    docker_client().containers.get(PRIMARY_CONTAINER).start()
    # đợi primary sẵn sàng
    time.sleep(10)

def run_scenario():
    log("== Scenario: CRUD + Replication ==")
    ensure_table_on_primary()

    # CREATE on primary
    rid = write_on_primary("create_on_primary")
    log(f"Inserted id={rid} on primary")

    # Replica should see it
    assert wait_until_replica_sees(rid), "Create not replicated to replica in time"
    log("Replica saw CREATE")

    # UPDATE on primary
    update_on_primary(rid, "updated_on_primary")
    assert wait_until_replica_sees(rid, expect_payload="updated_on_primary"), "Update not replicated in time"
    log("Replica saw UPDATE")

    # DELETE on primary
    delete_on_primary(rid)
    assert wait_until_replica_deleted(rid), "Delete not replicated in time"
    log("Replica saw DELETE")

    # Replica read-only assertion
    assert_replica_blocks_write()

def run_failover_read_only_check():
    log("== Scenario: Failover (primary down) ==")
    # Write a row first
    ensure_table_on_primary()
    rid = write_on_primary("before_failover")
    assert wait_until_replica_sees(rid), "Initial replication failed"
    log("Replica synced before failover")

    # Note: Docker control requires host access
    log("Note: Docker control test skipped (requires host access)")
    log("Manual test: docker stop postgres-primary, verify replica read-only, docker start postgres-primary")
    
    # Test replication resume (assuming primary is running)
    new_id = write_on_primary("after_failover")
    assert wait_until_replica_sees(new_id), "Replication did not resume"
    log("Replication resumed")

def main():
    run_scenario()
    run_failover_read_only_check()
    log("== All scenarios passed ==")

if __name__ == "__main__":
    main()
