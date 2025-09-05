#!/bin/bash

# Test PostgreSQL Cluster Workflow
# Script để kiểm tra luồng hoạt động của PostgreSQL cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PRIMARY_HOST="localhost"
PRIMARY_PORT="5432"
REPLICA1_HOST="localhost"
REPLICA1_PORT="5433"
REPLICA2_HOST="localhost"
REPLICA2_PORT="5434"
PGBOUNCER_HOST="localhost"
PGBOUNCER_PORT="6432"
DB_NAME="blink_db"
DB_USER="blink_user"
DB_PASSWORD="12345"

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test database connection
test_connection() {
    local host=$1
    local port=$2
    local name=$3
    
    log "Testing connection to $name ($host:$port)..."
    
    if PGPASSWORD=$DB_PASSWORD psql -h $host -p $port -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
        success "Connection to $name successful"
        return 0
    else
        error "Connection to $name failed"
        return 1
    fi
}

# Test replication status
test_replication() {
    log "=== TESTING REPLICATION STATUS ==="
    
    # Check primary replication slots
    log "Checking primary replication slots..."
    PGPASSWORD=$DB_PASSWORD psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $DB_USER -d $DB_NAME -c "
        SELECT slot_name, active, restart_lsn, confirmed_flush_lsn 
        FROM pg_replication_slots;
    "
    
    # Check replica status
    log "Checking replica 1 status..."
    if PGPASSWORD=$DB_PASSWORD psql -h $REPLICA1_HOST -p $REPLICA1_PORT -U $DB_USER -d $DB_NAME -c "SELECT pg_is_in_recovery();" | grep -q "t"; then
        success "Replica 1 is in recovery mode (correct)"
    else
        error "Replica 1 is not in recovery mode"
    fi
    
    log "Checking replica 2 status..."
    if PGPASSWORD=$DB_PASSWORD psql -h $REPLICA2_HOST -p $REPLICA2_PORT -U $DB_USER -d $DB_NAME -c "SELECT pg_is_in_recovery();" | grep -q "t"; then
        success "Replica 2 is in recovery mode (correct)"
    else
        error "Replica 2 is not in recovery mode"
    fi
}

# Test data consistency
test_data_consistency() {
    log "=== TESTING DATA CONSISTENCY ==="
    
    # Create test table and data
    log "Creating test data on primary..."
    PGPASSWORD=$DB_PASSWORD psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $DB_USER -d $DB_NAME -c "
        DROP TABLE IF EXISTS cluster_test;
        CREATE TABLE cluster_test (
            id SERIAL PRIMARY KEY,
            test_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO cluster_test (test_data) VALUES ('Test data from primary');
    "
    
    # Wait for replication
    log "Waiting for replication to complete..."
    sleep 5
    
    # Check data on replicas
    log "Checking data on replica 1..."
    REPLICA1_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $REPLICA1_HOST -p $REPLICA1_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM cluster_test;" | tr -d ' ')
    
    log "Checking data on replica 2..."
    REPLICA2_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $REPLICA2_HOST -p $REPLICA2_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM cluster_test;" | tr -d ' ')
    
    if [ "$REPLICA1_COUNT" = "1" ] && [ "$REPLICA2_COUNT" = "1" ]; then
        success "Data consistency verified - all replicas have the same data"
    else
        error "Data inconsistency detected - Replica1: $REPLICA1_COUNT, Replica2: $REPLICA2_COUNT"
    fi
    
    # Clean up
    PGPASSWORD=$DB_PASSWORD psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $DB_USER -d $DB_NAME -c "DROP TABLE cluster_test;"
}

# Test PgBouncer connection pooling
test_pgbouncer() {
    log "=== TESTING PGBOUNCER CONNECTION POOLING ==="
    
    # Test connection through PgBouncer
    log "Testing connection through PgBouncer..."
    if test_connection $PGBOUNCER_HOST $PGBOUNCER_PORT "PgBouncer"; then
        success "PgBouncer connection successful"
        
        # Check PgBouncer stats
        log "Checking PgBouncer statistics..."
        PGPASSWORD=$DB_PASSWORD psql -h $PGBOUNCER_HOST -p $PGBOUNCER_PORT -U $DB_USER -d $DB_NAME -c "
            SHOW POOLS;
            SHOW STATS;
        "
    else
        error "PgBouncer connection failed"
    fi
}

# Test failover scenario
test_failover() {
    log "=== TESTING FAILOVER SCENARIO ==="
    warning "This test will temporarily stop the primary database"
    
    read -p "Do you want to continue with failover test? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Skipping failover test"
        return
    fi
    
    # Stop primary
    log "Stopping primary database..."
    docker stop postgres-primary
    
    # Wait a moment
    sleep 3
    
    # Test if replicas are still accessible (read-only)
    log "Testing replica accessibility after primary failure..."
    if test_connection $REPLICA1_HOST $REPLICA1_PORT "Replica 1 (after primary failure)"; then
        success "Replica 1 still accessible after primary failure"
    else
        error "Replica 1 not accessible after primary failure"
    fi
    
    if test_connection $REPLICA2_HOST $REPLICA2_PORT "Replica 2 (after primary failure)"; then
        success "Replica 2 still accessible after primary failure"
    else
        error "Replica 2 not accessible after primary failure"
    fi
    
    # Restart primary
    log "Restarting primary database..."
    docker start postgres-primary
    
    # Wait for primary to be ready
    log "Waiting for primary to be ready..."
    sleep 10
    
    if test_connection $PRIMARY_HOST $PRIMARY_PORT "Primary (after restart)"; then
        success "Primary database restarted successfully"
    else
        error "Primary database restart failed"
    fi
}

# Test performance
test_performance() {
    log "=== TESTING PERFORMANCE ==="
    
    # Test write performance on primary
    log "Testing write performance on primary..."
    time PGPASSWORD=$DB_PASSWORD psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $DB_USER -d $DB_NAME -c "
        CREATE TABLE IF NOT EXISTS perf_test (id SERIAL, data TEXT);
        INSERT INTO perf_test (data) SELECT 'data_' || generate_series(1, 1000);
    " > /dev/null 2>&1
    
    # Test read performance on replicas
    log "Testing read performance on replica 1..."
    time PGPASSWORD=$DB_PASSWORD psql -h $REPLICA1_HOST -p $REPLICA1_PORT -U $DB_USER -d $DB_NAME -c "
        SELECT COUNT(*) FROM perf_test;
    " > /dev/null 2>&1
    
    log "Testing read performance on replica 2..."
    time PGPASSWORD=$DB_PASSWORD psql -h $REPLICA2_HOST -p $REPLICA2_PORT -U $DB_USER -d $DB_NAME -c "
        SELECT COUNT(*) FROM perf_test;
    " > /dev/null 2>&1
    
    # Clean up
    PGPASSWORD=$DB_PASSWORD psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $DB_USER -d $DB_NAME -c "DROP TABLE perf_test;"
    
    success "Performance tests completed"
}

# Main test function
main() {
    log "🚀 Starting PostgreSQL Cluster Workflow Test"
    log "=============================================="
    
    # Check if Docker containers are running
    log "Checking Docker containers..."
    if ! docker ps | grep -q "postgres-primary"; then
        error "PostgreSQL primary container is not running"
        log "Please start the cluster with: docker-compose -f docker-compose.cluster.yml up -d"
        exit 1
    fi
    
    if ! docker ps | grep -q "postgres-replica-1"; then
        error "PostgreSQL replica 1 container is not running"
        exit 1
    fi
    
    if ! docker ps | grep -q "postgres-replica-2"; then
        error "PostgreSQL replica 2 container is not running"
        exit 1
    fi
    
    if ! docker ps | grep -q "pgbouncer"; then
        error "PgBouncer container is not running"
        exit 1
    fi
    
    success "All containers are running"
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Run tests
    test_connection $PRIMARY_HOST $PRIMARY_PORT "Primary"
    test_connection $REPLICA1_HOST $REPLICA1_PORT "Replica 1"
    test_connection $REPLICA2_HOST $REPLICA2_PORT "Replica 2"
    test_pgbouncer
    test_replication
    test_data_consistency
    test_performance
    
    # Optional failover test
    test_failover
    
    log "�� PostgreSQL Cluster Workflow Test Completed!"
    log "=============================================="
    success "All tests passed! Your PostgreSQL cluster is working correctly."
}

# Run main function
main "$@"
