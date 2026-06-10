"""
core/logging_config.py

Centralized logging configuration with rotation and structured formatting.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    log_dir: str = "logs",
    console_level: int = logging.WARNING,
    file_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Setup comprehensive logging with rotation.
    
    Creates:
    - deep.log (rotating, main application log)
    - audit.log (security/audit events, append-only)
    - error.log (errors only, for quick debugging)
    """
    
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    
    json_formatter = logging.Formatter(
        fmt='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    
    # 1. Main rotating file handler (deep.log)
    main_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "deep.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    main_handler.setLevel(file_level)
    main_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_handler)
    
    # 2. Error-only file handler (error.log)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "error.log",
        maxBytes=max_bytes // 2,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # 3. Audit log (security events, append-only mode)
    audit_handler = logging.FileHandler(
        filename=log_path / "audit.log",
        mode="a",
        encoding="utf-8"
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(json_formatter)
    
    # Create audit logger
    audit_logger = logging.getLogger("deep.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False  # Don't duplicate to root
    
    # 4. Console handler (only warnings and above to reduce noise)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    _suppress_noisy_loggers()
    
    # Log startup
    deep_logger = logging.getLogger("DEEP")
    deep_logger.info(f"Logging initialized | Dir: {log_path.absolute()}")
    deep_logger.info(f"Log rotation: {max_bytes // (1024*1024)}MB per file, {backup_count} backups")
    
    return deep_logger


def _suppress_noisy_loggers():
    """Reduce noise from common third-party libraries."""
    noisy_loggers = [
        "sentence_transformers",
        "transformers",
        "huggingface_hub",
        "chromadb",
        "urllib3",
        "httpx",
        "httpcore",
        "asyncio",
    ]
    
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_audit_logger() -> logging.Logger:
    """Get the security audit logger."""
    return logging.getLogger("deep.audit")


def audit_event(
    event_type: str,
    user: str,
    action: str,
    details: Optional[dict] = None,
    success: bool = True
):
    """
    Log a security audit event.
    
    Args:
        event_type: Category (auth, tool, data, system)
        user: User identifier
        action: What was attempted
        details: Additional context
        success: Whether the action succeeded
    """
    logger = get_audit_logger()
    
    event_data = {
        "event_type": event_type,
        "user": user,
        "action": action,
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if details:
        event_data["details"] = details
    
    # Format as JSON for structured logging
    import json
    logger.info(json.dumps(event_data, default=str))


class ContextFilter(logging.Filter):
    """Add request/session context to log records."""
    
    def __init__(self):
        super().__init__()
        self.context = {}
    
    def set_context(self, **kwargs):
        """Set context values for current thread."""
        import threading
        tid = threading.current_thread().ident
        self.context[tid] = kwargs
    
    def filter(self, record):
        import threading
        tid = threading.current_thread().ident
        ctx = self.context.get(tid, {})
        
        for key, value in ctx.items():
            setattr(record, key, value)
        
        return True
