"""
Queue manager - handles job lifecycle and queue operations
"""

from typing import List, Optional
from datetime import datetime

from queuectl.models import Job, JobState
from queuectl.storage import JobStorage
from queuectl.utils import Config


class QueueManager:
    """
    Manages the job queue, including enqueuing, state transitions,
    retry logic, and Dead Letter Queue operations
    """
    
    def __init__(self, config: Config, storage_path: str = "queuectl.db"):
        """
        Initialize queue manager
        
        Args:
            config: Configuration object
            storage_path: Path to SQLite database
        """
        self.config = config
        self.storage = JobStorage(storage_path)
        
        # Reset any jobs stuck in processing state on startup
        self.storage.reset_processing_jobs()
    
    def enqueue(self, job_id: str, command: str, max_retries: Optional[int] = None) -> Job:
        """
        Enqueue a new job to the queue
        
        Args:
            job_id: Unique identifier for the job
            command: Shell command to execute
            max_retries: Maximum retry attempts (uses config default if None)
        
        Returns:
            Created Job object
            
        Raises:
            ValueError: If job with same ID already exists
        """
        if max_retries is None:
            max_retries = self.config.get('max_retries')
        
        # Check if job already exists
        existing = self.storage.get_job(job_id)
        if existing:
            raise ValueError(f"Job with ID '{job_id}' already exists")
        
        # Create new job
        job = Job(
            id=job_id,
            command=command,
            max_retries=max_retries
        )
        
        # Persist to storage
        self.storage.save_job(job)
        return job
    
    def get_next_job(self) -> Optional[Job]:
        """
        Get the next job to process
        
        Checks for:
        1. Retryable failed jobs (past their retry time)
        2. Pending jobs
        
        Returns:
            Job object or None if no jobs available
        """
        # First check for retryable failed jobs
        retryable = self.storage.get_retryable_jobs()
        if retryable:
            job = retryable[0]
            # Move back to pending for retry
            job.update_state(JobState.PENDING)
            self.storage.save_job(job)
        
        # Get next pending job (atomic operation)
        return self.storage.get_next_pending_job()
    
    def mark_completed(self, job: Job):
        """
        Mark a job as completed
        
        Args:
            job: Job that completed successfully
        """
        job.update_state(JobState.COMPLETED)
        self.storage.save_job(job)
    
    def mark_failed(self, job: Job, error_message: str):
        """
        Mark a job as failed and handle retry logic
        
        If job has remaining retries, schedule it for retry with exponential backoff.
        Otherwise, move to Dead Letter Queue.
        
        Args:
            job: Job that failed
            error_message: Error description
        """
        job.increment_attempts()
        
        if job.should_retry():
            # Schedule for retry with exponential backoff
            job.update_state(JobState.FAILED, error_message)
            job.set_next_retry(self.config.get('backoff_base'))
            print(f"Job {job.id} will retry in {job.calculate_retry_delay(self.config.get('backoff_base')):.1f} seconds")
        else:
            # Move to DLQ - no more retries
            job.update_state(JobState.DEAD, error_message)
            print(f"Job {job.id} moved to Dead Letter Queue after {job.attempts} attempts")
        
        self.storage.save_job(job)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a specific job by ID
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Job object if found, None otherwise
        """
        return self.storage.get_job(job_id)
    
    def list_jobs(self, state: Optional[str] = None, limit: int = 100) -> List[Job]:
        """
        List jobs, optionally filtered by state
        
        Args:
            state: Filter by job state (optional)
            limit: Maximum number of jobs to return
            
        Returns:
            List of Job objects
        """
        return self.storage.list_jobs(state, limit)
    
    def get_stats(self) -> dict:
        """
        Get job statistics
        
        Returns:
            Dictionary with counts for each state
        """
        return self.storage.get_stats()
    
    def retry_dlq_job(self, job_id: str) -> bool:
        """
        Retry a job from the Dead Letter Queue
        
        Resets the job to pending state with attempts reset to 0
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if job was found and moved, False otherwise
        """
        job = self.storage.get_job(job_id)
        
        if not job or job.state != JobState.DEAD:
            return False
        
        # Reset job for retry
        job.attempts = 0
        job.update_state(JobState.PENDING)
        job.next_retry_at = None
        job.error_message = None
        
        self.storage.save_job(job)
        return True
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the queue
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if job was deleted, False otherwise
        """
        return self.storage.delete_job(job_id)
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Clean up completed jobs older than specified days
        
        Args:
            days: Number of days to keep completed jobs
            
        Returns:
            Number of jobs deleted
        """
        return self.storage.cleanup_old_jobs(days)