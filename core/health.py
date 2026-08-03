"""
core/health.py

Health check system for DEEP.
Provides component status monitoring and system diagnostics.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Callable, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    name: str
    status: ComponentStatus
    latency_ms: float = 0.0
    message: str = ""
    last_check: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Centralized health monitoring for all DEEP components."""
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], ComponentHealth]] = {}
        self._cache: Dict[str, ComponentHealth] = {}
        self._cache_ttl = 5.0  # seconds
        self._last_check: Dict[str, float] = {}
    
    def register(self, name: str, check_fn: Callable[[], ComponentHealth]) -> None:
        """Register a component health check."""
        self._checks[name] = check_fn
        logger.info(f"Registered health check: {name}")
    
    async def check_all(self) -> Dict[str, ComponentHealth]:
        """Run all health checks concurrently."""
        now = time.time()
        
        # Check cache first
        results = {}
        to_check = []
        
        for name, check_fn in self._checks.items():
            last = self._last_check.get(name, 0)
            if now - last < self._cache_ttl and name in self._cache:
                results[name] = self._cache[name]
            else:
                to_check.append((name, check_fn))
        
        # Run checks concurrently
        if to_check:
            async def run_check(name_fn):
                name, fn = name_fn
                try:
                    start = time.time()
                    # Run sync function in thread pool
                    health = await asyncio.get_event_loop().run_in_executor(None, fn)
                    health.latency_ms = (time.time() - start) * 1000
                    health.last_check = time.time()
                    return name, health
                except Exception as e:
                    return name, ComponentHealth(
                        name=name,
                        status=ComponentStatus.FAILED,
                        message=f"Health check error: {e}",
                        latency_ms=0,
                        last_check=time.time()
                    )
            
            check_results = await asyncio.gather(
                *[run_check(item) for item in to_check],
                return_exceptions=True
            )
            
            for result in check_results:
                if isinstance(result, Exception):
                    logger.error(f"Health check failed with exception: {result}")
                    continue
                name, health = result
                self._cache[name] = health
                self._last_check[name] = time.time()
                results[name] = health
        
        return results
    
    def get_overall_status(self, results: Dict[str, ComponentHealth]) -> ComponentStatus:
        """Determine overall system status from component results."""
        if not results:
            return ComponentStatus.UNKNOWN
        
        statuses = [h.status for h in results.values()]
        
        if any(s == ComponentStatus.FAILED for s in statuses):
            return ComponentStatus.FAILED
        if any(s == ComponentStatus.DEGRADED for s in statuses):
            return ComponentStatus.DEGRADED
        if all(s == ComponentStatus.OK for s in statuses):
            return ComponentStatus.OK
        
        return ComponentStatus.UNKNOWN
    
    def to_dict(self, results: Dict[str, ComponentHealth]) -> Dict:
        """Convert health results to dictionary for API response."""
        return {
            "status": self.get_overall_status(results).value,
            "timestamp": time.time(),
            "components": {
                name: {
                    "status": h.status.value,
                    "latency_ms": round(h.latency_ms, 2),
                    "message": h.message,
                    "last_check": h.last_check,
                    "metadata": h.metadata
                }
                for name, h in results.items()
            }
        }


# Global health checker instance
_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    return _health_checker


# Pre-built health check functions

def check_ollama(base_url: str = "http://localhost:11434") -> ComponentHealth:
    """Check Ollama connectivity."""
    import requests
    
    start = time.time()
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name") for m in data.get("models", [])]
            return ComponentHealth(
                name="ollama",
                status=ComponentStatus.OK,
                latency_ms=latency,
                message=f"Connected, {len(models)} models available",
                metadata={"models": models[:5]}  # First 5 models
            )
        else:
            return ComponentHealth(
                name="ollama",
                status=ComponentStatus.DEGRADED,
                latency_ms=latency,
                message=f"Unexpected status: {response.status_code}"
            )
    except requests.exceptions.Timeout:
        return ComponentHealth(
            name="ollama",
            status=ComponentStatus.DEGRADED,
            latency_ms=5000,
            message="Connection timeout (5s)"
        )
    except requests.exceptions.ConnectionError:
        return ComponentHealth(
            name="ollama",
            status=ComponentStatus.FAILED,
            latency_ms=0,
            message="Connection refused - is Ollama running?"
        )
    except Exception as e:
        return ComponentHealth(
            name="ollama",
            status=ComponentStatus.FAILED,
            latency_ms=0,
            message=f"Error: {e}"
        )


def check_chroma(chroma_dir: str = "data/chroma") -> ComponentHealth:
    """Check ChromaDB health."""
    import os
    
    try:
        # Check if directory exists and is writable
        if not os.path.exists(chroma_dir):
            return ComponentHealth(
                name="chromadb",
                status=ComponentStatus.FAILED,
                message=f"Directory does not exist: {chroma_dir}"
            )
        
        if not os.access(chroma_dir, os.W_OK):
            return ComponentHealth(
                name="chromadb",
                status=ComponentStatus.DEGRADED,
                message="Directory not writable"
            )
        
        # Try to import and do basic operation
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            start = time.time()
            client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=chroma_dir,
                anonymized_telemetry=False
            ))
            
            # List collections (lightweight operation)
            collections = client.list_collections()
            latency = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="chromadb",
                status=ComponentStatus.OK,
                latency_ms=latency,
                message=f"Connected, {len(collections)} collections",
                metadata={"collection_count": len(collections)}
            )
        except ImportError:
            return ComponentHealth(
                name="chromadb",
                status=ComponentStatus.FAILED,
                message="chromadb not installed"
            )
        except Exception as e:
            return ComponentHealth(
                name="chromadb",
                status=ComponentStatus.DEGRADED,
                message=f"Client error: {e}"
            )
    except Exception as e:
        return ComponentHealth(
            name="chromadb",
            status=ComponentStatus.FAILED,
            message=f"Unexpected error: {e}"
        )


def check_memory_usage() -> ComponentHealth:
    """Check system memory usage."""
    import psutil
    
    try:
        mem = psutil.virtual_memory()
        
        status = ComponentStatus.OK
        message = f"{mem.percent}% used ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)"
        
        if mem.percent > 90:
            status = ComponentStatus.FAILED
            message = f"CRITICAL: {mem.percent}% memory usage"
        elif mem.percent > 75:
            status = ComponentStatus.DEGRADED
            message = f"WARNING: {mem.percent}% memory usage"
        
        return ComponentHealth(
            name="memory",
            status=status,
            message=message,
            metadata={
                "percent": mem.percent,
                "used_gb": mem.used // (1024**3),
                "total_gb": mem.total // (1024**3),
                "available_gb": mem.available // (1024**3)
            }
        )
    except Exception as e:
        return ComponentHealth(
            name="memory",
            status=ComponentStatus.UNKNOWN,
            message=f"Error checking memory: {e}"
        )


def check_disk_space() -> ComponentHealth:
    """Check disk space."""
    import psutil
    import os
    
    try:
        # Check C: drive on Windows, root on Unix
        path = "C:\\" if os.name == "nt" else "/"
        disk = psutil.disk_usage(path)
        
        percent_used = (disk.used / disk.total) * 100
        
        status = ComponentStatus.OK
        message = f"{percent_used:.1f}% used ({disk.free // (1024**3)}GB free)"
        
        if percent_used > 95:
            status = ComponentStatus.FAILED
            message = f"CRITICAL: Only {disk.free // (1024**3)}GB free"
        elif percent_used > 85:
            status = ComponentStatus.DEGRADED
            message = f"WARNING: {percent_used:.1f}% disk usage"
        
        return ComponentHealth(
            name="disk",
            status=status,
            message=message,
            metadata={
                "percent_used": round(percent_used, 1),
                "free_gb": disk.free // (1024**3),
                "total_gb": disk.total // (1024**3)
            }
        )
    except Exception as e:
        return ComponentHealth(
            name="disk",
            status=ComponentStatus.UNKNOWN,
            message=f"Error checking disk: {e}"
        )


# Convenience function to setup all standard checks
def setup_standard_health_checks(settings: Any) -> HealthChecker:
    """Configure health checker with all standard component checks."""
    checker = get_health_checker()
    
    checker.register("ollama", lambda: check_ollama(
        getattr(settings, "ollama_base_url", "http://localhost:11434")
    ))
    checker.register("chromadb", lambda: check_chroma(
        getattr(settings, "chroma_dir", "data/chroma")
    ))
    checker.register("memory", check_memory_usage)
    checker.register("disk", check_disk_space)
    
    return checker
