"""Application metrics and telemetry system for Git Worktree Manager."""

import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetricEvent:
    """Represents a single metric event."""
    timestamp: str
    event_type: str
    data: Dict[str, Any]
    session_id: str
    user_id: str


@dataclass
class PerformanceBenchmark:
    """Performance benchmark data."""
    operation: str
    duration_ms: float
    timestamp: str
    success: bool
    error_type: Optional[str] = None


@dataclass
class SessionMetrics:
    """Session-level metrics."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    worktree_operations: int = 0
    terminal_sessions: int = 0
    errors_count: int = 0
    git_commands: int = 0


class MetricsCollector:
    """Centralized metrics collection and storage system."""
    
    def __init__(self, config_dir: Path, enable_telemetry: bool = False):
        """Initialize metrics collector.
        
        Args:
            config_dir: Directory to store metrics files
            enable_telemetry: Whether to enable anonymous telemetry
        """
        self.config_dir = config_dir
        self.metrics_dir = config_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.enable_telemetry = enable_telemetry
        self.session_id = str(uuid.uuid4())
        self.user_id = self._get_or_create_user_id()
        
        # Current session metrics
        self.current_session = SessionMetrics(
            session_id=self.session_id,
            start_time=datetime.now().isoformat()
        )
        
        # Performance tracking
        self.performance_benchmarks: List[PerformanceBenchmark] = []
        self._operation_timers: Dict[str, float] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Metrics files
        self.events_file = self.metrics_dir / "events.jsonl"
        self.sessions_file = self.metrics_dir / "sessions.json"
        self.performance_file = self.metrics_dir / "performance.json"
        self.config_file = self.metrics_dir / "config.json"
        
        # Load existing configuration
        self._load_config()
        
        logger.info(f"Metrics collector initialized (session: {self.session_id[:8]})")

    def _get_or_create_user_id(self) -> str:
        """Get or create anonymous user ID."""
        user_id_file = self.metrics_dir / "user_id"
        
        if user_id_file.exists():
            try:
                return user_id_file.read_text().strip()
            except Exception as e:
                logger.warning(f"Failed to read user ID: {e}")
        
        # Create new anonymous user ID
        user_id = str(uuid.uuid4())
        try:
            user_id_file.write_text(user_id)
            logger.debug(f"Created new anonymous user ID: {user_id[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to save user ID: {e}")
        
        return user_id

    def _load_config(self):
        """Load metrics configuration."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.enable_telemetry = config.get('enable_telemetry', False)
                    logger.debug("Loaded metrics configuration")
        except Exception as e:
            logger.warning(f"Failed to load metrics config: {e}")

    def _save_config(self):
        """Save metrics configuration."""
        try:
            config = {
                'enable_telemetry': self.enable_telemetry,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save metrics config: {e}")

    def set_telemetry_enabled(self, enabled: bool):
        """Enable or disable telemetry with user consent."""
        self.enable_telemetry = enabled
        self._save_config()
        logger.info(f"Telemetry {'enabled' if enabled else 'disabled'}")

    def record_event(self, event_type: str, data: Dict[str, Any]):
        """Record a metric event.
        
        Args:
            event_type: Type of event (e.g., 'startup', 'worktree_create', 'error')
            data: Event-specific data
        """
        if not self.enable_telemetry:
            return
            
        with self._lock:
            try:
                event = MetricEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type=event_type,
                    data=data,
                    session_id=self.session_id,
                    user_id=self.user_id
                )
                
                # Append to events file (JSONL format)
                with open(self.events_file, 'a') as f:
                    f.write(json.dumps(asdict(event)) + '\n')
                
                logger.debug(f"Recorded event: {event_type}")
                
            except Exception as e:
                logger.warning(f"Failed to record event {event_type}: {e}")

    def record_startup(self, startup_time_ms: float):
        """Record application startup metrics."""
        self.record_event('startup', {
            'startup_time_ms': startup_time_ms,
            'python_version': self._get_python_version(),
            'platform': self._get_platform_info()
        })

    def record_worktree_operation(self, operation: str, success: bool, duration_ms: float, error: Optional[str] = None):
        """Record worktree operation metrics."""
        self.current_session.worktree_operations += 1
        
        self.record_event('worktree_operation', {
            'operation': operation,
            'success': success,
            'duration_ms': duration_ms,
            'error': error
        })
        
        # Record performance benchmark
        self.record_performance(operation, duration_ms, success, error)

    def record_terminal_session(self, duration_seconds: float, command_count: int):
        """Record terminal session metrics."""
        self.current_session.terminal_sessions += 1
        
        self.record_event('terminal_session', {
            'duration_seconds': duration_seconds,
            'command_count': command_count
        })

    def record_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Record error metrics."""
        self.current_session.errors_count += 1
        
        self.record_event('error', {
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        })

    def record_git_command(self, command: List[str], success: bool, duration_ms: float):
        """Record Git command execution metrics."""
        self.current_session.git_commands += 1
        
        self.record_event('git_command', {
            'command': command[0] if command else 'unknown',
            'success': success,
            'duration_ms': duration_ms
        })

    def record_performance(self, operation: str, duration_ms: float, success: bool, error_type: Optional[str] = None):
        """Record performance benchmark."""
        benchmark = PerformanceBenchmark(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat(),
            success=success,
            error_type=error_type
        )
        
        with self._lock:
            self.performance_benchmarks.append(benchmark)
            
            # Save performance data periodically
            if len(self.performance_benchmarks) % 10 == 0:
                self._save_performance_data()

    @contextmanager
    def time_operation(self, operation_name: str):
        """Context manager for timing operations.
        
        Usage:
            with metrics.time_operation('git_clone'):
                # perform operation
                pass
        """
        start_time = time.time()
        success = True
        error_type = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_type = type(e).__name__
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_performance(operation_name, duration_ms, success, error_type)

    def start_operation_timer(self, operation_name: str):
        """Start timing an operation."""
        self._operation_timers[operation_name] = time.time()

    def end_operation_timer(self, operation_name: str, success: bool = True, error_type: Optional[str] = None):
        """End timing an operation and record the result."""
        if operation_name not in self._operation_timers:
            logger.warning(f"No timer found for operation: {operation_name}")
            return
        
        start_time = self._operation_timers.pop(operation_name)
        duration_ms = (time.time() - start_time) * 1000
        self.record_performance(operation_name, duration_ms, success, error_type)

    def finalize_session(self):
        """Finalize current session and save metrics."""
        self.current_session.end_time = datetime.now().isoformat()
        
        if self.current_session.start_time:
            start_dt = datetime.fromisoformat(self.current_session.start_time)
            end_dt = datetime.fromisoformat(self.current_session.end_time)
            self.current_session.duration_seconds = (end_dt - start_dt).total_seconds()
        
        self._save_session_data()
        self._save_performance_data()
        self._rotate_old_files()
        
        logger.info(f"Session finalized: {self.current_session.duration_seconds:.1f}s, "
                   f"{self.current_session.worktree_operations} worktree ops, "
                   f"{self.current_session.errors_count} errors")

    def _save_session_data(self):
        """Save session data to file."""
        try:
            sessions = []
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r') as f:
                    sessions = json.load(f)
            
            sessions.append(asdict(self.current_session))
            
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save session data: {e}")

    def _save_performance_data(self):
        """Save performance benchmarks to file."""
        try:
            with open(self.performance_file, 'w') as f:
                json.dump([asdict(b) for b in self.performance_benchmarks], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save performance data: {e}")

    def _rotate_old_files(self):
        """Rotate old metrics files to prevent disk space issues."""
        try:
            # Rotate files older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for file_path in self.metrics_dir.glob("*.json*"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    archive_name = f"{file_path.name}.{int(cutoff_date.timestamp())}"
                    archive_path = self.metrics_dir / "archive" / archive_name
                    archive_path.parent.mkdir(exist_ok=True)
                    file_path.rename(archive_path)
                    logger.debug(f"Archived old metrics file: {file_path.name}")
                    
        except Exception as e:
            logger.warning(f"Failed to rotate metrics files: {e}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        try:
            summary = {
                'current_session': asdict(self.current_session),
                'performance_benchmarks_count': len(self.performance_benchmarks),
                'telemetry_enabled': self.enable_telemetry,
                'user_id': self.user_id[:8] + "..." if self.user_id else None,
                'session_id': self.session_id[:8] + "..."
            }
            
            # Add performance statistics
            if self.performance_benchmarks:
                durations = [b.duration_ms for b in self.performance_benchmarks if b.success]
                if durations:
                    summary['performance_stats'] = {
                        'avg_duration_ms': sum(durations) / len(durations),
                        'min_duration_ms': min(durations),
                        'max_duration_ms': max(durations),
                        'success_rate': len([b for b in self.performance_benchmarks if b.success]) / len(self.performance_benchmarks)
                    }
            
            return summary
            
        except Exception as e:
            logger.warning(f"Failed to generate metrics summary: {e}")
            return {}

    def _get_python_version(self) -> str:
        """Get Python version information."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_platform_info(self) -> Dict[str, str]:
        """Get platform information."""
        import platform
        return {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine()
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def initialize_metrics(config_dir: Path, enable_telemetry: bool = False) -> MetricsCollector:
    """Initialize global metrics collector."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(config_dir, enable_telemetry)
    return _metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance."""
    return _metrics_collector


def finalize_metrics():
    """Finalize metrics collection."""
    if _metrics_collector:
        _metrics_collector.finalize_session()


# Convenience functions for common metrics
def record_startup_time(startup_time_ms: float):
    """Record application startup time."""
    if _metrics_collector:
        _metrics_collector.record_startup(startup_time_ms)


def record_worktree_operation(operation: str, success: bool, duration_ms: float, error: Optional[str] = None):
    """Record worktree operation."""
    if _metrics_collector:
        _metrics_collector.record_worktree_operation(operation, success, duration_ms, error)


def record_error(error_type: str, error_message: str, context: Dict[str, Any] = None):
    """Record an error."""
    if _metrics_collector:
        _metrics_collector.record_error(error_type, error_message, context)


def time_operation(operation_name: str):
    """Context manager for timing operations."""
    if _metrics_collector:
        return _metrics_collector.time_operation(operation_name)
    else:
        # Return a no-op context manager if metrics not initialized
        from contextlib import nullcontext
        return nullcontext()
