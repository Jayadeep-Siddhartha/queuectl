# QueueCTL - Background Job Queue System

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade CLI-based background job queue system with support for multiple workers, automatic retries with exponential backoff, and a Dead Letter Queue for permanently failed jobs.

## 🎯 Features

- ✅ **Job Queue Management** - Enqueue, list, and monitor background jobs
- ✅ **Multiple Workers** - Run concurrent workers to process jobs in parallel
- ✅ **Automatic Retries** - Failed jobs retry automatically with exponential backoff
- ✅ **Dead Letter Queue** - Permanently failed jobs moved to DLQ for manual inspection
- ✅ **Persistent Storage** - SQLite database ensures jobs survive restarts
- ✅ **Graceful Shutdown** - Workers finish current jobs before stopping
- ✅ **Thread-Safe** - Prevents duplicate job processing with atomic operations
- ✅ **Configurable** - Adjust retry count and backoff strategy via CLI
- ✅ **Production Ready** - Comprehensive error handling and logging

## 📦 Quick Installation

```bash
# Clone repository
git clone https://github.com/yourusername/queuectl.git
cd queuectl

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install queuectl
pip install -e .

# Verify installation
queuectl --version
```


## 🚀 Quick Start

```bash
# 1. Add a job (simple - no JSON needed!)
queuectl add hello "echo Hello World"

# 2. Start a worker
queuectl worker start --count 1

# 3. Check status (in another terminal)
queuectl status

# 4. List completed jobs
queuectl list --state completed
```

## 💡 Two Ways to Add Jobs

### Method 1: Simple Mode (Recommended) ⭐

No JSON, no backslashes, works everywhere:

```bash
queuectl add <job-id> <command>

# Examples
queuectl add job1 "echo Hello"
queuectl add backup "python backup.py" --max-retries 5
```

### Method 2: Advanced Mode

For advanced use cases:

```bash
# Using options
queuectl enqueue --id job1 --command "echo Hello"

```

## 🔧 Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- git

### Installation Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/queuectl.git
cd queuectl
```

#### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Install QueueCTL

```bash
# Development mode (recommended for testing)
pip install -e .

# OR production install
pip install .
```

#### 5. Verify Installation

```bash
queuectl --version
# Output: queuectl, version 1.0.0

queuectl --help
```

## 📖 Usage

### Basic Workflow

1. **Enqueue jobs** - Add jobs to the queue
2. **Start workers** - Launch worker processes
3. **Monitor** - Check status and logs
4. **Manage DLQ** - Handle failed jobs

### Complete Example

```bash
# Add multiple jobs (simple way)
queuectl add job1 "echo Processing 1"
queuectl add job2 "sleep 2 && echo Processing 2"
queuectl add job3 "echo Processing 3"

# Or using options
queuectl enqueue -i job4 -c "echo Processing 4" -r 5

# Start 2 workers to process in parallel
queuectl worker start --count 2

# In another terminal, monitor progress
queuectl status

# List completed jobs
queuectl list --state completed

# Check for any failed jobs
queuectl dlq list
```

## 📋 Commands

### Job Management

```bash
# Enqueue a job
queuectl enqueue -i <job-id> -c "<command>" -r <retries>

# List jobs
queuectl list                    # All jobs
queuectl list --state pending    # Filter by state
queuectl list --limit 20         # Limit results

# Show system status
queuectl status
```

### Worker Management

```bash
# Start workers
queuectl worker start            # Start 1 worker
queuectl worker start --count 3  # Start 3 workers

# Stop workers (or press Ctrl+C)
queuectl worker stop
```

### Dead Letter Queue

```bash
# List DLQ jobs
queuectl dlq list

# Retry a job from DLQ
queuectl dlq retry <job-id>
```

### Configuration

```bash
# Show configuration
queuectl config show

# Update configuration
queuectl config set max-retries 5
queuectl config set backoff-base 2.0
queuectl config set job-timeout 600

# Reset to defaults
queuectl config reset
```

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                      CLI Interface                       │
│                     (queuectl.cli)                       │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│  Queue Manager  │    │ Worker Manager   │
│                 │◄───┤                  │
│  - Enqueue      │    │  - Start/Stop    │
│  - State Mgmt   │    │  - Execute Jobs  │
│  - Retry Logic  │    │  - Concurrency   │
└────────┬────────┘    └────────┬─────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌────────────────────┐
         │   Storage Layer    │
         │     (SQLite)       │
         │                    │
         │  - Job Data        │
         │  - Thread-Safe     │
         │  - Persistence     │
         └────────────────────┘
```

### Job Lifecycle

```
PENDING → PROCESSING → COMPLETED
                ↓
              FAILED ──┐
                ↑     │ (retry with backoff)
                └─────┘
                  │
                  │ (max retries exceeded)
                  ↓
                DEAD (DLQ)
```
## ⚙️ Configuration

Configuration is stored in `queuectl_config.json`:

```json
{
  "max_retries": 3,
  "backoff_base": 2.0,
  "job_timeout": 300,
  "poll_interval": 1
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_retries` | int | 3 | Maximum retry attempts before moving to DLQ |
| `backoff_base` | float | 2.0 | Base for exponential backoff calculation |
| `job_timeout` | int | 300 | Job execution timeout in seconds |
| `poll_interval` | int | 1 | Worker polling interval in seconds |

### Retry Backoff Formula

```
delay = backoff_base ^ attempts
```

**Example with backoff_base = 2.0:**
- Attempt 1: 2^1 = 2 seconds
- Attempt 2: 2^2 = 4 seconds  
- Attempt 3: 2^3 = 8 seconds


## 🎬 Demo Video

### Watch the full video for demo

<a href="https://drive.google.com/file/d/1vmXMa2RVRkPT1DMT-fcAzufiNe0BNlGr/view?usp=sharing" target="_blank">
  <img src="https://drive.google.com/thumbnail?id=1vmXMa2RVRkPT1DMT-fcAzufiNe0BNlGr" 
       alt="QueueCTL Demo Video" 
       width="600" 
       style="border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
</a>



🎬 **Click the image above** to watch the full demo video.

<p align='center'> Or</p>

<p>
  🎬 <strong><a href="https://drive.google.com/file/d/1vmXMa2RVRkPT1DMT-fcAzufiNe0BNlGr/view?usp=sharing" target="_blank">
  Click here to watch the full demo video</a></strong> 
</p>


The demo video covers:
- Installation and setup  
- Enqueuing and managing jobs  
- Running multiple workers in parallel  
- Monitoring queue and worker status  
- Handling retries with exponential backoff  
- Managing the Dead Letter Queue (DLQ)  
- Updating configuration settings  
- Graceful worker shutdown  




## 🧪 Testing

### Run Test Script

```bash
# Make executable
chmod +x scripts/simple-test.sh

# Run demo
./scripts/simple-test.sh
```

The simple test script demonstrates:
- Job enqueuing
- Worker execution
- Status monitoring
- Failed job handling
- DLQ operations
- Configuration management


```



## 🎯 Design Decisions

### 1. SQLite for Storage
- **Why:** Lightweight, serverless, ACID-compliant
- **Trade-off:** Not suitable for highly distributed systems
- **Scale:** Handles 100s of jobs efficiently

### 2. Threading vs Multiprocessing
- **Chosen:** Threading with proper locks
- **Why:** Simpler IPC, sufficient for I/O-bound operations
- **Note:** For CPU-intensive jobs, consider multiprocessing

### 3. Atomic Job Acquisition
- **Implementation:** SELECT + UPDATE in single transaction
- **Why:** Prevents duplicate processing by multiple workers
- **Result:** Thread-safe concurrent processing

### 4. Exponential Backoff
- **Formula:** `delay = base ^ attempts`
- **Why:** Prevents overwhelming failing services
- **Configurable:** Adjust base for different use cases

### 5. Graceful Shutdown
- **Implementation:** Signal handlers + worker flags
- **Why:** Ensures jobs complete before exit
- **Timeout:** 10 seconds for workers to finish

## 🚧 Limitations & Future Enhancements

### Current Limitations
- Single-node only (no distributed support)
- SQLite write contention at high concurrency (>50 workers)
- No job priorities
- No scheduled/delayed jobs
- No job dependencies

### Planned Features
- [ ] Job priorities (high/normal/low)
- [ ] Scheduled jobs with `run_at` timestamp
- [ ] Job dependencies and workflows
- [ ] Web dashboard for monitoring
- [ ] Metrics and statistics export
- [ ] Job output logging and capture
- [ ] Batch job operations
- [ ] PostgreSQL support for scale

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 👤 Author

**Jayadeep Siddhartha**  
Backend Developer Internship Assignment  
[GitHub](https://github.com/Jayadeep-Siddhartha) 

## 🙏 Acknowledgments

Built as part of the QueueCTL Backend Developer Internship Assignment.

**Last Updated:** November 2025  
**Version:** 1.0.0