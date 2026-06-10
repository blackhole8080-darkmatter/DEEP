"""
core/security/input_validator.py

Input validation and sanitization for security.
Prevents injection attacks and prompt injection.
"""

from __future__ import annotations

import re
import html
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    INFO = "info"           # Just info, no action needed
    WARNING = "warning"     # Suspicious but allowed
    BLOCKED = "blocked"     # Rejected


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    sanitized: str
    severity: ValidationSeverity
    message: str
    detected_issues: List[str]


class InputValidator:
    """
    Validates and sanitizes user inputs.
    
    Protects against:
    - Prompt injection attacks
    - HTML/script injection
    - Command injection attempts
    - Excessive length attacks
    """
    
    # Patterns that suggest prompt injection attempts
    _INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous\s+)?instruction",
        r"forget\s+(all\s+)?(previous\s+)?(prompt|instruction)",
        r"disregard\s+(all\s+)?(previous\s+)?(prompt|instruction)",
        r"you\s+are\s+now\s+",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"user\s*:\s*",
        r"new\s+role\s*:",
        r"prompt\s*:\s*",
        r"instruction\s*:\s*",
        r"</?system>",
        r"</?instruction>",
    ]
    
    # Patterns suggesting code/command injection
    _DANGEROUS_PATTERNS = [
        r"os\.system\s*\(",
        r"subprocess\.call\s*\(",
        r"subprocess\.run\s*\(",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
        r"import\s+os\s*;",
        r"import\s+subprocess\s*;",
        r"rm\s+-rf\s+/",
        r"del\s+/[sf]",
        r"format\s*[:\"']",
        r"f\"" + r"\s*\{.*os\.",
    ]
    
    # Maximum lengths
    MAX_INPUT_LENGTH = 10000
    MAX_LINE_LENGTH = 500
    MAX_LINES = 200
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self._injection_regex = [re.compile(p, re.IGNORECASE) for p in self._INJECTION_PATTERNS]
        self._dangerous_regex = [re.compile(p, re.IGNORECASE) for p in self._DANGEROUS_PATTERNS]
    
    def validate(
        self,
        text: str,
        allow_html: bool = False,
        max_length: Optional[int] = None
    ) -> ValidationResult:
        """
        Validate and sanitize input text.
        
        Args:
            text: Raw user input
            allow_html: If False, HTML tags will be escaped
            max_length: Maximum allowed length (default: MAX_INPUT_LENGTH)
        
        Returns:
            ValidationResult with sanitized text and validation status
        """
        issues = []
        
        # Check None/empty
        if not text:
            return ValidationResult(
                is_valid=True,
                sanitized="",
                severity=ValidationSeverity.INFO,
                message="Empty input",
                detected_issues=[]
            )
        
        # Length check
        max_len = max_length or self.MAX_INPUT_LENGTH
        if len(text) > max_len:
            issues.append(f"Input exceeds maximum length ({len(text)} > {max_len})")
            text = text[:max_len]
        
        # Line count check
        lines = text.split('\n')
        if len(lines) > self.MAX_LINES:
            issues.append(f"Too many lines ({len(lines)} > {self.MAX_LINES})")
            text = '\n'.join(lines[:self.MAX_LINES])
        
        # Line length check
        for i, line in enumerate(lines):
            if len(line) > self.MAX_LINE_LENGTH:
                issues.append(f"Line {i+1} exceeds max length")
                lines[i] = line[:self.MAX_LINE_LENGTH]
        
        # Check for injection attempts
        injection_found = self._check_injection(text)
        if injection_found:
            issues.append(f"Potential prompt injection detected: {injection_found}")
        
        # Check for dangerous patterns
        dangerous_found = self._check_dangerous(text)
        if dangerous_found:
            issues.append(f"Potentially dangerous pattern: {dangerous_found}")
        
        # Determine severity and validity
        if dangerous_found and self.strict:
            return ValidationResult(
                is_valid=False,
                sanitized="",
                severity=ValidationSeverity.BLOCKED,
                message="Input blocked: dangerous pattern detected",
                detected_issues=issues
            )
        
        if injection_found and self.strict:
            return ValidationResult(
                is_valid=False,
                sanitized="",
                severity=ValidationSeverity.BLOCKED,
                message="Input blocked: injection attempt detected",
                detected_issues=issues
            )
        
        # Sanitize
        sanitized = self._sanitize(text, allow_html)
        
        # Determine overall severity
        if issues:
            if injection_found or dangerous_found:
                severity = ValidationSeverity.WARNING
            else:
                severity = ValidationSeverity.INFO
        else:
            severity = ValidationSeverity.INFO
        
        return ValidationResult(
            is_valid=True,
            sanitized=sanitized,
            severity=severity,
            message="Input accepted" + (f" with {len(issues)} warnings" if issues else ""),
            detected_issues=issues
        )
    
    def _check_injection(self, text: str) -> Optional[str]:
        """Check for prompt injection patterns."""
        for pattern in self._injection_regex:
            match = pattern.search(text)
            if match:
                return match.group(0)[:50]  # Return matched text (truncated)
        return None
    
    def _check_dangerous(self, text: str) -> Optional[str]:
        """Check for dangerous code patterns."""
        for pattern in self._dangerous_regex:
            match = pattern.search(text)
            if match:
                return match.group(0)[:50]
        return None
    
    def _sanitize(self, text: str, allow_html: bool) -> str:
        """Sanitize text."""
        if not allow_html:
            # Escape HTML
            text = html.escape(text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove control characters except newlines and tabs
        text = ''.join(c for c in text if c == '\n' or c == '\t' or ord(c) >= 32)
        
        return text
    
    def validate_tool_arguments(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate tool arguments.
        
        Prevents:
        - Path traversal in file operations
        - Command injection in shell commands
        """
        issues = []
        
        # Check for path traversal
        for key, value in args.items():
            if isinstance(value, str):
                # Path traversal check
                if '..' in value or '~' in value:
                    issues.append(f"Potential path traversal in '{key}': {value[:50]}")
                
                # Shell metacharacter check for certain tools
                if tool_name in ['run_shell', 'execute_command', 'open']:
                    dangerous_chars = [';', '&', '|', '`', '$', '<', '>']
                    if any(c in value for c in dangerous_chars):
                        issues.append(f"Shell metacharacters in '{key}': {value[:50]}")
        
        if issues:
            return ValidationResult(
                is_valid=False,
                sanitized="",
                severity=ValidationSeverity.BLOCKED,
                message="Tool arguments blocked",
                detected_issues=issues
            )
        
        return ValidationResult(
            is_valid=True,
            sanitized="",
            severity=ValidationSeverity.INFO,
            message="Tool arguments valid",
            detected_issues=[]
        )


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    Tracks requests per client and enposes limits.
    """
    
    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict]:
        """
        Check if request is allowed for client.
        
        Returns:
            (allowed, metadata)
        """
        now = time.time()
        
        # Clean old entries
        if client_id in self._requests:
            self._requests[client_id] = [
                t for t in self._requests[client_id]
                if now - t < self.window_seconds
            ]
        else:
            self._requests[client_id] = []
        
        # Check limit
        current_count = len(self._requests[client_id])
        
        if current_count >= self.max_requests:
            oldest = min(self._requests[client_id])
            reset_in = int(self.window_seconds - (now - oldest))
            
            return False, {
                "limit": self.max_requests,
                "remaining": 0,
                "reset_in_seconds": reset_in,
                "window": self.window_seconds
            }
        
        # Record this request
        self._requests[client_id].append(now)
        
        return True, {
            "limit": self.max_requests,
            "remaining": self.max_requests - current_count - 1,
            "reset_in_seconds": self.window_seconds,
            "window": self.window_seconds
        }
    
    def reset(self, client_id: str):
        """Reset counter for a client."""
        self._requests.pop(client_id, None)


# Global validator instance
_validator: Optional[InputValidator] = None
_rate_limiter: Optional[RateLimiter] = None


def get_validator(strict: bool = False) -> InputValidator:
    """Get global input validator."""
    global _validator
    if _validator is None:
        _validator = InputValidator(strict=strict)
    return _validator


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def validate_input(text: str, strict: bool = False) -> ValidationResult:
    """Quick function to validate input."""
    return get_validator(strict).validate(text)


# Import time for rate limiter
import time
