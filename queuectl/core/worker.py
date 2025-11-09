"""
Worker process management and job execution
"""

import subprocess
import time
import threading
from typing import List
import signal
import sys

from queuectl.core.queue_manager import QueueManager
from queuectl.utils import Config
from queuectl.models import Job


class Worker:
    """
    Single worker that processes jobs from the queue
    Runs in a separate thread and executes shell commands
    """
    
    def __init__(self, worker_id: int, queue_manager: QueueManager, config: Config):
        """
        Initialize worker
        
        Args:
            worker_id: Unique identifier for this worker
            queue_manager: Queue manager instance
            config: Configuration object
        """
        self.worker_id = worker_id
        self.queue_manager = queue_manager
        self.config = config
        self.running = False
        self.thread = None
        self.current_job = None
    
    def start(self):
        """Start the worker thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the worker gracefully"""
        self.running = False
    
    def join(self, timeout=None):
        """
        Wait for worker thread to finish
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        if self.thread:
            self.thread.join(timeout)
    
    def _run(self):
        """
        Main worker loop
        Continuously polls for jobs and executes them
        """
        print(f"[Worker-{self.worker_id}] Started")
        while self.running:
            try:
                # Get next job
                job = self.queue_manager.get_next_job()
                
                if job:
                    self.current_job = job
                    print(f"[Worker-{self.worker_id}] Processing job: {job.id}")
                    self._execute_job(job)
                    self.current_job = None
                else:
                    # No jobs available, sleep briefly
                    time.sleep(self.config.get('poll_interval', 1))
                    
            except Exception as e:
                print(f"[Worker-{self.worker_id}] Error: {e}")
                time.sleep(self.config.get('poll_interval', 1))
        
        print(f"[Worker-{self.worker_id}] Stopped")
    
    def _execute_job(self, job: Job):
        """
        Execute a job command
        
        Handles command execution, captures output/errors,
        and updates job state based on exit code
        
        Args:
            job: Job to execute
        """
        try:
            # Get timeout from config (default 300 seconds = 5 minutes)
            timeout = self.config.get('job_timeout', 300)
            
            # Execute command using shell
            result = subprocess.run(
                job.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Check exit code
            if result.returncode == 0:
                print(f"[Worker-{self.worker_id}] ✓ Job {job.id} completed successfully")
                if result.stdout:
                    print(f"[Worker-{self.worker_id}]   Output: {result.stdout.strip()[:100]}")
                self.queue_manager.mark_completed(job)
            else:
                error_msg = f"Command exited with code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr[:200]}"
                
                print(f"[Worker-{self.worker_id}] ✗ Job {job.id} failed: {error_msg}")
                self.queue_manager.mark_failed(job, error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            print(f"[Worker-{self.worker_id}] ⏱ Job {job.id} timed out")
            self.queue_manager.mark_failed(job, error_msg)
            
        except FileNotFoundError:
            error_msg = "Command not found"
            print(f"[Worker-{self.worker_id}] ✗ Job {job.id} failed: {error_msg}")
            self.queue_manager.mark_failed(job, error_msg)
            
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            print(f"[Worker-{self.worker_id}] ✗ Job {job.id} error: {error_msg}")
            self.queue_manager.mark_failed(job, error_msg)
    
    def is_busy(self) -> bool:
        """
        Check if worker is currently processing a job
        
        Returns:
            True if processing, False otherwise
        """
        return self.current_job is not None


class WorkerManager:
    """
    Manages multiple worker processes
    Handles worker lifecycle and graceful shutdown
    """
    
    def __init__(self, queue_manager: QueueManager, config: Config):
        """
        Initialize worker manager
        
        Args:
            queue_manager: Queue manager instance
            config: Configuration object
        """
        self.queue_manager = queue_manager
        self.config = config
        self.workers: List[Worker] = []
        self.shutdown_event = threading.Event()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (SIGINT, SIGTERM)
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        print("\n⚠ Received shutdown signal...")
        self.stop_workers()
        sys.exit(0)
    
    def start_workers(self, count: int):
        """
        Start specified number of workers
        
        Args:
            count: Number of workers to start
        """
        for i in range(count):
            worker = Worker(i + 1, self.queue_manager, self.config)
            worker.start()
            self.workers.append(worker)
    
    def stop_workers(self):
        """
        Stop all workers gracefully
        Waits for current jobs to complete (up to 10 seconds per worker)
        """
        if not self.workers:
            return
            
        print("⏳ Stopping workers gracefully...")
        
        # Signal all workers to stop
        for worker in self.workers:
            worker.stop()
        
        # Wait for all workers to finish current job
        for worker in self.workers:
            if worker.is_busy():
                print(f"   Waiting for Worker-{worker.worker_id} to finish current job...")
            worker.join(timeout=self.config.get('worker_shutdown_timeout', 10))
        
        self.workers.clear()
        self.shutdown_event.set()
        print("✓ All workers stopped")
    
    def wait(self):
        """Wait for shutdown signal"""
        self.shutdown_event.wait()
    
    def get_active_count(self) -> int:
        """
        Get number of active workers
        
        Returns:
            Count of running workers
        """
        return len([w for w in self.workers if w.running])
    
    def get_busy_count(self) -> int:
        """
        Get number of workers currently processing jobs
        
        Returns:
            Count of busy workers
        """
        return len([w for w in self.workers if w.is_busy()])
    
    def get_status(self) -> dict:
        """
        Get worker manager status
        
        Returns:
            Dictionary with worker statistics
        """
        return {
            'total': len(self.workers),
            'active': self.get_active_count(),
            'busy': self.get_busy_count(),
            'idle': self.get_active_count() - self.get_busy_count()
        }