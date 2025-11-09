#!/usr/bin/env python3
"""
QueueCTL - CLI-based Background Job Queue System
Command-line interface implementation
"""

import click
import json
import sys
import time
from typing import Optional

from queuectl.core import QueueManager, WorkerManager
from queuectl.utils import Config


# Initialize components
config = Config()
queue_manager = QueueManager(config)
worker_manager = WorkerManager(queue_manager, config)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    QueueCTL - Background Job Queue System
    
    A production-grade CLI tool for managing background jobs with
    automatic retries, exponential backoff, and Dead Letter Queue.
    """
    pass


@cli.command()
@click.argument('job_id')
@click.argument('command')
@click.option('--max-retries', '-r', type=int, help='Maximum retry attempts')
def add(job_id: str, command: str, max_retries: Optional[int]):
    """
    Quick way to add a job (no JSON needed).
    
    This is a shortcut for enqueue that doesn't require JSON.
    
    Example:
    
        queuectl add job1 "echo Hello"
        
        queuectl add backup "python backup.py" --max-retries 5
        
        queuectl add process "ls -la"
    """
    try:
        # Enqueue job
        job = queue_manager.enqueue(
            job_id=job_id,
            command=command,
            max_retries=max_retries if max_retries is not None else config.get('max_retries')
        )
        
        # Success output
        click.echo(f"✓ Job added successfully")
        click.echo(f"  ID:          {job.id}")
        click.echo(f"  Command:     {job.command}")
        click.echo(f"  Max Retries: {job.max_retries}")
        
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_data', required=False)
@click.option('--file', '-f', type=click.File('r'), help='Read job data from file')
@click.option('--id', '-i', help='Job ID (alternative to JSON)')
@click.option('--command', '-c', help='Command to execute (alternative to JSON)')
@click.option('--max-retries', '-r', type=int, help='Maximum retry attempts')
def enqueue(job_data: Optional[str], file, id: Optional[str], command: Optional[str], max_retries: Optional[int]):
    """
    Enqueue a new job to the queue.
    
    Two ways to enqueue:
    
    1. Simple mode (no JSON needed):
    
        queuectl enqueue --id job1 --command "echo Hello"
        
        queuectl enqueue -i backup -c "python backup.py" -r 5
    
    2. JSON mode:
    
        queuectl enqueue '{"id":"job1","command":"echo Hello"}'
        
        queuectl enqueue --file job.json
        
        echo '{"id":"job1","command":"echo test"}' | queuectl enqueue -
    
    On Windows CMD (if using JSON):
    
        queuectl enqueue "{\"id\":\"job1\",\"command\":\"echo Hello\"}"
    """
    try:
        # Mode 1: Simple arguments (--id and --command)
        if id and command:
            job_dict = {
                'id': id,
                'command': command
            }
            if max_retries is not None:
                job_dict['max_retries'] = max_retries
        
        # Mode 2: JSON from various sources
        else:
            # Read from file if specified
            if file:
                job_data = file.read()
            # Read from stdin if job_data is "-"
            elif job_data == "-":
                job_data = sys.stdin.read()
            elif not job_data:
                click.echo("❌ Error: Either provide JSON or use --id and --command", err=True)
                click.echo("", err=True)
                click.echo("Simple mode:", err=True)
                click.echo("   queuectl enqueue --id job1 --command \"echo Hello\"", err=True)
                click.echo("", err=True)
                click.echo("JSON mode:", err=True)
                click.echo("   queuectl enqueue '{\"id\":\"job1\",\"command\":\"echo Hello\"}'", err=True)
                sys.exit(1)
            
            job_dict = json.loads(job_data)
        
        # Validate required fields
        if 'id' not in job_dict:
            click.echo("❌ Error: Job must contain 'id' field", err=True)
            sys.exit(1)
            
        if 'command' not in job_dict:
            click.echo("❌ Error: Job must contain 'command' field", err=True)
            sys.exit(1)
        
        # Enqueue job
        job = queue_manager.enqueue(
            job_id=job_dict['id'],
            command=job_dict['command'],
            max_retries=job_dict.get('max_retries', config.get('max_retries'))
        )
        
        # Success output
        click.echo(f"✓ Job enqueued successfully")
        click.echo(f"  ID:          {job.id}")
        click.echo(f"  Command:     {job.command}")
        click.echo(f"  Max Retries: {job.max_retries}")
        click.echo(f"  Created:     {job.created_at}")
        
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error: Invalid JSON format - {str(e)}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def worker():
    """Manage worker processes"""
    pass


@worker.command()
@click.option('--count', '-c', default=1, help='Number of workers to start', type=int)
def start(count: int):
    """
    Start worker processes to execute jobs.
    
    Workers will run continuously until stopped with Ctrl+C.
    Multiple workers can process jobs concurrently.
    
    Example:
    
        queuectl worker start --count 3
    """
    try:
        if count < 1:
            click.echo("❌ Error: Worker count must be at least 1", err=True)
            sys.exit(1)
        
        worker_manager.start_workers(count)
        click.echo(f"✓ Started {count} worker(s)")
        click.echo("  Workers are processing jobs...")
        click.echo("  Press Ctrl+C to stop workers gracefully")
        click.echo("")
        
        # Keep main thread alive and handle Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass  # Let the except block below handle it
            
    except KeyboardInterrupt:
        click.echo("\n⚠ Stopping workers gracefully...")
        worker_manager.stop_workers()
        click.echo("✓ All workers stopped")
        sys.exit(0)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@worker.command()
def stop():
    """
    Stop all running workers gracefully.
    
    Workers will finish their current jobs before stopping.
    """
    try:
        worker_manager.stop_workers()
        click.echo("✓ All workers stopped")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """
    Show system status and job statistics.
    
    Displays:
    - Job counts by state
    - Active worker count
    - Current configuration
    """
    try:
        stats = queue_manager.get_stats()
        worker_stats = worker_manager.get_status()
        
        click.echo("=" * 60)
        click.echo("QueueCTL Status")
        click.echo("=" * 60)
        
        click.echo(f"\n📊 Job Statistics:")
        click.echo(f"  Pending:    {stats['pending']:>5}")
        click.echo(f"  Processing: {stats['processing']:>5}")
        click.echo(f"  Completed:  {stats['completed']:>5}")
        click.echo(f"  Failed:     {stats['failed']:>5}")
        click.echo(f"  Dead (DLQ): {stats['dead']:>5}")
        click.echo(f"  {'─' * 20}")
        click.echo(f"  Total:      {stats['total']:>5}")
        
        click.echo(f"\n👷 Workers:")
        click.echo(f"  Total:      {worker_stats['total']:>5}")
        click.echo(f"  Active:     {worker_stats['active']:>5}")
        click.echo(f"  Busy:       {worker_stats['busy']:>5}")
        click.echo(f"  Idle:       {worker_stats['idle']:>5}")
        
        click.echo(f"\n⚙️  Configuration:")
        click.echo(f"  Max Retries:   {config.get('max_retries')}")
        click.echo(f"  Backoff Base:  {config.get('backoff_base')}")
        click.echo(f"  Job Timeout:   {config.get('job_timeout')}s")
        
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--state', '-s', help='Filter by state (pending, processing, completed, failed, dead)')
@click.option('--limit', '-l', default=10, help='Maximum number of jobs to display', type=int)
def list(state: Optional[str], limit: int):
    """
    List jobs, optionally filtered by state.
    
    Example:
    
        queuectl list
        
        queuectl list --state pending
        
        queuectl list --state completed --limit 20
    """
    try:
        # Validate state if provided
        valid_states = ['pending', 'processing', 'completed', 'failed', 'dead']
        if state and state not in valid_states:
            click.echo(f"❌ Error: Invalid state '{state}'", err=True)
            click.echo(f"   Valid states: {', '.join(valid_states)}", err=True)
            sys.exit(1)
        
        jobs = queue_manager.list_jobs(state=state, limit=limit)
        
        if not jobs:
            click.echo(f"No jobs found{f' with state: {state}' if state else ''}")
            return
        
        # Header
        click.echo(f"\n{'ID':<20} {'State':<12} {'Command':<35} {'Attempts':<10} {'Updated'}")
        click.echo("─" * 110)
        
        # Job rows
        for job in jobs:
            cmd_preview = job.command[:32] + "..." if len(job.command) > 35 else job.command
            updated_short = job.updated_at[:19] if job.updated_at else "N/A"
            click.echo(
                f"{job.id:<20} {job.state:<12} {cmd_preview:<35} "
                f"{job.attempts}/{job.max_retries:<8} {updated_short}"
            )
        
        click.echo(f"\nShowing {len(jobs)} job(s){f' with state: {state}' if state else ''}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def dlq():
    """Manage Dead Letter Queue (DLQ)"""
    pass


@dlq.command(name='list')
@click.option('--limit', '-l', default=10, help='Maximum number of jobs to display', type=int)
def dlq_list(limit: int):
    """
    List jobs in the Dead Letter Queue.
    
    Shows jobs that have exhausted all retry attempts.
    """
    try:
        jobs = queue_manager.list_jobs(state='dead', limit=limit)
        
        if not jobs:
            click.echo("✓ No jobs in Dead Letter Queue")
            return
        
        # Header
        click.echo(f"\n{'ID':<20} {'Command':<45} {'Attempts':<10} {'Error':<30}")
        click.echo("─" * 120)
        
        # Job rows
        for job in jobs:
            cmd_preview = job.command[:42] + "..." if len(job.command) > 45 else job.command
            error_preview = (job.error_message[:27] + "...") if job.error_message and len(job.error_message) > 30 else (job.error_message or "N/A")
            click.echo(
                f"{job.id:<20} {cmd_preview:<45} {job.attempts:<10} {error_preview:<30}"
            )
        
        click.echo(f"\n💀 {len(jobs)} job(s) in Dead Letter Queue")
        click.echo("   Use 'queuectl dlq retry <job-id>' to retry a job")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@dlq.command()
@click.argument('job_id')
def retry(job_id: str):
    """
    Retry a job from the Dead Letter Queue.
    
    Resets the job to pending state with attempt count reset to 0.
    
    Example:
    
        queuectl dlq retry job-123
    """
    try:
        success = queue_manager.retry_dlq_job(job_id)
        
        if success:
            click.echo(f"✓ Job '{job_id}' moved from DLQ back to pending queue")
            click.echo(f"  The job will be processed by the next available worker")
        else:
            click.echo(f"❌ Error: Job '{job_id}' not found in Dead Letter Queue", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group(name='config')
def config_cmd():
    """Manage configuration settings"""
    pass


@config_cmd.command()
@click.argument('key')
@click.argument('value')
def set(key: str, value: str):
    """
    Set a configuration value.
    
    Available keys:
    - max-retries: Maximum number of retry attempts (integer)
    - backoff-base: Base for exponential backoff calculation (float)
    - job-timeout: Job execution timeout in seconds (integer)
    - poll-interval: Worker polling interval in seconds (integer)
    - worker-shutdown-timeout: Worker graceful shutdown timeout (integer)
    
    Example:
    
        queuectl config set max-retries 5
        
        queuectl config set backoff-base 1.5
        
        queuectl config set job-timeout 600
        
        queuectl config set poll-interval 2
        
        queuectl config set worker-shutdown-timeout 15
    """
    try:
        valid_keys = [
            'max-retries', 
            'backoff-base', 
            'job-timeout',
            'poll-interval',
            'worker-shutdown-timeout'
        ]
        
        if key not in valid_keys:
            click.echo(f"❌ Error: Invalid configuration key '{key}'", err=True)
            click.echo(f"   Valid keys: {', '.join(valid_keys)}", err=True)
            sys.exit(1)
        
        # Convert key format (kebab-case to snake_case)
        config_key = key.replace('-', '_')
        
        # Convert value to appropriate type
        try:
            if config_key in ['max_retries', 'job_timeout', 'poll_interval', 'worker_shutdown_timeout']:
                value = int(value)
                if value < 0:
                    raise ValueError("Value must be non-negative")
                if config_key == 'poll_interval' and value < 1:
                    raise ValueError("Poll interval must be at least 1 second")
            elif config_key == 'backoff_base':
                value = float(value)
                if value <= 0:
                    raise ValueError("Value must be positive")
        except ValueError as e:
            click.echo(f"❌ Error: Invalid value for '{key}': {str(e)}", err=True)
            sys.exit(1)
        
        # Save configuration
        config.set(config_key, value)
        click.echo(f"✓ Configuration updated")
        click.echo(f"  {key} = {value}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@config_cmd.command()
def show():
    """
    Show current configuration.
    
    Displays all configuration values and their current settings.
    """
    try:
        click.echo("\n⚙️  Current Configuration:")
        click.echo("─" * 40)
        click.echo(f"  max-retries:   {config.get('max_retries')}")
        click.echo(f"  backoff-base:  {config.get('backoff_base')}")
        click.echo(f"  job-timeout:   {config.get('job_timeout')}s")
        click.echo(f"  poll-interval: {config.get('poll_interval')}s")
        click.echo("─" * 40)
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@config_cmd.command()
def reset():
    """
    Reset configuration to default values.
    
    This will restore all configuration settings to their defaults:
    - max-retries: 3
    - backoff-base: 2.0
    - job-timeout: 300
    """
    try:
        click.confirm('Are you sure you want to reset configuration to defaults?', abort=True)
        config.reset()
        click.echo("✓ Configuration reset to defaults")
        
    except click.Abort:
        click.echo("Cancelled")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()