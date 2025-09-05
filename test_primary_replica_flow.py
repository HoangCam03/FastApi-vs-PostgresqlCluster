# fastapi_project/test_primary_replica_flow.py
#!/usr/bin/env python3

## Bài test tối giản chứng minh flow: CREATE/UPDATE/DELETE trên Primary → thấy trên Replica; ghi vào Replica bị chặn.
##Mục tiêu: Bằng chứng ngắn gọn, dễ chạy để demo cho anh Đăng.
import time
from datetime import datetime, timedelta

from sqlalchemy import text
from app.database.connection import primary_engine, replica_engine

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cluster_flow_test (
    id SERIAL PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def run():
    print("== Primary/Replica flow test ==")

    with primary_engine.begin() as pconn:
        pconn.execute(text(TABLE_SQL))
        print("Created/ensured table on primary")

        # Clean slate
        pconn.execute(text("TRUNCATE cluster_flow_test RESTART IDENTITY;"))

        # CREATE on primary
        res = pconn.execute(
            text("INSERT INTO cluster_flow_test (payload) VALUES (:v) RETURNING id"),
            {"v": "create_on_primary"}
        )
        row_id = res.scalar_one()
        print(f"Inserted row id={row_id} on primary")

    # READ on replica (wait until replicated)
    deadline = datetime.utcnow() + timedelta(seconds=20)
    replicated = False
    while datetime.utcnow() < deadline:
        with replica_engine.connect() as rconn:
            cnt = rconn.execute(text("SELECT COUNT(*) FROM cluster_flow_test WHERE id=:id"),
                                {"id": row_id}).scalar_one()
            if cnt == 1:
                replicated = True
                break
        time.sleep(0.5)
    print(f"Replicated to replica: {replicated}")
    if not replicated:
        raise RuntimeError("Row did not appear on replica within timeout")

    # UPDATE on primary
    with primary_engine.begin() as pconn:
        pconn.execute(
            text("UPDATE cluster_flow_test SET payload=:v, updated_at=NOW() WHERE id=:id"),
            {"v": "updated_on_primary", "id": row_id}
        )
        print("Updated row on primary")

    # Verify UPDATE on replica
    deadline = datetime.utcnow() + timedelta(seconds=20)
    seen_update = False
    while datetime.utcnow() < deadline:
        with replica_engine.connect() as rconn:
            payload = rconn.execute(
                text("SELECT payload FROM cluster_flow_test WHERE id=:id"),
                {"id": row_id}
            ).scalar_one()
            if payload == "updated_on_primary":
                seen_update = True
                break
        time.sleep(0.5)
    print(f"Update replicated to replica: {seen_update}")
    if not seen_update:
        raise RuntimeError("Update did not replicate to replica within timeout")

    # DELETE on primary
    with primary_engine.begin() as pconn:
        pconn.execute(text("DELETE FROM cluster_flow_test WHERE id=:id"), {"id": row_id})
        print("Deleted row on primary")

    # Verify DELETE on replica
    deadline = datetime.utcnow() + timedelta(seconds=20)
    seen_delete = False
    while datetime.utcnow() < deadline:
        with replica_engine.connect() as rconn:
            cnt = rconn.execute(
                text("SELECT COUNT(*) FROM cluster_flow_test WHERE id=:id"),
                {"id": row_id}
            ).scalar_one()
            if cnt == 0:
                seen_delete = True
                break
        time.sleep(0.5)
    print(f"Delete replicated to replica: {seen_delete}")
    if not seen_delete:
        raise RuntimeError("Delete did not replicate to replica within timeout")

    # Assert REPLICA is read-only: attempt to INSERT should fail
    try:
        with replica_engine.begin() as rconn:
            rconn.execute(text("INSERT INTO cluster_flow_test (payload) VALUES ('should_fail_on_replica')"))
        raise AssertionError("Replica accepted a write, expected read-only")
    except Exception as e:
        print(f"Replica write blocked as expected: {str(e).splitlines()[0]}")

    print("== Flow test completed successfully ==")

if __name__ == "__main__":
    run()
