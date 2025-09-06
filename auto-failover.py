#!/usr/bin/env python3
"""
Auto-failover script for PostgreSQL cluster
Monitors primary database and promotes replica when primary is down
"""

import psycopg2
import time
import subprocess
import logging
from datetime import datetime

# Configuration
PRIMARY_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'blink_db',
    'user': 'blink_user',
    'password': '12345'
}

REPLICA_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'blink_db',
    'user': 'blink_user',
    'password': '12345'
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('failover.log'),
        logging.StreamHandler()
    ]
)

def check_database_health(config):
    """Check if database is healthy"""
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        return False

def promote_replica_to_primary():
    """Promote replica to primary by stopping primary and updating HAProxy config"""
    try:
        logging.info("🔄 Promoting replica to primary...")
        
        # Stop primary container
        subprocess.run(["docker", "stop", "postgres-primary"], check=True)
        logging.info("✅ Primary container stopped")
        
        # Update HAProxy config to route traffic to replica
        haproxy_config = """
global
    daemon
    maxconn 256
    log stdout local0

defaults
    mode tcp
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option tcplog

# HAProxy Statistics
listen stats
    bind *:5000
    mode http
    stats enable
    stats uri /stats
    stats refresh 5s
    stats admin if TRUE

# PostgreSQL Cluster - Replica promoted to primary
listen postgres
    bind *:5432
    mode tcp
    option tcplog
    balance roundrobin
    option tcp-check
    tcp-check connect port 5432
    
    # Replica server (now acting as primary)
    server postgres-replica-1 postgres-replica-1:5432 check port 5432 inter 3s rise 2 fall 3 weight 100

# Health check endpoint
listen health
    bind *:8080
    mode http
    option httpchk GET /health
    http-check expect status 200
"""
        
        with open('haproxy-failover-active.cfg', 'w') as f:
            f.write(haproxy_config)
        
        # Reload HAProxy configuration
        subprocess.run(["docker", "exec", "haproxy", "haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg", "-c"], check=True)
        subprocess.run(["docker", "exec", "haproxy", "haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg", "-sf", "1"], check=True)
        
        logging.info("✅ HAProxy configuration updated")
        logging.info("✅ Failover completed successfully!")
        
        return True
    except Exception as e:
        logging.error(f"❌ Failover failed: {e}")
        return False

def restore_primary():
    """Restore primary database and update HAProxy config"""
    try:
        logging.info("🔄 Restoring primary database...")
        
        # Start primary container
        subprocess.run(["docker", "start", "postgres-primary"], check=True)
        logging.info("✅ Primary container started")
        
        # Wait for primary to be ready
        time.sleep(30)
        
        # Check if primary is healthy
        if check_database_health(PRIMARY_CONFIG):
            # Update HAProxy config back to normal
            haproxy_config = """
global
    daemon
    maxconn 256
    log stdout local0

defaults
    mode tcp
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option tcplog

# HAProxy Statistics
listen stats
    bind *:5000
    mode http
    stats enable
    stats uri /stats
    stats refresh 5s
    stats admin if TRUE

# PostgreSQL Cluster - Normal operation
listen postgres
    bind *:5432
    mode tcp
    option tcplog
    balance roundrobin
    option tcp-check
    tcp-check connect port 5432
    
    # Primary server (restored)
    server postgres-primary postgres-primary:5432 check port 5432 inter 3s rise 2 fall 3 weight 100
    
    # Replica server (backup)
    server postgres-replica-1 postgres-replica-1:5432 check port 5432 inter 3s rise 2 fall 3 weight 50 backup

# Health check endpoint
listen health
    bind *:8080
    mode http
    option httpchk GET /health
    http-check expect status 200
"""
            
            with open('haproxy-failover-active.cfg', 'w') as f:
                f.write(haproxy_config)
            
            # Reload HAProxy configuration
            subprocess.run(["docker", "exec", "haproxy", "haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg", "-c"], check=True)
            subprocess.run(["docker", "exec", "haproxy", "haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg", "-sf", "1"], check=True)
            
            logging.info("✅ Primary restored and HAProxy configuration updated")
            return True
        else:
            logging.error("❌ Primary is not healthy after restart")
            return False
            
    except Exception as e:
        logging.error(f"❌ Primary restoration failed: {e}")
        return False

def main():
    """Main monitoring loop"""
    logging.info("🚀 Starting PostgreSQL auto-failover monitor...")
    
    failover_active = False
    
    while True:
        try:
            # Check primary health
            primary_healthy = check_database_health(PRIMARY_CONFIG)
            
            if not primary_healthy and not failover_active:
                logging.warning("⚠️  Primary database is down!")
                if promote_replica_to_primary():
                    failover_active = True
                    logging.info("🔄 Failover activated - monitoring for primary recovery...")
            elif primary_healthy and failover_active:
                logging.info("✅ Primary database is back online!")
                if restore_primary():
                    failover_active = False
                    logging.info("🔄 Normal operation restored")
            
            # Log status
            status = "FAILOVER ACTIVE" if failover_active else "NORMAL"
            logging.info(f"📊 Status: {status} - Primary: {'✅' if primary_healthy else '❌'}")
            
            # Wait before next check
            time.sleep(10)
            
        except KeyboardInterrupt:
            logging.info("🛑 Monitor stopped by user")
            break
        except Exception as e:
            logging.error(f"❌ Monitor error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
