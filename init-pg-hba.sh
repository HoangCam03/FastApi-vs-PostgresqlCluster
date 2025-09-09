#!/bin/bash

# Script to automatically configure pg_hba.conf for HAProxy and replication
# This script runs after pg_auto_failover initialization

# Check if already configured
if [ -f "/tmp/pg_hba_configured" ]; then
    echo "✅ pg_hba.conf already configured, skipping..."
    exit 0
fi

echo "🔧 Configuring pg_hba.conf for HAProxy and replication..."

# Wait for pg_auto_failover to initialize
sleep 30

# Function to add pg_hba entries
add_pg_hba_entries() {
    local pgdata_path=$1
    local pg_hba_file="$pgdata_path/pg_hba.conf"
    
    if [ -f "$pg_hba_file" ]; then
        echo "📝 Adding HAProxy and replication entries to $pg_hba_file"
        
        # Add HAProxy network access (if not already present)
        if ! grep -q "host all all 172.18.0.0/16 trust" "$pg_hba_file"; then
            echo "host all all 172.18.0.0/16 trust" >> "$pg_hba_file"
        fi
        
        # Add replication access for pgautofailover_replicator (if not already present)
        if ! grep -q "host replication pgautofailover_replicator 172.18.0.0/16 trust" "$pg_hba_file"; then
            echo "host replication pgautofailover_replicator 172.18.0.0/16 trust" >> "$pg_hba_file"
        fi
        
        # Reload configuration
        echo "🔄 Reloading PostgreSQL configuration..."
        psql -U postgres -c 'SELECT pg_reload_conf();' 2>/dev/null || true
        
        # Mark as configured
        touch /tmp/pg_hba_configured
        
        echo "✅ pg_hba.conf configured successfully"
    else
        echo "⚠️ pg_hba.conf not found at $pg_hba_file"
    fi
}

# Configure for replica (uses /var/lib/postgresql/data/pgdata)
if [ -d "/var/lib/postgresql/data/pgdata" ]; then
    add_pg_hba_entries "/var/lib/postgresql/data/pgdata"
fi

# Configure for primary (uses /var/lib/postgresql/data)
if [ -d "/var/lib/postgresql/data" ] && [ ! -d "/var/lib/postgresql/data/pgdata" ]; then
    add_pg_hba_entries "/var/lib/postgresql/data"
fi

echo "🎉 pg_hba.conf configuration completed!"
