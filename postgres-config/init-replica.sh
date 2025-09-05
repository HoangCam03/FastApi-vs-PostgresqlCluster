#!/bin/bash
set -e

echo "Starting replica initialization..."

# Wait for primary to be ready with better error handling
echo "Waiting for primary database to be ready..."
until pg_isready -h postgres-primary -p 5432 -U blink_user -d blink_db; do
    echo "postgres-primary:5432 - no response, waiting..."
    sleep 5
done

echo "Primary database is ready!"

# Additional wait to ensure primary is fully initialized
echo "Waiting additional time for primary to be fully initialized..."
sleep 15

# Check if replica is already initialized
if [ -f "$PGDATA/standby.signal" ] && [ -f "$PGDATA/postgresql.auto.conf" ]; then
    echo "Replica already initialized"
    exit 0
fi

echo "Initializing replica..."

# Clean up any existing data - CHỈ xóa khi cần thiết
if [ -d "$PGDATA" ] && [ "$(ls -A $PGDATA)" ]; then
    echo "Cleaning existing data directory..."
    rm -rf "$PGDATA"/*
fi

# Create backup from primary using EXISTING replication slot 
echo "Creating backup from primary..."
pg_basebackup -R -D "$PGDATA" -X stream -S replica${REPLICA_NUMBER}_slot -h postgres-primary -U replicator

# Fix ownership
chown -R postgres:postgres "$PGDATA"

echo "Replica initialization complete"

# CRITICAL: For PostgreSQL 13+, create standby.signal file to enable replica mode
if [ ! -f "$PGDATA/standby.signal" ]; then
    echo "Creating standby.signal file for PostgreSQL 13+..."
    touch "$PGDATA/standby.signal"
fi
