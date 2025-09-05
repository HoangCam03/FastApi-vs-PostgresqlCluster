#!/bin/bash

# Wait for primary to be ready
echo "Waiting for primary database to be ready..."
sleep 30

# Setup replication for replica 1
echo "Setting up replication for replica 1..."
docker exec postgres-replica-1 pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U blink_user -v -P -W

# Setup replication for replica 2
echo "Setting up replication for replica 2..."
docker exec postgres-replica-2 pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U blink_user -v -P -W

echo "Replication setup completed!"
