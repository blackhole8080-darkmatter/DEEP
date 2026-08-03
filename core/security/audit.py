"""
core/security/audit.py

Security audit logging for DEEP.
Tracks all security-relevant events in tamper-resistant format.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class AuditEventType(Enum):
    """Types of audit events."""
    AUTH = "auth"               # Authentication attempts
    CHAT = "chat"               # Chat messages
    TOOL = "tool"               # Tool executions
    SYSTEM = "system"           # System changes
    DATA = "data"               # Data access/modification
    SECURITY = "security"       # Security events


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """A single audit event."""
    timestamp: float
    event_type: str
    user: str
    action: str
    success: bool
    details: Dict[str, Any]
    severity: str
    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, separators=(',', ':'))


class AuditLogger:
    """
    Security audit logger with integrity protection.
    
    Features:
    - Append-only log (tamper detection)
    - Cryptographic integrity (HMAC chain)
    - Structured JSON format
    - Separate from application logs
    """
    
    def __init__(
        self,
        log_dir: str = "logs",
        secret_key: Optional[str] = None
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Audit log file
        self.log_file = self.log_dir / "audit.log"
        
        # Secret for HMAC (prevents tampering)
        self._secret = secret_key or os.environ.get(
            "DEEP_AUDIT_SECRET",
            "default-secret-change-in-production"
        )
        
        # Previous hash for chain integrity
        self._previous_hash: Optional[str] = None
        
        # Load previous hash if log exists
        self._load_previous_hash()
    
    def _load_previous_hash(self):
        """Load the last entry's hash for chain continuity."""
        if not self.log_file.exists():
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    # Get last line
                    last_line = lines[-1].strip()
                    if last_line:
                        entry = json.loads(last_line)
                        self._previous_hash = entry.get("hash")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not load previous audit hash: {e}")
    
    def _compute_hash(self, event: AuditEvent) -> str:
        """Compute HMAC hash of event for integrity."""
        # Create canonical representation
        data = json.dumps({
            "timestamp": event.timestamp,
            "type": event.event_type,
            "user": event.user,
            "action": event.action,
            "success": event.success,
            "details": event.details,
            "prev_hash": self._previous_hash or "0"
        }, sort_keys=True, separators=(',', ':'))
        
        return hmac.new(
            self._secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:32]  # First 32 chars sufficient
    
    def log(
        self,
        event_type: AuditEventType | str,
        user: str,
        action: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> bool:
        """
        Log an audit event.
        
        Args:
            event_type: Category of event
            user: User identifier
            action: What was done
            success: Whether it succeeded
            details: Additional context
            severity: Importance level
            session_id: Session identifier
            client_ip: Client IP address
        
        Returns:
            True if logged successfully
        """
        # Convert enums if needed
        if isinstance(event_type, AuditEventType):
            event_type = event_type.value
        if isinstance(severity, AuditSeverity):
            severity = severity.value
        
        # Create event
        event = AuditEvent(
            timestamp=time.time(),
            event_type=event_type,
            user=user,
            action=action,
            success=success,
            details=details or {},
            severity=severity,
            session_id=session_id,
            client_ip=client_ip
        )
        
        # Compute hash
        entry_hash = self._compute_hash(event)
        
        # Build entry
        entry = {
            **event.to_dict(),
            "hash": entry_hash,
            "prev_hash": self._previous_hash or "0"
        }
        
        # Write atomically
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, default=str, separators=(',', ':')) + '\n')
                f.flush()
                os.fsync(f.fileno())  # Ensure written to disk
            
            # Update previous hash
            self._previous_hash = entry_hash
            
            return True
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to write audit log: {e}")
            return False
    
    def verify_integrity(self) -> Tuple[bool, int, Optional[str]]:
        """
        Verify the integrity of the audit log.
        
        Returns:
            (is_valid, entry_count, first_invalid_entry)
        """
        if not self.log_file.exists():
            return True, 0, None
        
        prev_hash = "0"
        count = 0
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        return False, count, f"Line {line_num}: Invalid JSON"
                    
                    # Check chain integrity
                    stored_prev = entry.get("prev_hash")
                    if stored_prev != prev_hash:
                        return False, count, f"Line {line_num}: Chain broken"
                    
                    # Verify hash (skip for entries without hash - backward compat)
                    stored_hash = entry.get("hash")
                    if stored_hash:
                        # Recompute hash
                        event = AuditEvent(
                            timestamp=entry["timestamp"],
                            event_type=entry["event_type"],
                            user=entry["user"],
                            action=entry["action"],
                            success=entry["success"],
                            details=entry["details"],
                            severity=entry.get("severity", "info"),
                            session_id=entry.get("session_id"),
                            client_ip=entry.get("client_ip")
                        )
                        
                        old_prev = self._previous_hash
                        self._previous_hash = prev_hash if prev_hash != "0" else None
                        computed = self._compute_hash(event)
                        self._previous_hash = old_prev
                        
                        if computed != stored_hash:
                            return False, count, f"Line {line_num}: Hash mismatch"
                    
                    prev_hash = stored_hash or "0"
                    count += 1
            
            return True, count, None
            
        except Exception as e:
            return False, count, f"Exception: {e}"
    
    def query(
        self,
        event_type: Optional[str] = None,
        user: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> list:
        """
        Query audit log entries.
        
        Note: This is for analysis only - entries are still append-only.
        """
        if not self.log_file.exists():
            return []
        
        results = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                    except:
                        continue
                    
                    # Filter
                    if event_type and entry.get("event_type") != event_type:
                        continue
                    if user and entry.get("user") != user:
                        continue
                    if start_time and entry.get("timestamp", 0) < start_time:
                        continue
                    if end_time and entry.get("timestamp", 0) > end_time:
                        continue
                    
                    results.append(entry)
                    
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Query failed: {e}")
            return []


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit(
    event_type: AuditEventType | str,
    user: str,
    action: str,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    **kwargs
) -> bool:
    """
    Convenience function for audit logging.
    
    Example:
        audit(AuditEventType.AUTH, "user123", "login", success=True)
        audit("chat", "user123", "send_message", details={"tokens": 150})
    """
    logger = get_audit_logger()
    return logger.log(
        event_type=event_type,
        user=user,
        action=action,
        success=success,
        details=details,
        severity=severity,
        **kwargs
    )


# For backward compatibility
from typing import Tuple
