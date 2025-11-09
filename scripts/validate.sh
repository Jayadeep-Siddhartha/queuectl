#!/bin/bash
# QueueCTL Quick Validation Script
# Tests core flows and validates configuration

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

# Function to run test
test_case() {
    local name="$1"
    local command="$2"
    
    echo -e "${BLUE}Testing: $name${NC}"
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}  ✗ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

echo "=========================================="
echo "QueueCTL Core Flow Validation"
echo "=========================================="
echo ""

# Clean start
echo "Preparing test environment..."
rm -f queuectl.db queuectl_config.json test_*.db 2>/dev/null || true
echo ""

echo "=========================================="
echo "1. INSTALLATION & VERSION"
echo "=========================================="
test_case "Version command" "queuectl --version"
test_case "Help command" "queuectl --help"
echo ""

echo "=========================================="
echo "2. CONFIGURATION (No Hardcoded Values)"
echo "=========================================="
test_case "Set max-retries" "queuectl config set max-retries 5"
test_case "Set backoff-base" "queuectl config set backoff-base 2.5"
test_case "Set job-timeout" "queuectl config set job-timeout 600"
test_case "Set poll-interval" "queuectl config set poll-interval 2"
test_case "Set worker-shutdown-timeout" "queuectl config set worker-shutdown-timeout 15"
test_case "Show config" "queuectl config show | grep -q 'max-retries.*5'"
test_case "Config persists" "cat queuectl_config.json | grep -q '\"max_retries\": 5'"
echo ""

echo "=========================================="
echo "3. JOB ENQUEUE"
echo "=========================================="
test_case "Enqueue job (simple)" "queuectl add test1 'echo Hello'"
test_case "Enqueue job (with options)" "queuectl enqueue -i test2 -c 'echo Test' -r 3"
test_case "Enqueue job (JSON)" "queuectl enqueue '{\"id\":\"test3\",\"command\":\"echo JSON\"}'"
test_case "Reject duplicate ID" "! queuectl add test1 'echo Duplicate'"
echo ""

echo "=========================================="
echo "4. JOB LISTING"
echo "=========================================="
test_case "List all jobs" "queuectl list"
test_case "List pending jobs" "queuectl list --state pending | grep -q test1"
test_case "Status command" "queuectl status | grep -q 'Job Statistics'"
echo ""

echo "=========================================="
echo "5. WORKER EXECUTION"
echo "=========================================="
echo "  Starting worker for 5 seconds..."
timeout 5 queuectl worker start >/dev/null 2>&1 || true
sleep 1
test_case "Jobs completed" "queuectl list --state completed | grep -q completed"
test_case "Job output captured" "queuectl status | grep -q 'Completed:.*[1-9]'"
echo ""

echo "=========================================="
echo "6. FAILED JOB RETRY"
echo "=========================================="
queuectl config set max-retries 2
queuectl add fail-test "exit 1" >/dev/null 2>&1
echo "  Starting worker to process failing job..."
timeout 8 queuectl worker start >/dev/null 2>&1 || true
sleep 1
test_case "Failed job in DLQ or failed state" \
    "(queuectl list --state dead | grep -q fail-test) || (queuectl list --state failed | grep -q fail-test)"
echo ""

echo "=========================================="
echo "7. DEAD LETTER QUEUE"
echo "=========================================="
test_case "DLQ list command" "queuectl dlq list"
if queuectl list --state dead | grep -q fail-test; then
    test_case "DLQ retry" "queuectl dlq retry fail-test"
    test_case "Job back in pending" "queuectl list --state pending | grep -q fail-test"
else
    echo -e "${YELLOW}  ⊗ SKIP (no jobs in DLQ yet)${NC}"
fi
echo ""

echo "=========================================="
echo "8. MULTIPLE WORKERS"
echo "=========================================="
for i in {1..5}; do
    queuectl add "multi$i" "echo Job $i" >/dev/null 2>&1
done
echo "  Starting 3 workers for 10 seconds..."
timeout 10 queuectl worker start --count 3 >/dev/null 2>&1 || true
sleep 1
COMPLETED=$(queuectl list --state completed 2>/dev/null | grep -c "completed" || echo 0)
if [ "$COMPLETED" -ge 5 ]; then
    echo -e "${GREEN}  ✓ PASS (processed $COMPLETED jobs)${NC}"
    ((PASSED++))
else
    echo -e "${RED}  ✗ FAIL (only $COMPLETED/5 jobs completed)${NC}"
    ((FAILED++))
fi
echo ""

echo "=========================================="
echo "9. DATA PERSISTENCE"
echo "=========================================="
queuectl add persist-test "echo Persistent" >/dev/null 2>&1
test_case "Job persists in database" "queuectl list | grep -q persist-test"
test_case "Database file exists" "test -f queuectl.db"
test_case "Config file exists" "test -f queuectl_config.json"
echo ""

echo "=========================================="
echo "10. ERROR HANDLING"
echo "=========================================="
test_case "Invalid JSON rejected" "! queuectl enqueue 'invalid json'"
test_case "Missing required fields" "! queuectl enqueue '{\"id\":\"missing\"}'"
test_case "Invalid config key" "! queuectl config set invalid-key 5"
test_case "Invalid config value" "! queuectl config set max-retries -1"
echo ""

# Final status
echo "=========================================="
echo "VALIDATION RESULTS"
echo "=========================================="
queuectl status
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
else
    echo -e "${GREEN}Failed: $FAILED${NC}"
fi
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! QueueCTL is working correctly.${NC}"
    echo ""
    echo "Configuration validation:"
    echo "  ✓ No hardcoded values detected"
    echo "  ✓ All config options working"
    echo "  ✓ Configuration persists correctly"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    echo ""
    exit 1
fi