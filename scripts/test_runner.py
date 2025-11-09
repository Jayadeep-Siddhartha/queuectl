#!/usr/bin/env python3
"""
QueueCTL Cross-Platform Test Runner
Works on Windows, Mac, and Linux
"""

import subprocess
import os
import sys
import time
from pathlib import Path


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        
    def cleanup(self):
        """Clean test environment"""
        for f in ['queuectl.db', 'queuectl_config.json']:
            try:
                os.remove(f)
            except:
                pass
    
    def run_command(self, cmd):
        """Run command and return success/failure"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def test(self, name, cmd, check_output=None):
        """Run a test"""
        print(f"Testing: {name}")
        success, stdout, stderr = self.run_command(cmd)
        
        # Additional output check if specified
        if success and check_output:
            if check_output not in stdout and check_output not in stderr:
                success = False
        
        if success:
            print("  ✓ PASS")
            self.passed += 1
        else:
            print("  ✗ FAIL")
            if stdout or stderr:
                error = (stdout + stderr)[:100]
                print(f"  Error: {error}")
            self.failed += 1
    
    def run_all(self):
        """Run all tests"""
        print("=" * 50)
        print("QueueCTL Cross-Platform Test")
        print("=" * 50)
        print()
        
        # Cleanup
        self.cleanup()
        
        # 1. Installation
        print("1. INSTALLATION CHECK")
        print("-" * 50)
        self.test("Version command", "queuectl --version")
        self.test("Help command", "queuectl --help")
        print()
        
        # 2. Job Enqueuing
        print("2. JOB ENQUEUING")
        print("-" * 50)
        self.test("Add job (simple)", 'queuectl add job1 "echo test"')
        self.test("Add job (with retries)", 'queuectl add job2 "echo test2" -r 5')
        self.test("List jobs", "queuectl list", check_output="job1")
        print()
        
        # 3. Configuration
        print("3. CONFIGURATION")
        print("-" * 50)
        self.test("Set max-retries", "queuectl config set max-retries 5")
        self.test("Set backoff-base", "queuectl config set backoff-base 2.0")
        self.test("Set poll-interval", "queuectl config set poll-interval 2")
        self.test("Show config", "queuectl config show", check_output="max-retries")
        print()
        
        # 4. Worker Execution
        print("4. WORKER EXECUTION")
        print("-" * 50)
        print("  Starting worker for 5 seconds...")
        
        # Start worker in background
        if sys.platform == 'win32':
            subprocess.Popen(
                'queuectl worker start',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                'queuectl worker start',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
        
        time.sleep(6)
        
        # Kill worker
        if sys.platform == 'win32':
            os.system('taskkill /F /IM python.exe /T >nul 2>&1')
        else:
            os.system('pkill -f queuectl')
        
        time.sleep(1)
        self.test("Jobs completed", "queuectl list --state completed", check_output="completed")
        print()
        
        # 5. Status
        print("5. STATUS CHECK")
        print("-" * 50)
        self.test("Status command", "queuectl status")
        print()
        
        # 6. Data Persistence
        print("6. DATA PERSISTENCE")
        print("-" * 50)
        self.test("Database exists", f"python -c \"import os; exit(0 if os.path.exists('queuectl.db') else 1)\"")
        self.test("Config exists", f"python -c \"import os; exit(0 if os.path.exists('queuectl_config.json') else 1)\"")
        print()
        
        # Summary
        print("=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print()
        
        if self.failed == 0:
            print("✓ All tests passed!")
            return 0
        else:
            print("✗ Some tests failed")
            return 1


if __name__ == '__main__':
    runner = TestRunner()
    exit_code = runner.run_all()
    sys.exit(exit_code)