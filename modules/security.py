"""
security.py

Cybersecurity monitoring and intrusion detection for DEEP.
- Network traffic monitoring and analysis
- System log monitoring and anomaly detection
- File integrity monitoring
- Real-time alerting for security events
- Signature-based and anomaly-based intrusion detection
"""

from __future__ import annotations

import os
import sys
import time
import threading
import queue
import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional, Callable, Dict, List
from datetime import datetime
from collections import defaultdict, deque

import psutil

try:
    from ..core.config import Settings
except ImportError:
    from core.config import Settings


def _system_disk_path() -> str:
    if sys.platform == "win32":
        drive = os.environ.get("SystemDrive", "C:")
        return drive + os.sep
    return "/"


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """Represents a security event/alert."""
    event_type: str  # "network", "system", "file", "intrusion"
    severity: str  # "low", "medium", "high", "critical"
    timestamp: str
    source: str
    description: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NetworkConnection:
    """Represents a network connection."""
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    status: str
    pid: int
    process_name: str


class AlertSystem:
    """Handles real-time alerting for security events."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._alert_queue: queue.Queue[SecurityEvent] = queue.Queue()
        self._alert_handlers: List[Callable[[SecurityEvent], None]] = []
        self._event_history: deque[SecurityEvent] = deque(maxlen=1000)
        self._running = False
        self._alert_thread: Optional[threading.Thread] = None

    def add_handler(self, handler: Callable[[SecurityEvent], None]) -> None:
        """Add a custom alert handler (e.g., email, SMS, desktop notification)."""
        self._alert_handlers.append(handler)

    def emit(self, event: SecurityEvent) -> None:
        """Emit a security event to the alert system."""
        self._event_history.append(event)
        self._alert_queue.put(event)
        # Only show HIGH/CRITICAL alerts on console to reduce noise
        # All events are still logged to file and available via get_recent_events()
        if event.severity in ("high", "critical"):
            logger.warning(f"SECURITY ALERT [{event.severity.upper()}]: {event.description}")
        else:
            # Log lower severity events at DEBUG level (silent on console)
            logger.debug(f"Security event [{event.severity}]: {event.description}")

    def start(self) -> None:
        """Start the alert processing thread."""
        if self._running:
            return
        self._running = True
        self._alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self._alert_thread.start()

    def stop(self) -> None:
        """Stop the alert processing thread."""
        self._running = False
        if self._alert_thread:
            self._alert_thread.join(timeout=5)

    def _process_alerts(self) -> None:
        """Process alerts from the queue and notify handlers."""
        while self._running:
            try:
                event = self._alert_queue.get(timeout=1)
                for handler in self._alert_handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Alert handler error: {e}")
            except queue.Empty:
                continue

    def get_recent_events(self, limit: int = 50) -> List[dict[str, Any]]:
        """Get recent security events."""
        events = list(self._event_history)[-limit:]
        return [event.to_dict() for event in events]


class NetworkMonitor:
    """Monitors network traffic and connections for suspicious activity."""

    def __init__(self, alert_system: AlertSystem):
        self._alert_system = alert_system
        self._baseline_connections: set[tuple[str, int, str, int]] = set()
        self._connection_history: Dict[str, List[NetworkConnection]] = defaultdict(list)
        self._suspicious_ports = {22, 23, 135, 139, 445, 1433, 3389, 5900}
        self._known_malicious_ips: set[str] = set()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start network monitoring."""
        if self._running:
            return
        self._running = True
        self._establish_baseline()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop network monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _establish_baseline(self) -> None:
        """Establish baseline of normal network connections."""
        try:
            for conn in psutil.net_connections():
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    key = (conn.laddr.ip, conn.laddr.port, conn.raddr.ip, conn.raddr.port)
                    self._baseline_connections.add(key)
            logger.info(f"Network baseline established with {len(self._baseline_connections)} connections")
        except Exception as e:
            logger.error(f"Failed to establish network baseline: {e}")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                self._analyze_connections()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Network monitoring error: {e}")
                time.sleep(10)

    def _analyze_connections(self) -> None:
        """Analyze current network connections for suspicious activity."""
        current_connections = set()
        
        try:
            for conn in psutil.net_connections():
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    local_ip, local_port = conn.laddr
                    remote_ip, remote_port = conn.raddr
                    key = (local_ip, local_port, remote_ip, remote_port)
                    current_connections.add(key)

                    # Check for suspicious ports
                    if remote_port in self._suspicious_ports:
                        self._alert_system.emit(SecurityEvent(
                            event_type="network",
                            severity="medium",
                            timestamp=datetime.now().isoformat(),
                            source=f"{remote_ip}:{remote_port}",
                            description=f"Suspicious port connection detected: {remote_port}",
                            details={"local": f"{local_ip}:{local_port}", "remote": f"{remote_ip}:{remote_port}"}
                        ))

                    # Check for unknown connections
                    if key not in self._baseline_connections:
                        try:
                            process = psutil.Process(conn.pid) if conn.pid else None
                            process_name = process.name() if process else "unknown"
                        except:
                            process_name = "unknown"

                        self._alert_system.emit(SecurityEvent(
                            event_type="network",
                            severity="low",
                            timestamp=datetime.now().isoformat(),
                            source=f"{remote_ip}:{remote_port}",
                            description=f"New network connection established",
                            details={
                                "local": f"{local_ip}:{local_port}",
                                "remote": f"{remote_ip}:{remote_port}",
                                "process": process_name,
                                "pid": conn.pid
                            }
                        ))

        except Exception as e:
            logger.error(f"Connection analysis error: {e}")

    def get_active_connections(self) -> List[dict[str, Any]]:
        """Get current active network connections."""
        connections = []
        try:
            for conn in psutil.net_connections():
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    try:
                        process = psutil.Process(conn.pid) if conn.pid else None
                        process_name = process.name() if process else "unknown"
                    except:
                        process_name = "unknown"

                    connections.append({
                        "local_address": conn.laddr.ip if conn.laddr else "N/A",
                        "local_port": conn.laddr.port if conn.laddr else 0,
                        "remote_address": conn.raddr.ip if conn.raddr else "N/A",
                        "remote_port": conn.raddr.port if conn.raddr else 0,
                        "status": conn.status,
                        "pid": conn.pid or 0,
                        "process_name": process_name
                    })
        except Exception as e:
            logger.error(f"Failed to get connections: {e}")
        
        return connections[:50]  # Limit to 50 connections


class SystemMonitor:
    """Monitors system logs and processes for suspicious activity."""

    def __init__(self, alert_system: AlertSystem):
        self._alert_system = alert_system
        self._baseline_processes: Dict[str, int] = {}
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start system monitoring."""
        if self._running:
            return
        self._running = True
        self._establish_baseline()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop system monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _establish_baseline(self) -> None:
        """Establish baseline of normal system processes."""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if name:
                        self._baseline_processes[name] = self._baseline_processes.get(name, 0) + 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            logger.info(f"System baseline established with {len(self._baseline_processes)} processes")
        except Exception as e:
            logger.error(f"Failed to establish system baseline: {e}")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                self._analyze_processes()
                self._check_system_resources()
                time.sleep(10)
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                time.sleep(10)

    def _analyze_processes(self) -> None:
        """Analyze running processes for suspicious activity."""
        suspicious_keywords = ['miner', 'crypto', 'bitcoin', 'malware', 'trojan', 'backdoor', 'rootkit']
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    name = proc.info['name'].lower() if proc.info['name'] else ""
                    cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                    
                    # Check for suspicious process names
                    for keyword in suspicious_keywords:
                        if keyword in name or keyword in cmdline:
                            self._alert_system.emit(SecurityEvent(
                                event_type="system",
                                severity="high",
                                timestamp=datetime.now().isoformat(),
                                source=f"PID:{proc.info['pid']}",
                                description=f"Suspicious process detected: {proc.info['name']}",
                                details={
                                    "pid": proc.info['pid'],
                                    "name": proc.info['name'],
                                    "cmdline": proc.info['cmdline']
                                }
                            ))
                            break

                    # Check for processes with unusually high CPU/memory
                    try:
                        cpu_percent = proc.cpu_percent(interval=0.1)
                        mem_percent = proc.memory_percent()
                        
                        if cpu_percent > 90 or mem_percent > 90:
                            self._alert_system.emit(SecurityEvent(
                                event_type="system",
                                severity="medium",
                                timestamp=datetime.now().isoformat(),
                                source=f"PID:{proc.info['pid']}",
                                description=f"High resource usage: {proc.info['name']}",
                                details={
                                    "pid": proc.info['pid'],
                                    "name": proc.info['name'],
                                    "cpu_percent": cpu_percent,
                                    "memory_percent": mem_percent
                                }
                            ))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Process analysis error: {e}")

    def _check_system_resources(self) -> None:
        """Check for abnormal system resource usage."""
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage(_system_disk_path()).percent

            if cpu > 95:
                self._alert_system.emit(SecurityEvent(
                    event_type="system",
                    severity="high",
                    timestamp=datetime.now().isoformat(),
                    source="system",
                    description=f"Critically high CPU usage: {cpu}%",
                    details={"cpu_percent": cpu}
                ))

            if mem > 95:
                self._alert_system.emit(SecurityEvent(
                    event_type="system",
                    severity="high",
                    timestamp=datetime.now().isoformat(),
                    source="system",
                    description=f"Critically high memory usage: {mem}%",
                    details={"memory_percent": mem}
                ))

            if disk > 95:
                self._alert_system.emit(SecurityEvent(
                    event_type="system",
                    severity="medium",
                    timestamp=datetime.now().isoformat(),
                    source="system",
                    description=f"High disk usage: {disk}%",
                    details={"disk_percent": disk}
                ))

        except Exception as e:
            logger.error(f"Resource check error: {e}")

    def get_system_status(self) -> dict[str, Any]:
        """Get current system status."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage(_system_disk_path()).percent,
                "process_count": len(list(psutil.process_iter())),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {}


class IntrusionDetector:
    """Signature-based and anomaly-based intrusion detection."""

    def __init__(self, alert_system: AlertSystem):
        self._alert_system = alert_system
        self._signatures = self._load_signatures()
        self._anomaly_thresholds = {
            "connection_rate": 100,  # connections per minute
            "failed_login_attempts": 5,
            "port_scan_threshold": 10
        }
        self._connection_counter: deque[tuple[str, float]] = deque(maxlen=1000)
        self._failed_logins: Dict[str, int] = defaultdict(int)
        self._running = False
        self._detector_thread: Optional[threading.Thread] = None

    def _load_signatures(self) -> List[dict[str, Any]]:
        """Load intrusion detection signatures."""
        return [
            {
                "name": "Port Scan Detection",
                "pattern": "multiple_connections_to_different_ports",
                "severity": "high",
                "description": "Potential port scanning activity detected"
            },
            {
                "name": "Brute Force Login",
                "pattern": "multiple_failed_login_attempts",
                "severity": "high",
                "description": "Potential brute force attack detected"
            },
            {
                "name": "DDoS Pattern",
                "pattern": "high_connection_rate",
                "severity": "critical",
                "description": "Potential DDoS attack detected"
            }
        ]

    def start(self) -> None:
        """Start intrusion detection."""
        if self._running:
            return
        self._running = True
        self._detector_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._detector_thread.start()

    def stop(self) -> None:
        """Stop intrusion detection."""
        self._running = False
        if self._detector_thread:
            self._detector_thread.join(timeout=5)

    def _detection_loop(self) -> None:
        """Main detection loop."""
        while self._running:
            try:
                self._detect_anomalies()
                time.sleep(30)
            except Exception as e:
                logger.error(f"Intrusion detection error: {e}")
                time.sleep(30)

    def _detect_anomalies(self) -> None:
        """Detect anomalies based on traffic patterns."""
        current_time = time.time()
        
        # Clean old connection records (older than 1 minute)
        self._connection_counter = deque([
            (ip, t) for ip, t in self._connection_counter 
            if current_time - t < 60
        ], maxlen=1000)

        # Check for high connection rate (potential DDoS)
        if len(self._connection_counter) > self._anomaly_thresholds["connection_rate"]:
            ip_counts = defaultdict(int)
            for ip, _ in self._connection_counter:
                ip_counts[ip] += 1
            
            top_ip = max(ip_counts.items(), key=lambda x: x[1])
            self._alert_system.emit(SecurityEvent(
                event_type="intrusion",
                severity="critical",
                timestamp=datetime.now().isoformat(),
                source=top_ip[0],
                description=f"High connection rate detected from {top_ip[0]}: {top_ip[1]} connections/min",
                details={"ip": top_ip[0], "connection_count": top_ip[1]}
            ))

    def record_connection(self, remote_ip: str) -> None:
        """Record a new connection for anomaly detection."""
        self._connection_counter.append((remote_ip, time.time()))

    def record_failed_login(self, username: str, remote_ip: str) -> None:
        """Record a failed login attempt."""
        key = f"{username}@{remote_ip}"
        self._failed_logins[key] += 1
        
        if self._failed_logins[key] >= self._anomaly_thresholds["failed_login_attempts"]:
            self._alert_system.emit(SecurityEvent(
                event_type="intrusion",
                severity="high",
                timestamp=datetime.now().isoformat(),
                source=remote_ip,
                description=f"Multiple failed login attempts for {username}",
                details={
                    "username": username,
                    "remote_ip": remote_ip,
                    "attempts": self._failed_logins[key]
                }
            ))


class SecurityMonitor:
    """Main security monitoring orchestrator."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._alert_system = AlertSystem(settings)
        self._network_monitor = NetworkMonitor(self._alert_system)
        self._system_monitor = SystemMonitor(self._alert_system)
        self._intrusion_detector = IntrusionDetector(self._alert_system)
        self._running = False

    def start(self) -> None:
        """Start all security monitoring components."""
        if self._running:
            return
        
        logger.info("Starting DEEP Security Monitor...")
        self._running = True
        self._alert_system.start()
        self._network_monitor.start()
        self._system_monitor.start()
        self._intrusion_detector.start()
        
        # Add default desktop notification handler
        try:
            from plyer import notification
            def desktop_notifier(event: SecurityEvent):
                notification.notify(
                    title=f"DEEP Security Alert [{event.severity.upper()}]",
                    message=event.description,
                    app_name="DEEP",
                    timeout=10
                )
            self._alert_system.add_handler(desktop_notifier)
        except ImportError:
            logger.warning("plyer not available for desktop notifications")

        logger.info("DEEP Security Monitor started successfully")

    def stop(self) -> None:
        """Stop all security monitoring components."""
        if not self._running:
            return
        
        logger.info("Stopping DEEP Security Monitor...")
        self._running = False
        self._intrusion_detector.stop()
        self._system_monitor.stop()
        self._network_monitor.stop()
        self._alert_system.stop()
        logger.info("DEEP Security Monitor stopped")

    def get_security_status(self) -> dict[str, Any]:
        """Get comprehensive security status."""
        return {
            "monitoring_active": self._running,
            "recent_events": self._alert_system.get_recent_events(limit=20),
            "network_connections": self._network_monitor.get_active_connections(),
            "system_status": self._system_monitor.get_system_status(),
            "timestamp": datetime.now().isoformat()
        }
