"""
Job model and related classes
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json


class JobState:
    """Job state constants"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class Job:
    """
    Represents a background job in the queue system
    
    Attributes:
        id: Unique identifier for the job
        command: Shell command to execute
        state: Current job state (pending, processing, completed, failed, dead)
        attempts: Number of execution attempts
        max_retries: Maximum number of retry attempts
        created_at: Job creation timestamp
        updated_at: Last update timestamp
        next_retry_at: Timestamp for next retry (if failed)
        error_message: Last error message (if failed)
    """
    id: str
    command: str
    state: str = JobState.PENDING
    attempts: int = 0
    max_retries: int = 3
    created_at: str = None
    updated_at: str = None
    next_retry_at: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided"""
        now = datetime.utcnow().isoformat() + "Z"
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self) -> dict:
        """Convert job to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert job to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        """Create job from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Job':
        """Create job from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def update_state(self, new_state: str, error_message: Optional[str] = None):
        """
        Update job state and timestamp
        
        Args:
            new_state: New state to set
            error_message: Optional error message if failed
        """
        self.state = new_state
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        if error_message:
            self.error_message = error_message
    
    def increment_attempts(self):
        """Increment attempt counter and update timestamp"""
        self.attempts += 1
        self.updated_at = datetime.utcnow().isoformat() + "Z"
    
    def should_retry(self) -> bool:
        """
        Check if job should be retried
        
        Returns:
            True if attempts < max_retries, False otherwise
        """
        return self.attempts < self.max_retries
    
    def calculate_retry_delay(self, backoff_base: float = 2.0) -> float:
        """
        Calculate exponential backoff delay in seconds
        Formula: delay = base ^ attempts
        
        Args:
            backoff_base: Base for exponential calculation
            
        Returns:
            Delay in seconds
        """
        return backoff_base ** self.attempts
    
    def set_next_retry(self, backoff_base: float = 2.0):
        """
        Calculate and set next retry timestamp
        
        Args:
            backoff_base: Base for exponential backoff calculation
        """
        delay = self.calculate_retry_delay(backoff_base)
        next_time = datetime.utcnow().timestamp() + delay
        self.next_retry_at = datetime.fromtimestamp(next_time).isoformat() + "Z"
    
    def __str__(self) -> str:
        """String representation of job"""
        return f"Job(id={self.id}, state={self.state}, attempts={self.attempts}/{self.max_retries})"
    
    def __repr__(self) -> str:
        """Detailed representation of job"""
        return f"Job(id='{self.id}', command='{self.command}', state='{self.state}')"