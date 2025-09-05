#!/bin/bash

# PostgreSQL Cluster Testing Script
# Script để chạy các test cluster một cách dễ dàng

echo "🚀 PostgreSQL Cluster Testing Suite"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️ $message${NC}"
            ;;
    esac
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_status "ERROR" "Python3 is not installed or not in PATH"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_status "WARNING" "Docker is not installed or not in PATH"
    print_status "WARNING" "Some tests may fail"
fi

# Check if cluster containers are running
print_status "INFO" "Checking cluster containers..."
if command -v docker &> /dev/null; then
    if docker ps --format "{{.Names}}" | grep -q "postgres-primary"; then
        print_status "SUCCESS" "Primary container is running"
    else
        print_status "WARNING" "Primary container is not running"
    fi
    
    if docker ps --format "{{.Names}}" | grep -q "postgres-replica"; then
        print_status "SUCCESS" "Replica container is running"
    else
        print_status "WARNING" "Replica container is not running"
    fi
fi

# Function to run a specific test
run_test() {
    local test_file=$1
    local test_name=$2
    
    if [ ! -f "$test_file" ]; then
        print_status "ERROR" "Test file $test_file not found"
        return 1
    fi
    
    print_status "INFO" "Running $test_name..."
    echo "----------------------------------------"
    
    if python3 "$test_file"; then
        print_status "SUCCESS" "$test_name completed successfully"
        return 0
    else
        print_status "ERROR" "$test_name failed"
        return 1
    fi
}

# Function to run all tests
run_all_tests() {
    print_status "INFO" "Running all cluster tests..."
    echo "========================================"
    
    python3 master_cluster_test.py
}

# Function to run quick tests only
run_quick_tests() {
    print_status "INFO" "Running quick tests only..."
    echo "====================================="
    
    tests=(
        "simple_cluster_test.py:Simple Cluster Test"
        "test_primary_replica_flow.py:Primary Replica Flow Test"
    )
    
    for test in "${tests[@]}"; do
        IFS=':' read -r file name <<< "$test"
        run_test "$file" "$name"
        echo
    done
}

# Function to run comprehensive tests
run_comprehensive_tests() {
    print_status "INFO" "Running comprehensive tests..."
    echo "======================================="
    
    tests=(
        "comprehensive_cluster_test.py:Comprehensive Cluster Test"
        "advanced_cluster_test.py:Advanced Cluster Test"
        "network_performance_test.py:Network Performance Test"
    )
    
    for test in "${tests[@]}"; do
        IFS=':' read -r file name <<< "$test"
        run_test "$file" "$name"
        echo
    done
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  all              Run all cluster tests (default)"
    echo "  quick            Run quick tests only"
    echo "  comprehensive    Run comprehensive tests only"
    echo "  simple           Run simple cluster test only"
    echo "  flow             Run primary replica flow test only"
    echo "  scenarios        Run cluster scenarios test only"
    echo "  crud             Run CRUD operations test only"
    echo "  comprehensive    Run comprehensive cluster test only"
    echo "  advanced         Run advanced cluster test only"
    echo "  network          Run network performance test only"
    echo "  master           Run master test suite"
    echo "  list             List available test suites"
    echo "  help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 quick              # Run quick tests only"
    echo "  $0 simple             # Run simple test only"
    echo "  $0 master             # Run master test suite"
}

# Main script logic
case "${1:-all}" in
    "all")
        run_all_tests
        ;;
    "quick")
        run_quick_tests
        ;;
    "comprehensive")
        run_comprehensive_tests
        ;;
    "simple")
        run_test "simple_cluster_test.py" "Simple Cluster Test"
        ;;
    "flow")
        run_test "test_primary_replica_flow.py" "Primary Replica Flow Test"
        ;;
    "scenarios")
        run_test "cluster_scenarios_test.py" "Cluster Scenarios Test"
        ;;
    "crud")
        run_test "test_crud_operations.py" "CRUD Operations Test"
        ;;
    "comprehensive")
        run_test "comprehensive_cluster_test.py" "Comprehensive Cluster Test"
        ;;
    "advanced")
        run_test "advanced_cluster_test.py" "Advanced Cluster Test"
        ;;
    "network")
        run_test "network_performance_test.py" "Network Performance Test"
        ;;
    "master")
        python3 master_cluster_test.py
        ;;
    "list")
        python3 master_cluster_test.py --list
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_status "ERROR" "Unknown option: $1"
        show_help
        exit 1
        ;;
esac

print_status "INFO" "Cluster testing completed!"
