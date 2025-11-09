#!/bin/bash
# QueueCTL Demo Script
# This script demonstrates all major features of queuectl

set -e

echo "=========================================="
echo "QueueCTL Demo Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run command and show it
run_demo() {
    echo -e "${BLUE}$ $1${NC}"
    eval $1
    echo ""
    sleep 2
}

# Function for section headers
section() {
    echo ""
    echo -e "${GREEN}=== $1 ===${NC}"
    echo ""
}

# Clean up any existing test data
echo -e "${YELLOW}Cleaning up old test data...${NC}"
rm -f queuectl.db queuectl_config.json worker_log.txt
echo ""

# 1. Show help
section "1. Showing Help"
run_demo "queuectl --help"

# 2. Show version
section "2. Checking Version"
run_demo "queuectl --version"

# 3. Enqueue simple jobs
section "3. Enqueuing Jobs"
run_demo "queuectl enqueue '{\"id\":\"job1\",\"command\":\"echo Hello from job 1\"}'"
run_demo "queuectl enqueue '{\"id\":\"job2\",\"command\":\"sleep 2 && echo Job 2 completed\"}'"
run_demo "queuectl enqueue '{\"id\":\"job3\",\"command\":\"echo Job 3 done\"}'"

# 4. List pending jobs
section "4. Listing Pending Jobs"
run_demo "queuectl list --state pending"

# 5. Check status
section "5. Checking System Status"
run_demo "queuectl status"

# 6. Show configuration
section "6. Showing Configuration"
run_demo "queuectl config show"

# 7. Update configuration
section "7. Updating Configuration"
run_demo "queuectl config set max-retries 2"
run_demo "queuectl config set backoff-base 1.5"
run_demo "queuectl config show"

# 8. Enqueue a failing job
section "8. Enqueuing a Failing Job"
run_demo "queuectl enqueue '{\"id\":\"fail-job\",\"command\":\"exit 1\",\"max_retries\":2}'"

# 9. Enqueue more jobs
section "9. Enqueuing More Jobs"
for i in {4..8}; do
    queuectl enqueue "{\"id\":\"job$i\",\"command\":\"echo Processing job $i && sleep 1\"}"
done
echo "Enqueued 5 more jobs"
echo ""

# 10. List all jobs
section "10. Listing All Jobs"
run_demo "queuectl list --limit 20"

# 11. Start workers in background
section "11. Starting Workers (will run for 15 seconds)"
echo -e "${BLUE}$ queuectl worker start --count 3 &${NC}"
echo "Starting 3 workers in background..."
timeout 15 queuectl worker start --count 3 > worker_log.txt 2>&1 &
WORKER_PID=$!
echo "Workers started with PID: $WORKER_PID"
echo ""

# Wait and show progress
echo "Workers processing jobs..."
for i in {1..15}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

# Wait for workers to finish
wait $WORKER_PID 2>/dev/null || true

# 12. Check completed jobs
section "12. Checking Completed Jobs"
run_demo "queuectl list --state completed"

# 13. Check failed/dead jobs
section "13. Checking Failed and Dead Jobs"
run_demo "queuectl list --state failed"
run_demo "queuectl list --state dead"

# 14. List DLQ
section "14. Checking Dead Letter Queue"
run_demo "queuectl dlq list"

# 15. Try to retry a DLQ job
section "15. Retrying Job from DLQ"
# Check if there's a job in DLQ
DLQ_JOB=$(queuectl list --state dead --limit 1 2>/dev/null | grep -oP '^\S+' | tail -1)
if [ ! -z "$DLQ_JOB" ]; then
    echo "Found DLQ job: $DLQ_JOB"
    run_demo "queuectl dlq retry $DLQ_JOB"
    run_demo "queuectl list --state pending"
else
    echo "No jobs in DLQ to retry"
    echo ""
fi

# 16. Final status
section "16. Final System Status"
run_demo "queuectl status"

# 17. Show worker log
section "17. Worker Log (last 30 lines)"
if [ -f worker_log.txt ]; then
    echo -e "${BLUE}$ tail -30 worker_log.txt${NC}"
    tail -30 worker_log.txt
    echo ""
fi

# Summary
echo ""
echo -e "${GREEN}=========================================="
echo "Demo Completed Successfully!"
echo "==========================================${NC}"
echo ""
echo "Files created:"
echo "  - queuectl.db (job database)"
echo "  - queuectl_config.json (configuration)"
echo "  - worker_log.txt (worker output)"
echo ""
echo "Try these commands:"
echo "  queuectl status              # Check system status"
echo "  queuectl list                # List all jobs"
echo "  queuectl worker start -c 2   # Start 2 workers"
echo "  queuectl dlq list            # Check Dead Letter Queue"
echo ""
echo "To clean up: rm queuectl.db queuectl_config.json worker_log.txt"
echo ""