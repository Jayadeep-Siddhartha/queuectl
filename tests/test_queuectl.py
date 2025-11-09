"""
Test suite for queuectl
Run with: python -m pytest tests/ or python tests/test_queuectl.py
"""

import os
import time
import subprocess
from pathlib import Path
import sys


class TestRunner:
    """Simple test runner for queuectl"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_db = "test_queuectl.db"
        self.test_config = "test_queuectl_config.json"
    
    def setup(self):
        """Setup test environment"""
        # Remove existing test files
        for f in [self.test_db, self.test_config]:
            if Path(f).exists():
                os.remove(f)
        print("🔧 Test environment setup complete\n")
    
    def teardown(self):
        """Cleanup test environment"""
        for f in [self.test_db, self.test_config]:
            if Path(f).exists():
                os.remove(f)
    
    def run_command(self, cmd: str, capture=True):
        """Run a shell command"""
        if capture:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True
            )
            return result.returncode, result.stdout, result.stderr
        else:
            return subprocess.run(cmd, shell=True).returncode, "", ""
    
    def assert_equals(self, actual, expected, test_name):
        """Assert equality"""
        if actual == expected:
            print(f"✅ PASS: {test_name}")
            self.passed += 1
            return True
        else:
            print(f"❌ FAIL: {test_name}")
            print(f"   Expected: {expected}")
            print(f"   Got: {actual}")
            self.failed += 1
            return False
    
    def assert_contains(self, text, substring, test_name):
        """Assert text contains substring"""
        if substring in text:
            print(f"✅ PASS: {test_name}")
            self.passed += 1
            return True
        else:
            print(f"❌ FAIL: {test_name}")
            print(f"   Expected substring: {substring}")
            print(f"   In text: {text[:200]}")
            self.failed += 1
            return False
    
    def test_01_enqueue_job(self):
        """Test enqueuing a basic job"""
        # Use the simple add command instead of JSON
        code, stdout, stderr = self.run_command(
            'python -m queuectl.cli add test1 "echo Hello World"'
        )
        self.assert_equals(code, 0, "Enqueue returns success code")
        self.assert_contains(stdout, "Job added successfully", "Enqueue shows success message")
        self.assert_contains(stdout, "test1", "Enqueue shows job ID")
    
    def test_02_enqueue_duplicate(self):
        """Test enqueuing duplicate job ID fails"""
        # Try to add duplicate
        code, stdout, stderr = self.run_command(
            'python -m queuectl.cli add test1 "echo Duplicate"'
        )
        self.assert_equals(code, 1, "Duplicate enqueue returns error code")
        self.assert_contains(stdout + stderr, "already exists", "Shows duplicate error")
    
    def test_03_list_jobs(self):
        """Test listing jobs"""
        code, stdout, stderr = self.run_command(
            'python -m queuectl.cli list --state pending'
        )
        self.assert_equals(code, 0, "List returns success code")
        self.assert_contains(stdout, "test1", "Job appears in list")
    
    def test_04_status_command(self):
        """Test status command"""
        code, stdout, stderr = self.run_command('python -m queuectl.cli status')
        self.assert_equals(code, 0, "Status returns success code")
        self.assert_contains(stdout, "Job Statistics", "Status shows statistics")
        self.assert_contains(stdout, "Workers", "Status shows worker info")
    
    def test_05_worker_execution(self):
        """Test worker executes job successfully"""
        print("   Starting worker for 5 seconds...")
        proc = subprocess.Popen(
            'timeout 5 python -m queuectl.cli worker start --count 1 || true',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(6)
        
        # Check if job completed
        code, stdout, stderr = self.run_command(
            'python -m queuectl.cli list --state completed'
        )
        self.assert_contains(stdout, "test1", "Job completed successfully")
    
    def test_06_failed_job(self):
        """Test job failure and retry"""
        # Enqueue a job that will fail using add command
        self.run_command(
            'python -m queuectl.cli add fail1 "exit 1" -r 2'
        )
        
        # Start worker
        print("   Starting worker to process failing job...")
        proc = subprocess.Popen(
            'timeout 3 python -m queuectl.cli worker start --count 1 || true',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(4)
        
        # Check job is in failed or dead state
        code1, stdout1, stderr1 = self.run_command(
            'python -m queuectl.cli list --state failed'
        )
        code2, stdout2, stderr2 = self.run_command(
            'python -m queuectl.cli list --state dead'
        )
        
        is_failed_or_dead = "fail1" in stdout1 or "fail1" in stdout2
        self.assert_equals(
            is_failed_or_dead, True,
            "Failed job moved to failed or dead state"
        )
    
    def test_07_dlq_list(self):
        """Test DLQ list command"""
        code, stdout, stderr = self.run_command('python -m queuectl.cli dlq list')
        self.assert_equals(code, 0, "DLQ list returns success code")
    
    def test_08_config_set(self):
        """Test configuration management"""
        code, stdout, stderr = self.run_command(
            'python -m queuectl.cli config set max-retries 5'
        )
        self.assert_equals(code, 0, "Config set returns success code")
        self.assert_contains(stdout, "updated", "Config set shows success")
        
        # Verify config was saved
        code, stdout, stderr = self.run_command('python -m queuectl.cli config show')
        self.assert_contains(stdout, "5", "Config shows updated value")
    
    def test_09_config_show(self):
        """Test config show command"""
        code, stdout, stderr = self.run_command('python -m queuectl.cli config show')
        self.assert_equals(code, 0, "Config show returns success code")
        self.assert_contains(stdout, "max-retries", "Config shows settings")
    
    def test_10_persistence(self):
        """Test data persists"""
        # Enqueue a job using add command
        self.run_command(
            'python -m queuectl.cli add persist1 "echo Persistent"'
        )
        
        # List jobs
        code, stdout, stderr = self.run_command('python -m queuectl.cli list')
        self.assert_contains(stdout, "persist1", "Job persists in database")
    
    def test_11_multiple_jobs(self):
        """Test multiple job enqueue"""
        # Use add command for multiple jobs
        for i in range(3):
            self.run_command(
                f'python -m queuectl.cli add multi{i} "echo Job {i}"'
            )
        
        code, stdout, stderr = self.run_command('python -m queuectl.cli list --state pending')
        
        has_all = all(f"multi{i}" in stdout for i in range(3))
        self.assert_equals(has_all, True, "All jobs enqueued successfully")
    
    def test_12_invalid_json(self):
        """Test invalid JSON handling"""
        # Test with enqueue command (JSON mode)
        code, stdout, stderr = self.run_command(
            'python -m queuectl.cli enqueue \'{"invalid json\''
        )
        self.assert_equals(code, 1, "Invalid JSON returns error code")
        self.assert_contains(stdout + stderr, "Invalid JSON", "Shows JSON error")
        
        # Test missing required field with add command
        code, stdout, stderr = self.run_command(
            'python -m queuectl.cli add "" "echo test"'
        )
        # Should fail with empty ID
        self.assert_equals(code, 1, "Empty ID returns error code")
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 70)
        print("QueueCTL Test Suite")
        print("=" * 70)
        print()
        
        self.setup()
        
        tests = [
            self.test_01_enqueue_job,
            self.test_02_enqueue_duplicate,
            self.test_03_list_jobs,
            self.test_04_status_command,
            self.test_05_worker_execution,
            self.test_06_failed_job,
            self.test_07_dlq_list,
            self.test_08_config_set,
            self.test_09_config_show,
            self.test_10_persistence,
            self.test_11_multiple_jobs,
            self.test_12_invalid_json,
        ]
        
        for i, test in enumerate(tests, 1):
            print(f"\n{'─' * 70}")
            print(f"Test {i:02d}: {test.__doc__}")
            print('─' * 70)
            try:
                test()
            except Exception as e:
                print(f"❌ FAIL: Test threw exception: {e}")
                import traceback
                traceback.print_exc()
                self.failed += 1
        
        print("\n" + "=" * 70)
        print(f"Test Results: {self.passed} passed, {self.failed} failed")
        print("=" * 70)
        
        self.teardown()
        
        return self.failed == 0


if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)