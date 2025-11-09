#!/bin/bash
# Simple functional test for QueueCTL
# Tests core flows without complex test framework

echo "=========================================="
echo "QueueCTL Simple Functional Test"
echo "=========================================="
echo ""

# Clean up
rm -f queuectl.db queuectl_config.json 2>/dev/null || true

PASS=0
FAIL=0

test_step() {
    echo "Testing: $1"
    if eval "$2" > /tmp/test_output.txt 2>&1; then
        echo "  ✓ PASS"
        ((PASS++))
        return 0
    else
        echo "  ✗ FAIL"
        if [ -f /tmp/test_output.txt ]; then
            echo "  Error: $(head -1 /tmp/test_output.txt)"
        fi
        ((FAIL++))
        return 1
    fi
}

echo "1. Installation Check"
echo "──────────────────────────────────────"
test_step "Version command" "queuectl --version"
test_step "Help command" "queuectl --help"
echo ""

echo "2. Job Enqueuing"
echo "──────────────────────────────────────"
test_step "Add job (simple)" "queuectl add job1 'echo test'"
test_step "Add job (with options)" "queuectl add job2 'echo test2' -r 5"
test_step "Job appears in list" "queuectl list | grep -q job1"
echo ""

echo "3. Configuration"
echo "──────────────────────────────────────"
test_step "Set max-retries" "queuectl config set max-retries 5"
test_step "Set backoff-base" "queuectl config set backoff-base 2.0"
test_step "Set poll-interval" "queuectl config set poll-interval 2"
test_step "Show config" "queuectl config show | grep -q max-retries"
echo ""

echo "4. Worker Execution"
echo "──────────────────────────────────────"
echo "  Starting worker for 5 seconds..."
timeout 5 queuectl worker start >/dev/null 2>&1 || true
sleep 1
test_step "Jobs completed" "queuectl list --state completed | grep -q completed"
echo ""

echo "5. Status Check"
echo "──────────────────────────────────────"
test_step "Status command" "queuectl status >/dev/null"
echo ""

echo "6. Data Persistence"
echo "──────────────────────────────────────"
test_step "Database exists" "test -f queuectl.db"
test_step "Config file exists" "test -f queuectl_config.json"
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi