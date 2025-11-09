"""
Persistent storage layer for jobs using SQLite
Thread-safe implementation with proper locking
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager
from threading import Lock

from queuectl.models import Job, JobState


class JobStorage:
    """
    Handles persistent storage of jobs using SQLite
    Thread-safe with connection pooling per thread
    """
    
    def __init__(self, db_path: str = "queuectl.db"):
        """
        Initialize storage with database path
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.lock = Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema with tables and indices"""
        with self._get_connection() as conn:
            # Create jobs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    next_retry_at TEXT,
                    error_message TEXT
                )
            """)
            
            # Create indices for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_state 
                ON jobs(state)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_next_retry 
                ON jobs(next_retry_at) 
                WHERE state = 'failed'
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON jobs(created_at)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """
        Get database connection with context manager
        
        Yields:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_job(self, job: Job) -> bool:
        """
        Save or update a job in the database
        
        Args:
            job: Job object to save
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO jobs 
                        (id, command, state, attempts, max_retries, 
                         created_at, updated_at, next_retry_at, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job.id, job.command, job.state, job.attempts,
                        job.max_retries, job.created_at, job.updated_at,
                        job.next_retry_at, job.error_message
                    ))
                    conn.commit()
                    return True
                except sqlite3.Error as e:
                    print(f"Database error: {e}")
                    return False
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Retrieve a job by ID
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Job object if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return Job(**dict(row))
            return None
    
    def get_next_pending_job(self) -> Optional[Job]:
        """
        Get the next pending job and atomically mark it as processing
        This is a critical operation that prevents duplicate processing
        
        Returns:
            Job object if available, None otherwise
        """
        with self.lock:
            with self._get_connection() as conn:
                # Get oldest pending job
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    WHERE state = ? 
                    ORDER BY created_at ASC 
                    LIMIT 1
                """, (JobState.PENDING,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                job = Job(**dict(row))
                
                # Atomically update to processing
                job.update_state(JobState.PROCESSING)
                conn.execute("""
                    UPDATE jobs 
                    SET state = ?, updated_at = ?
                    WHERE id = ? AND state = ?
                """, (job.state, job.updated_at, job.id, JobState.PENDING))
                
                conn.commit()
                
                # Verify we got the lock
                if conn.total_changes == 0:
                    return None
                
                return job
    
    def get_retryable_jobs(self) -> List[Job]:
        """
        Get failed jobs that are ready to retry (past their retry time)
        
        Returns:
            List of Job objects ready for retry
        """
        from datetime import datetime
        
        now = datetime.utcnow().isoformat() + "Z"
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM jobs 
                WHERE state = ? 
                AND next_retry_at IS NOT NULL 
                AND next_retry_at <= ?
                ORDER BY next_retry_at ASC
            """, (JobState.FAILED, now))
            
            return [Job(**dict(row)) for row in cursor.fetchall()]
    
    def list_jobs(self, state: Optional[str] = None, limit: int = 100) -> List[Job]:
        """
        List jobs, optionally filtered by state
        
        Args:
            state: Filter by job state (optional)
            limit: Maximum number of jobs to return
            
        Returns:
            List of Job objects
        """
        with self._get_connection() as conn:
            if state:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    WHERE state = ? 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                """, (state, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM jobs 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                """, (limit,))
            
            return [Job(**dict(row)) for row in cursor.fetchall()]
    
    def get_stats(self) -> dict:
        """
        Get job statistics by state
        
        Returns:
            Dictionary with counts for each state and total
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT state, COUNT(*) as count 
                FROM jobs 
                GROUP BY state
            """)
            
            stats = {
                JobState.PENDING: 0,
                JobState.PROCESSING: 0,
                JobState.COMPLETED: 0,
                JobState.FAILED: 0,
                JobState.DEAD: 0
            }
            
            for row in cursor.fetchall():
                stats[row['state']] = row['count']
            
            stats['total'] = sum(stats.values())
            
            return stats
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the database
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if job was deleted, False otherwise
        """
        with self.lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                conn.commit()
                return conn.total_changes > 0
    
    def reset_processing_jobs(self):
        """
        Reset any jobs stuck in processing state (e.g., after crash)
        This should be called on system startup
        """
        with self.lock:
            with self._get_connection() as conn:
                from datetime import datetime
                now = datetime.utcnow().isoformat() + "Z"
                
                cursor = conn.execute("""
                    SELECT COUNT(*) as count FROM jobs WHERE state = ?
                """, (JobState.PROCESSING,))
                
                count = cursor.fetchone()['count']
                
                if count > 0:
                    print(f"Resetting {count} stuck processing job(s)...")
                    conn.execute("""
                        UPDATE jobs 
                        SET state = ?, updated_at = ?
                        WHERE state = ?
                    """, (JobState.PENDING, now, JobState.PROCESSING))
                    conn.commit()
    
    def cleanup_old_jobs(self, days: int = 30):
        """
        Clean up completed jobs older than specified days
        
        Args:
            days: Number of days to keep completed jobs
            
        Returns:
            Number of jobs deleted
        """
        with self.lock:
            with self._get_connection() as conn:
                from datetime import datetime, timedelta
                
                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
                
                cursor = conn.execute("""
                    DELETE FROM jobs 
                    WHERE state = ? AND updated_at < ?
                """, (JobState.COMPLETED, cutoff))
                
                conn.commit()
                return cursor.rowcount