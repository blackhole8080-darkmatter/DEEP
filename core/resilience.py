"""
core/resilience.py

Circuit breaker pattern, timeouts, and retry logic for resilient operations.
Prevents cascade failures when external services (Ollama, APIs) are down.
"""

from __future__ import annotations

import asyncio
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional, TypeVar
from dataclasses import dataclass
from functools import wraps
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 3          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds before attempting recovery
    half_open_max_calls: int = 1        # Test calls in half-open state
    success_threshold: int = 2          # Successes needed to close
    
    # Timeout settings
    timeout_seconds: float = 30.0       # Default timeout for calls
    
    # Retry settings
    max_retries: int = 2
    retry_delay: float = 1.0
    retry_backoff: float = 2.0          # Exponential backoff multiplier


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Too many failures, calls rejected immediately
    - HALF_OPEN: Testing if service recovered after timeout
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        
        # Thread-safe state management
        self._lock = threading.RLock()
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Raises:
            CircuitBreakerOpen: If circuit is open
            TimeoutError: If call exceeds timeout
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(f"[{self.name}] Circuit entering HALF_OPEN state")
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit [{self.name}] is OPEN. Last failure: "
                        f"{self._time_since_last_failure():.1f}s ago"
                    )
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpen(
                        f"Circuit [{self.name}] HALF_OPEN limit reached"
                    )
                self._half_open_calls += 1
        
        # Execute the call outside the lock
        try:
            result = self._execute_with_timeout(func, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Async version of call."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(f"[{self.name}] Circuit entering HALF_OPEN state")
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit [{self.name}] is OPEN"
                    )
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpen(
                        f"Circuit [{self.name}] HALF_OPEN limit reached"
                    )
                self._half_open_calls += 1
        
        try:
            result = await self._execute_with_timeout_async(func, *args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise
    
    def _execute_with_timeout(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with timeout using thread-based approach."""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=self.config.timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"Call exceeded timeout of {self.config.timeout_seconds}s"
                )
    
    async def _execute_with_timeout_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute async function with timeout."""
        return await asyncio.wait_for(
            func(*args, **kwargs) if asyncio.iscoroutinefunction(func) 
            else asyncio.to_thread(func, *args, **kwargs),
            timeout=self.config.timeout_seconds
        )
    
    def _on_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    logger.info(f"[{self.name}] Circuit CLOSED (recovered)")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            else:
                # In closed state, just reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
    
    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failed during test, go back to open
                logger.warning(f"[{self.name}] Circuit OPEN (recovery failed)")
                self._state = CircuitState.OPEN
                self._success_count = 0
            elif self._failure_count >= self.config.failure_threshold:
                # Too many failures, open the circuit
                logger.warning(
                    f"[{self.name}] Circuit OPEN after {self._failure_count} failures"
                )
                self._state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        if self._last_failure_time is None:
            return True
        return (time.time() - self._last_failure_time) >= self.config.recovery_timeout
    
    def _time_since_last_failure(self) -> float:
        """Get seconds since last failure."""
        if self._last_failure_time is None:
            return float('inf')
        return time.time() - self._last_failure_time
    
    def force_reset(self):
        """Manually reset circuit to CLOSED state."""
        with self._lock:
            logger.info(f"[{self.name}] Circuit manually reset to CLOSED")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class ResilientLLMClient:
    """
    Wrapper for LLM clients with circuit breaker, retry, and timeout protection.
    """
    
    def __init__(self, client_name: str, config: Optional[CircuitBreakerConfig] = None):
        self.client_name = client_name
        self.breaker = CircuitBreaker(client_name, config)
        self.config = config or CircuitBreakerConfig()
    
    def call_with_retry(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Call with circuit breaker + retry logic.
        
        Attempts:
        1. Try with circuit breaker
        2. If fails, retry with exponential backoff
        3. If all retries fail, raise last exception
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return self.breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpen:
                # Circuit is open, don't retry - fail fast
                raise
            except (TimeoutError, ConnectionError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    logger.warning(
                        f"[{self.client_name}] Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            except Exception as e:
                # Other exceptions - don't retry
                raise
        
        # All retries exhausted
        raise last_exception or RuntimeError(f"All {self.config.max_retries} retries failed")
    
    async def call_with_retry_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Async version with retry."""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await self.breaker.call_async(func, *args, **kwargs)
            except CircuitBreakerOpen:
                raise
            except (TimeoutError, ConnectionError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    logger.warning(
                        f"[{self.client_name}] Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
            except Exception:
                raise
        
        raise last_exception or RuntimeError(f"All {self.config.max_retries} retries failed")


def with_timeout(seconds: float):
    """Decorator for adding timeout to functions."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"Function exceeded timeout of {seconds}s")
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await asyncio.wait_for(
                func(*args, **kwargs) if asyncio.iscoroutinefunction(func)
                else asyncio.to_thread(func, *args, **kwargs),
                timeout=seconds
            )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator for adding circuit breaker to functions."""
    breaker = CircuitBreaker(name, config)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await breaker.call_async(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


# Global circuit breakers for common services
_ollama_breaker = CircuitBreaker("ollama", CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30.0,  # Faster recovery for local service
    timeout_seconds=60.0
))

_claude_breaker = CircuitBreaker("claude", CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0,
    timeout_seconds=30.0
))

_chroma_breaker = CircuitBreaker("chromadb", CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30.0,
    timeout_seconds=10.0
))


def get_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get a global circuit breaker by name."""
    breakers = {
        "ollama": _ollama_breaker,
        "claude": _claude_breaker,
        "chromadb": _chroma_breaker,
    }
    return breakers.get(name)
