"""
tools.py

System control & utility functions for DEEP.
- Cross-platform process management.
- Dynamic tool routing registry.
- Clear parameter schema hints for local/cloud LLMs.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import subprocess
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Any, Optional

import requests
import psutil
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
try:
    import pyautogui
except ImportError:
    pyautogui = None
try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
except ImportError:
    AudioUtilities = IAudioEndpointVolume = CLSCTX_ALL = None

try:
    from ..core.config import Settings
    from ..core.memory import MemorySystem
    from .security import SecurityMonitor
except ImportError:
    from core.config import Settings
    from core.memory import MemorySystem
    from modules.security import SecurityMonitor

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    content: str

    def to_text(self) -> str:
        return json.dumps({"ok": self.ok, "result": self.content}, ensure_ascii=False)


class ToolBox:
    """Dynamic tool provider interface used by brain.py."""

    def __init__(
        self,
        settings: Settings,
        memory_system: Optional[MemorySystem] = None,
        security_monitor: Optional[SecurityMonitor] = None,
    ) -> None:
        self._settings = settings
        self._memory = memory_system

        base_dir = os.path.abspath(os.path.dirname(__file__))
        self._workspace_root = os.path.join(base_dir, "workspace")
        os.makedirs(self._workspace_root, exist_ok=True)

        self._security_monitor = security_monitor or SecurityMonitor(settings=settings)
        
        # Dynamic tool registry mapping names to execution handlers and system docs
        self._registry: dict[str, dict[str, Any]] = {
            "get_system_status": {
                "func": lambda _: self._get_system_status(),
                "desc": "Retrieves real-time CPU, Memory, and Disk usage metrics. Arguments: none."
            },
            "list_dir": {
                "func": lambda args: self._list_dir(path=str(args.get("path", ""))),
                "desc": "Lists contents of a directory inside the workspace. Args: {'path': 'relative/path'}"
            },
            "read_file": {
                "func": lambda args: self._read_file(path=str(args.get("path", ""))),
                "desc": "Reads content from a file inside the workspace. Args: {'path': 'relative/path'}"
            },
            "write_file": {
                "func": lambda args: self._write_file(path=str(args.get("path", "")), content=str(args.get("content", ""))),
                "desc": "Writes content to a file inside the workspace. Args: {'path': 'relative/path', 'content': 'text content'}"
            },
            "launch_app": {
                "func": lambda args: self._launch_app(path=str(args.get("path", ""))),
                "desc": "Launches a desktop executable application by its file path. Args: {'path': 'C:/Path/app.exe'}"
            },
            "open_browser": {
                "func": lambda args: self._open_browser(url=str(args.get("url", ""))),
                "desc": "Opens a specific URL website address in the default web browser. Args: {'path': 'https://example.com'}"
            },
            "search_web": {
                "func": lambda args: self._search_web(query=str(args.get("query", ""))),
                "desc": "Runs a web search engine query and displays the results in the browser. Args: {'query': 'search terms'}"
            },
            "play_music": {
                "func": lambda args: self._play_music(query=str(args.get("query", ""))),
                "desc": "Searches for and streams audio tracks or videos via YouTube. Args: {'query': 'artist or song'}"
            },
            "get_running_processes": {
                "func": lambda _: self._get_running_processes(),
                "desc": "Lists the currently active system processes. Arguments: none."
            },
            "set_volume": {
                "func": lambda args: self._set_volume(level=int(args.get("level", 50))),
                "desc": "Sets the system master volume level. Args: {'level': 0-100}"
            },
            "set_brightness": {
                "func": lambda args: self._set_brightness(level=int(args.get("level", 50))),
                "desc": "Sets the primary monitor brightness level. Args: {'level': 0-100}"
            },
            "media_control": {
                "func": lambda args: self._media_control(action=str(args.get("action", "playpause"))),
                "desc": "Controls media playback. Args: {'action': 'playpause', 'next', 'prev', 'volumeup', 'volumedown'}"
            },
            "power_control": {
                "func": lambda args: self._power_control(action=str(args.get("action", "lock"))),
                "desc": "Triggers system power state changes. Args: {'action': 'lock', 'sleep', 'shutdown'}"
            },
            "research_web": {
                "func": lambda args: self._research_topic(topic=str(args.get("topic", ""))),
                "desc": "Quick DuckDuckGo search returning top snippet results. Args: {'topic': 'query string'}"
            },
            "fetch_page": {
                "func": lambda args: self._fetch_page(url=str(args.get("url", ""))),
                "desc": "Fetches and reads the full text content of any webpage URL. Args: {'url': 'https://example.com/article'}"
            },
            "deep_search": {
                "func": lambda args: self._deep_search(query=str(args.get("query", "")), num_pages=int(args.get("num_pages", 3))),
                "desc": "Searches DuckDuckGo and READS the top pages for deep research. Args: {'query': 'topic', 'num_pages': 3}"
            },
            "get_weather": {
                "func": lambda args: self._get_weather(location=str(args.get("location", ""))),
                "desc": "Gets current live weather for a city or location. Args: {'location': 'London'}"
            },
            "get_price": {
                "func": lambda args: self._get_price(symbol=str(args.get("symbol", ""))),
                "desc": "Gets live stock or crypto price. Args: {'symbol': 'AAPL' or 'BTC-USD'}"
            },
            "get_ai_news": {
                "func": lambda _: self._get_ai_news(),
                "desc": "Fetches the latest headlines in Artificial Intelligence and Technology. Arguments: none."
            },
            "project_helper": {
                "func": lambda args: self._project_helper(task=str(args.get("task", ""))),
                "desc": "Assists with project building, code explanation, or tool suggestions. Args: {'task': 'how to use FastAPI'}"
            },
            "save_knowledge": {
                "func": lambda args: self._save_knowledge(fact=str(args.get("fact", ""))),
                "desc": "Saves a new fact, research finding, or project note into persistent memory for long-term recall. Args: {'fact': 'summary of learned info'}"
            },
            "get_security_status": {
                "func": lambda _: self._get_security_status(),
                "desc": "Retrieves comprehensive security monitoring status including network connections, system status, and recent security events. Arguments: none."
            },
            "start_security_monitoring": {
                "func": lambda _: self._start_security_monitoring(),
                "desc": "Starts the DEEP security monitoring system to detect cyber threats and intrusions. Arguments: none."
            },
            "stop_security_monitoring": {
                "func": lambda _: self._stop_security_monitoring(),
                "desc": "Stops the DEEP security monitoring system. Arguments: none."
            },
            "get_security_events": {
                "func": lambda args: self._get_security_events(limit=int(args.get("limit", 20))),
                "desc": "Retrieves recent security events and alerts. Args: {'limit': number of events (default: 20)}"
            },
            "get_network_connections": {
                "func": lambda _: self._get_network_connections(),
                "desc": "Retrieves current active network connections for security analysis. Arguments: none."
            },
            "scan_network": {
                "func": lambda _: self._scan_network(),
                "desc": "Scans the local network (LAN) to discover active devices and their IP/MAC addresses. Arguments: none."
            },
            "scan_ports": {
                "func": lambda args: self._scan_ports(target=str(args.get("target", "127.0.0.1"))),
                "desc": "Scans a specific target IP address for common open ports (22, 80, 443, 3389, etc.). Args: {'target': '192.168.1.1'}"
            },
            "audit_system": {
                "func": lambda _: self._audit_system(),
                "desc": "Performs a local security audit including firewall status, suspicious processes, and OS updates. Arguments: none."
            },
            "threat_intel": {
                "func": lambda args: self._threat_intel(query=str(args.get("query", ""))),
                "desc": "Researches specific vulnerabilities, CVEs, or recent cyber threats related to a technology. Args: {'query': 'log4j vulnerability'}"
            },
            # JARVIS News & Automation Tools
            "get_news_briefing": {
                "func": lambda _: self._get_news_briefing(),
                "desc": "Fetches global news briefing covering tech, AI, science, and world news. Perfect for staying informed. Arguments: none."
            },
            "search_news": {
                "func": lambda args: self._search_news(query=str(args.get("query", "")), max_results=int(args.get("max_results", 10))),
                "desc": "Search for specific topics in news. Args: {'query': 'artificial intelligence', 'max_results': 10}"
            },
            "research_topic": {
                "func": lambda args: self._deep_search(query=str(args.get("topic", "")), num_pages=int(args.get("num_pages", 3))),
                "desc": "Deep research: searches DuckDuckGo and reads top pages for a topic. Args: {'topic': 'quantum computing', 'num_pages': 3}"
            },
            "submit_task": {
                "func": lambda args: self._submit_task(task_description=str(args.get("task_description", "")), priority=int(args.get("priority", 5))),
                "desc": "Submit a complex task for autonomous execution. Args: {'task_description': 'Research and summarize...', 'priority': 1-10}"
            },
            "get_task_status": {
                "func": lambda _: self._get_all_tasks(),
                "desc": "Check status of all running and completed tasks. Arguments: none."
            },
            # ---- ML algorithm knowledge base (Layer 1: advise/explain) ----
            "ml_list": {
                "func": lambda _: self._ml_list(),
                "desc": "Lists every machine-learning algorithm Deep knows, grouped by family (supervised, unsupervised, deep learning, reinforcement, optimization). Arguments: none."
            },
            "ml_explain": {
                "func": lambda args: self._ml_explain(query=str(args.get("query", ""))),
                "desc": "Explains one ML algorithm: what it does, when to use it, and the real library to call. Args: {'query': 'xgboost' or 'lstm' or 'dbscan'}"
            },
            "ml_recommend": {
                "func": lambda args: self._ml_recommend(problem=str(args.get("problem", ""))),
                "desc": "Recommends the best ML algorithm(s) for a described problem, ranked, with the library to use. Args: {'problem': 'detect anomalies in network traffic'}"
            },
            # ---- ML execution (Layer 2: actually train/predict via scikit-learn) ----
            "ml_runnable": {
                "func": lambda _: self._ml_runnable(),
                "desc": "Lists which ML algorithms Deep can actually TRAIN/RUN right now (vs advise-only). Arguments: none."
            },
            "ml_train": {
                "func": lambda args: self._ml_train(
                    algorithm=str(args.get("algorithm", "")),
                    data=str(args.get("data", "")),
                    target=str(args.get("target", "")) or None,
                    save_as=str(args.get("save_as", "")) or None,
                    params=args.get("params"),
                ),
                "desc": "Trains a real ML model. data is a workspace CSV path OR an internal source: 'internal:processes' or 'internal:network'. Supervised algos need a target column. Optional params tune the algorithm (e.g. {'n_clusters': 3}). Args: {'algorithm': 'kmeans', 'data': 'iris.csv', 'params': {'n_clusters': 3}, 'save_as': 'iris_km'}"
            },
            "ml_predict": {
                "func": lambda args: self._ml_predict(
                    model_name=str(args.get("model_name", "")),
                    data=str(args.get("data", "")),
                ),
                "desc": "Predicts using a previously trained+saved model. Args: {'model_name': 'iris_rf', 'data': 'new_data.csv'}"
            },

            # ══════════════════════════════════════════════════════════════════
            # ETIS Expert Domain Tools
            # ══════════════════════════════════════════════════════════════════

            # ── Cybersecurity ──────────────────────────────────────────────────
            "cve_lookup": {
                "func": lambda args: self._cve_lookup(cve_id=str(args.get("cve_id", ""))),
                "desc": "Full CVE record from NVD API v2.0 including CVSS, CWE, affected products, KEV status. Args: {'cve_id': 'CVE-2024-3400'}"
            },
            "cve_search": {
                "func": lambda args: self._cve_search(
                    keyword=str(args.get("keyword", "")),
                    min_cvss=float(args.get("min_cvss", 7.0)),
                    days_back=int(args.get("days_back", 30)),
                ),
                "desc": "Search NVD for recent CVEs by keyword. Args: {'keyword': 'palo alto', 'min_cvss': 7.0, 'days_back': 30}"
            },
            "mitre_ttp_search": {
                "func": lambda args: self._mitre_ttp_search(query=str(args.get("query", ""))),
                "desc": "Search MITRE ATT&CK techniques by keyword/ID. Args: {'query': 'T1190' or 'remote code execution'}"
            },
            "mitre_kill_chain": {
                "func": lambda args: self._mitre_kill_chain(
                    cve_id=str(args.get("cve_id", "")),
                    description=str(args.get("description", "")),
                ),
                "desc": "Map a CVE to ATT&CK kill chain phases and techniques. Args: {'cve_id': 'CVE-2024-3400', 'description': 'RCE in...'}"
            },
            "osint_passive_recon": {
                "func": lambda args: self._osint_passive_recon(target=str(args.get("target", ""))),
                "desc": "Passive OSINT recon: DNS, cert transparency, geolocation, subdomain enumeration. Args: {'target': 'example.com' or '1.2.3.4'}"
            },
            "osint_metadata": {
                "func": lambda args: self._osint_metadata(file_path=str(args.get("file_path", ""))),
                "desc": "Extract metadata from file (PDF/DOCX/JPEG/PNG): author, GPS, creation date. Args: {'file_path': '/path/to/file.pdf'}"
            },
            "exploit_search": {
                "func": lambda args: self._exploit_search(cve_id=str(args.get("cve_id", ""))),
                "desc": "Search for public exploits (PoC-in-GitHub) for a CVE. Args: {'cve_id': 'CVE-2024-3400'}"
            },
            "kev_feed": {
                "func": lambda args: self._kev_feed(days_back=int(args.get("days_back", 30))),
                "desc": "Fetch CISA Known Exploited Vulnerabilities added in last N days. Args: {'days_back': 30}"
            },

            # ── RF / Wireless ──────────────────────────────────────────────────
            "wifi_deep_scan": {
                "func": lambda _: self._wifi_deep_scan(),
                "desc": "Full WiFi scan: SSID/BSSID/channel/security/clients + evil twin detection. Arguments: none."
            },
            "bt_enumerate": {
                "func": lambda args: self._bt_enumerate(scan_duration=float(args.get("scan_duration", 10.0))),
                "desc": "BLE scan: discover nearby Bluetooth devices, RSSI distance, manufacturer data, AirTag detection. Args: {'scan_duration': 10.0}"
            },
            "spectrum_analyze": {
                "func": lambda args: self._spectrum_analyze(
                    center_freq=float(args.get("center_freq", 433.92e6)),
                    bandwidth=float(args.get("bandwidth", 200e3)),
                    duration=float(args.get("duration", 2.0)),
                ),
                "desc": "SDR spectrum analysis (RTL-SDR required). Args: {'center_freq': 433920000, 'bandwidth': 200000, 'duration': 2.0}"
            },
            "analyze_iq_file": {
                "func": lambda args: self._analyze_iq_file(
                    path=str(args.get("path", "")),
                    sample_rate=float(args.get("sample_rate", 2e6)),
                    center_freq=float(args.get("center_freq", 0.0)),
                ),
                "desc": "Offline IQ file analysis (FFT, waterfall). Args: {'path': 'capture.iq', 'sample_rate': 2000000}"
            },
            "identify_rf_protocol": {
                "func": lambda args: self._identify_rf_protocol(
                    center_freq=float(args.get("center_freq", 0)),
                    bandwidth=float(args.get("bandwidth", 0)),
                ),
                "desc": "Identify radio protocol from frequency and bandwidth. Args: {'center_freq': 868.42e6, 'bandwidth': 25000}"
            },

            # ── Protocol RE ────────────────────────────────────────────────────
            "parse_pcap": {
                "func": lambda args: self._parse_pcap(file_path=str(args.get("file_path", ""))),
                "desc": "Analyze PCAP file: flows, protocols, DNS, TLS SNIs, security findings. Args: {'file_path': 'capture.pcap'}"
            },
            "analyze_binary_protocol": {
                "func": lambda args: self._analyze_binary_protocol(
                    hex_samples=args.get("hex_samples", []),
                ),
                "desc": "Reverse engineer unknown binary protocol. Args: {'hex_samples': ['AABB0001000B...', ...]}"
            },
            "generate_dissector": {
                "func": lambda args: self._generate_dissector(
                    hex_samples=args.get("hex_samples", []),
                    protocol_name=str(args.get("protocol_name", "unknown")),
                    port=int(args.get("port", 9999)),
                    transport=str(args.get("transport", "tcp")),
                    output_path=args.get("output_path"),
                ),
                "desc": "Generate Wireshark Lua dissector from binary samples. Args: {'hex_samples': [...], 'protocol_name': 'MyProto', 'port': 9999}"
            },

            # ── Hardware / Firmware ────────────────────────────────────────────
            "analyze_firmware": {
                "func": lambda args: self._analyze_firmware(file_path=str(args.get("file_path", ""))),
                "desc": "Firmware binary analysis: entropy map, architecture, filesystem carving, credential extraction. Args: {'file_path': 'firmware.bin'}"
            },

            # ── Physics ────────────────────────────────────────────────────────
            "compute_physics": {
                "func": lambda args: self._compute_physics(
                    expression=str(args.get("expression", "")),
                    variables=args.get("variables", {}),
                    output=str(args.get("output", "symbolic")),
                ),
                "desc": "Physics computation: symbolic math, formula evaluation, LaTeX output. Args: {'expression': 'plasma_frequency', 'variables': {'n': 1e18}}"
            },
            "simulate_physics": {
                "func": lambda args: self._simulate_physics(
                    system=str(args.get("system", "pendulum")),
                    params=args.get("params", {}),
                    t_span=tuple(args.get("t_span", [0, 10])),
                ),
                "desc": "Simulate a physical system ODE. Systems: pendulum, lorenz, harmonic_oscillator, plasma_wave. Args: {'system': 'lorenz', 't_span': [0, 50]}"
            },
            "get_physics_constant": {
                "func": lambda args: self._get_physics_constant(name=str(args.get("name", ""))),
                "desc": "Lookup NIST CODATA physical constant. Args: {'name': 'speed_of_light' or 'boltzmann_constant'}"
            },

            # ── Robotics ───────────────────────────────────────────────────────
            "robot_forward_kinematics": {
                "func": lambda args: self._robot_fk(
                    joint_angles=args.get("joint_angles", []),
                    robot_model=str(args.get("robot_model", "ur5")),
                ),
                "desc": "Robot forward kinematics (UR5/PUMA560). Args: {'joint_angles': [0,0,0,0,0,0], 'robot_model': 'ur5'}"
            },
            "robot_inverse_kinematics": {
                "func": lambda args: self._robot_ik(
                    target_pos=tuple(args.get("target_pos", [0, 0, 0])),
                    robot_model=str(args.get("robot_model", "ur5")),
                ),
                "desc": "Robot IK: compute joint angles to reach (x,y,z) position. Args: {'target_pos': [0.3, 0.2, 0.5], 'robot_model': 'ur5'}"
            },

            # ── Sandbox Execution ──────────────────────────────────────────────
            "run_sandboxed": {
                "func": lambda args: self._run_sandboxed(
                    code=str(args.get("code", "")),
                    language=str(args.get("language", "python")),
                    timeout=int(args.get("timeout", 30)),
                ),
                "desc": "Execute code in isolated Docker sandbox (no network, memory-limited). Args: {'code': 'print(1+1)', 'language': 'python', 'timeout': 30}"
            },
            "sandbox_status": {
                "func": lambda _: self._sandbox_status(),
                "desc": "Check Docker sandbox availability and supported languages. Arguments: none."
            },

            # ── Intel Feeds ────────────────────────────────────────────────────
            "intel_feed": {
                "func": lambda args: self._intel_feed(days_back=int(args.get("days_back", 7))),
                "desc": "Fetch live threat intel: CISA KEV + arXiv security/robotics/physics papers. Args: {'days_back': 7}"
            },

            # ── Cross-Domain Synthesis ─────────────────────────────────────────
            "classify_domain": {
                "func": lambda args: self._classify_domain(query=str(args.get("query", ""))),
                "desc": "Classify a query into expert domains and suggest tool invocations. Args: {'query': 'analyze this AUV firmware for vulnerabilities'}"
            },
        }


    def describe_tools(self) -> str:
        """Return structured schemas for the LLM's prompt context."""
        if not self._settings.enable_system_tools:
            return "Tooling is disabled by config."

        descriptions = []
        for name, internal in self._registry.items():
            descriptions.append(f"- Tool: '{name}'\n  Usage: {internal['desc']}")
        return "\n".join(descriptions)

    def execute_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """Dynamically dispatches tool execution to registered functions."""
        if not self._settings.enable_system_tools:
            return ToolResult(ok=False, content="System tools are disabled.").to_text()

        name = (tool_name or "").strip()
        if name not in self._registry:
            return ToolResult(ok=False, content=f"Unknown tool target: '{name}'").to_text()

        try:
            target_entry = self._registry[name]
            handler = target_entry["func"]
            
            # Unified execution with arguments
            result = handler(args)
                
            return result.to_text()
        except Exception as exc:
            return ToolResult(ok=False, content=f"Execution error on tool '{name}': {exc}").to_text()

    # ---- Tool implementations ----

    def _get_system_status(self) -> ToolResult:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.getcwd())

        content = (
            f"CPU: {cpu_percent:.1f}%\n"
            f"Memory: {mem.percent:.1f}% used ({mem.available / (1024 ** 3):.2f} GB available)\n"
            f"Disk: {disk.percent:.1f}% used ({disk.free / (1024 ** 3):.2f} GB free)"
        )
        return ToolResult(ok=True, content=content)

    def _get_running_processes(self) -> ToolResult:
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    procs.append(f"{p.info['name']} (PID: {p.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            # Return top 15 for context safety
            content = "Running Processes (Top 15):\n" + "\n".join(procs[:15])
            return ToolResult(ok=True, content=content)
        except Exception as e:
            return ToolResult(ok=False, content=str(e))

    def _resolve_workspace_path(self, relative_path: str) -> str:
        rel = (relative_path or "").replace("\\", "/").lstrip("/")
        abs_path = os.path.abspath(os.path.join(self._workspace_root, rel))

        if not abs_path.startswith(self._workspace_root + os.sep) and abs_path != self._workspace_root:
            raise ValueError("Access Denied: Path escapes workspace security sandbox.")

        return abs_path

    def _list_dir(self, path: str) -> ToolResult:
        try:
            target = self._resolve_workspace_path(path)
            if not os.path.exists(target):
                return ToolResult(ok=False, content="Directory does not exist.")
            if not os.path.isdir(target):
                return ToolResult(ok=False, content="Path target is a file, not a directory.")

            entries = []
            for name in sorted(os.listdir(target)):
                full = os.path.join(target, name)
                kind = "dir" if os.path.isdir(full) else "file"
                entries.append(f"[{kind}] {name}")

            return ToolResult(ok=True, content="\n".join(entries) if entries else "(empty)")
        except Exception as e:
            return ToolResult(ok=False, content=str(e))

    def _read_file(self, path: str) -> ToolResult:
        try:
            target = self._resolve_workspace_path(path)
            if not os.path.exists(target):
                return ToolResult(ok=False, content="Target file does not exist.")
            
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()

            max_chars = 25000
            if len(data) > max_chars:
                data = data[:max_chars] + "\n... [Content Truncated due to size constraints]"
            return ToolResult(ok=True, content=data)
        except Exception as e:
            return ToolResult(ok=False, content=str(e))

    def _write_file(self, path: str, content: str) -> ToolResult:
        try:
            target = self._resolve_workspace_path(path)
            os.makedirs(os.path.dirname(target), exist_ok=True)

            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(ok=True, content=f"Successfully saved tracking logs to '{path}'.")
        except Exception as e:
            return ToolResult(ok=False, content=str(e))

    def _launch_app(self, path: str) -> ToolResult:
        p = (path or "").strip().replace("\\", "/")
        if not p:
            return ToolResult(ok=False, content="Executable binary path cannot be blank.")

        if not os.path.exists(p):
            return ToolResult(ok=False, content=f"Target path '{p}' cannot be found on host system.")

        # Cross-platform execution compatibility
        try:
            if sys.platform == "win32":
                # Windows hidden flag optimization
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen([p], creationflags=CREATE_NO_WINDOW, shell=False)
            else:
                # UNIX / POSIX baseline background launch
                subprocess.Popen([p], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            return ToolResult(ok=True, content=f"Process thread successfully initiated for: {p}")
        except Exception as exc:
            return ToolResult(ok=False, content=f"Process spawning breakdown: {exc}")

    def _open_browser(self, url: str) -> ToolResult:
        u = (url or "").strip()
        if not u:
            return ToolResult(ok=False, content="URL string parsing failed.")

        if not (u.startswith("http://") or u.startswith("https://")):
            u = "https://" + u

        webbrowser.open(u)
        return ToolResult(ok=True, content=f"Opening {u} in your browser.")

    def _search_web(self, query: str) -> ToolResult:
        q = (query or "").strip()
        if not q:
            return ToolResult(ok=False, content="Search payload cannot be empty.")

        encoded = urllib.parse.quote_plus(q)
        return self._open_browser(f"https://www.google.com/search?q={encoded}")

    def _play_music(self, query: str) -> ToolResult:
        q = (query or "").strip()
        if not q:
            return ToolResult(ok=False, content="Query string parsing dropped.")

        encoded = urllib.parse.quote_plus(q)
        return self._open_browser(f"https://www.youtube.com/results?search_query={encoded}")

    def _set_volume(self, level: int) -> ToolResult:
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            # Volume range is 0.0 to 1.0
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return ToolResult(ok=True, content=f"System volume set to {level}%.")
        except Exception as e:
            return ToolResult(ok=False, content=f"Volume control failed: {e}")

    def _set_brightness(self, level: int) -> ToolResult:
        try:
            sbc.set_brightness(level)
            return ToolResult(ok=True, content=f"Brightness set to {level}%.")
        except Exception as e:
            return ToolResult(ok=False, content=f"Brightness control failed: {e}")

    def _power_control(self, action: str) -> ToolResult:
        act = (action or "lock").strip().lower()
        try:
            if sys.platform == "win32":
                import ctypes

                if act == "lock":
                    ctypes.windll.user32.LockWorkStation()
                    return ToolResult(ok=True, content="Workstation locked.")
                if act == "sleep":
                    ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
                    return ToolResult(ok=True, content="System entering sleep mode.")
                if act == "shutdown":
                    subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
                    return ToolResult(ok=True, content="Shutdown initiated.")
                return ToolResult(ok=False, content=f"Unsupported power action: {act}")

            if act == "lock":
                subprocess.run(["loginctl", "lock-session"], check=False)
                return ToolResult(ok=True, content="Session locked.")
            if act == "sleep":
                subprocess.run(["systemctl", "suspend"], check=False)
                return ToolResult(ok=True, content="System entering sleep mode.")
            if act == "shutdown":
                subprocess.run(["shutdown", "-h", "now"], check=False)
                return ToolResult(ok=True, content="Shutdown initiated.")
            return ToolResult(ok=False, content=f"Unsupported power action: {act}")
        except Exception as e:
            return ToolResult(ok=False, content=f"Power control failed: {e}")

    def _media_control(self, action: str) -> ToolResult:
        try:
            mapping = {
                "playpause": "playpause",
                "next": "nexttrack",
                "prev": "prevtrack",
                "volumeup": "volumeup",
                "volumedown": "volumedown"
            }
            key = mapping.get(action.lower())
            if key:
                pyautogui.press(key)
                return ToolResult(ok=True, content=f"Media action '{action}' executed.")
            return ToolResult(ok=False, content=f"Unsupported media action: {action}")
        except Exception as e:
            return ToolResult(ok=False, content=f"Media control failed: {e}")

    def _research_topic(self, topic: str) -> ToolResult:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(topic, max_results=5))
            
            summary_parts = [f"Research Summary for: {topic}"]
            for r in results:
                summary_parts.append(f"- {r['title']}: {r['body']} (Source: {r['href']})")
            
            return ToolResult(ok=True, content="\n".join(summary_parts))
        except Exception as e:
            return ToolResult(ok=False, content=f"Research failed: {e}")

    def _get_ai_news(self) -> ToolResult:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text("latest AI news headlines", max_results=8))
            
            news_parts = ["Latest AI & Tech Headlines:"]
            for r in results:
                news_parts.append(f"- {r['title']} ({r['href']})")
            
            return ToolResult(ok=True, content="\n".join(news_parts))
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to fetch news: {e}")

    def _project_helper(self, task: str) -> ToolResult:
        # This tool is more of a prompt hint for the brain to use its own knowledge
        # but we can also use it to fetch documentation or common patterns.
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(f"documentation and examples for {task}", max_results=3))
            
            help_parts = [f"Project Assistance for: {task}"]
            for r in results:
                help_parts.append(f"- Source: {r['href']}\n  Details: {r['body']}")
            
            return ToolResult(ok=True, content="\n".join(help_parts))
        except Exception as e:
            return ToolResult(ok=False, content=f"Project helper failed: {e}")

    def _save_knowledge(self, fact: str) -> ToolResult:
        fact = (fact or "").strip()
        if not fact:
            return ToolResult(ok=False, content="No fact provided to save.")
        # Unified store: write to the SAME LongTermMemory the live chat recalls
        # from, so saved knowledge is actually retrievable (not a dead store).
        try:
            try:
                from ..core.ltm_memory import LongTermMemory
            except ImportError:
                from core.ltm_memory import LongTermMemory
            if not hasattr(self, "_ltm") or self._ltm is None:
                self._ltm = LongTermMemory()
            self._ltm.store(
                memory_type="fact",
                content=fact,
                metadata={"source": "save_knowledge"},
                importance=1.5,
            )
            return ToolResult(ok=True, content="Knowledge committed to long-term memory (recallable).")
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to save knowledge: {e}")

    # ---- Security tool implementations ----

    def _get_security_status(self) -> ToolResult:
        """Get comprehensive security monitoring status."""
        try:
            status = self._security_monitor.get_security_status()
            content = json.dumps(status, indent=2, default=str)
            return ToolResult(ok=True, content=content)
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to get security status: {e}")

    def _start_security_monitoring(self) -> ToolResult:
        """Start the security monitoring system."""
        try:
            self._security_monitor.start()
            return ToolResult(ok=True, content="DEEP Security Monitor started successfully. Network, system, and intrusion detection are now active.")
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to start security monitor: {e}")

    def _stop_security_monitoring(self) -> ToolResult:
        """Stop the security monitoring system."""
        try:
            self._security_monitor.stop()
            return ToolResult(ok=True, content="DEEP Security Monitor stopped.")
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to stop security monitor: {e}")

    def _get_security_events(self, limit: int = 20) -> ToolResult:
        """Get recent security events."""
        try:
            events = self._security_monitor._alert_system.get_recent_events(limit=limit)
            if not events:
                return ToolResult(ok=True, content="No recent security events detected.")
            
            content = f"Recent Security Events (Last {len(events)}):\n"
            for event in events:
                content += f"\n[{event['severity'].upper()}] {event['timestamp']}\n"
                content += f"Type: {event['event_type']} | Source: {event['source']}\n"
                content += f"Description: {event['description']}\n"
            
            return ToolResult(ok=True, content=content)
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to get security events: {e}")

    def _get_network_connections(self) -> ToolResult:
        """Get current active network connections."""
        try:
            connections = self._security_monitor._network_monitor.get_active_connections()
            if not connections:
                return ToolResult(ok=True, content="No active network connections found.")
            
            content = f"Active Network Connections ({len(connections)}):\n"
            for conn in connections[:20]:  # Limit to 20 for readability
                content += f"\n{conn['remote_address']}:{conn['remote_port']} -> {conn['local_address']}:{conn['local_port']}\n"
                content += f"Status: {conn['status']} | Process: {conn['process_name']} (PID: {conn['pid']})\n"
            
            return ToolResult(ok=True, content=content)
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to get network connections: {e}")

    def _scan_network(self) -> ToolResult:
        """Lightweight network discovery via ARP cache."""
        try:
            if sys.platform == "win32":
                output = subprocess.check_output(["arp", "-a"], stderr=subprocess.STDOUT, text=True)
            else:
                output = subprocess.check_output(["ip", "neigh"], stderr=subprocess.STDOUT, text=True)
            
            return ToolResult(ok=True, content=f"Active LAN Devices:\n{output}")
        except Exception as e:
            return ToolResult(ok=False, content=f"Network scan failed: {e}")

    def _scan_ports(self, target: str) -> ToolResult:
        """Basic port scanner for common services."""
        import socket
        common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 8080, 27017]
        open_ports = []
        
        target_ip = target.strip()
        timeout = 0.5  # 500ms timeout per port
        
        try:
            for port in common_ports:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    result = s.connect_ex((target_ip, port))
                    if result == 0:
                        open_ports.append(str(port))
            
            if open_ports:
                return ToolResult(ok=True, content=f"Open ports found on {target_ip}: {', '.join(open_ports)}")
            return ToolResult(ok=True, content=f"No common ports open on {target_ip}.")
        except Exception as e:
            return ToolResult(ok=False, content=f"Port scan error: {e}")

    def _audit_system(self) -> ToolResult:
        """Audits firewall and suspicious processes."""
        audit_report = ["System Security Audit Report:"]
        
        # 1. Firewall Status
        try:
            if sys.platform == "win32":
                fw = subprocess.check_output(["netsh", "advfirewall", "show", "allprofiles", "state"], text=True)
                audit_report.append("\n[Firewall Status]\n" + fw.strip())
            else:
                fw = subprocess.check_output(["ufw", "status"], text=True)
                audit_report.append("\n[Firewall Status]\n" + fw.strip())
        except Exception:
            audit_report.append("\n[Firewall Status] Could not determine (permission denied or tool missing).")

        # 2. Suspicious Processes (simple heuristic)
        suspicious = []
        for p in psutil.process_iter(['pid', 'name', 'username']):
            try:
                # Flag processes with weird names or known suspicious patterns if we had a list
                # For now, just list those running from temp dirs or with no name
                if not p.info['name'] or ".tmp" in p.info['name'].lower():
                    suspicious.append(f"{p.info['name']} (PID: {p.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if suspicious:
            audit_report.append("\n[Suspicious Processes]\n" + "\n".join(suspicious))
        else:
            audit_report.append("\n[Suspicious Processes] None detected via basic heuristics.")

        return ToolResult(ok=True, content="\n".join(audit_report))

    def _threat_intel(self, query: str) -> ToolResult:
        """Researches threats and CVEs."""
        if not query:
            return ToolResult(ok=False, content="Please specify a vulnerability or technology to research.")
        
        search_query = f"vulnerability CVE security advisory {query}"
        return self._research_topic(search_query)

    # ---- JARVIS News & Automation Tools ----

    def _get_news_briefing(self) -> ToolResult:
        """Fetch global news briefing."""
        try:
            # Import here to avoid circular dependencies
            from DEEP.news_engine import NewsAggregator
            
            aggregator = NewsAggregator(self._settings)
            briefing = aggregator.get_briefing()
            formatted = aggregator.format_briefing_text(briefing)
            
            return ToolResult(ok=True, content=formatted)
        except Exception as e:
            logger.error(f"News briefing error: {e}")
            return ToolResult(ok=False, content=f"Failed to fetch news: {e}")

    def _search_news(self, query: str, max_results: int = 10) -> ToolResult:
        """Search news for specific topics."""
        try:
            from DEEP.news_engine import NewsAggregator
            
            aggregator = NewsAggregator(self._settings)
            articles = aggregator.search_news(query, max_results)
            
            if not articles:
                return ToolResult(ok=True, content=f"No news found for '{query}'.")
            
            content = f"News Search Results for '{query}':\n\n"
            for i, article in enumerate(articles, 1):
                content += f"{i}. {article.title}\n"
                content += f"   Source: {article.source} | Category: {article.category}\n"
                if article.summary:
                    content += f"   Summary: {article.summary[:100]}...\n"
                content += f"   Link: {article.url}\n\n"
            
            return ToolResult(ok=True, content=content)
        except Exception as e:
            logger.error(f"News search error: {e}")
            return ToolResult(ok=False, content=f"Failed to search news: {e}")

    def _fetch_page(self, url: str) -> ToolResult:
        """Fetch and return cleaned text body of a webpage."""
        u = (url or "").strip()
        if not u:
            return ToolResult(ok=False, content="No URL provided.")
        if not (u.startswith("http://") or u.startswith("https://")):
            u = "https://" + u
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; DEEP/1.0)"}
            resp = requests.get(u, headers=headers, timeout=10)
            resp.raise_for_status()

            if BeautifulSoup is not None:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
            else:
                import re as _re
                text = _re.sub(r"<[^>]+>", " ", resp.text)

            # Trim to 6000 chars — enough for LLM context without blowing the window
            text = "\n".join(line for line in text.splitlines() if line.strip())
            if len(text) > 6000:
                text = text[:6000] + "\n… [content truncated]"
            return ToolResult(ok=True, content=f"[Page: {u}]\n\n{text}")
        except Exception as e:
            return ToolResult(ok=False, content=f"Failed to fetch page: {e}")

    def _deep_search(self, query: str, num_pages: int = 3) -> ToolResult:
        """Search DuckDuckGo and read the top N pages for thorough research."""
        q = (query or "").strip()
        if not q:
            return ToolResult(ok=False, content="No query provided.")
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(q, max_results=max(num_pages, 5)))
        except Exception as e:
            return ToolResult(ok=False, content=f"Search failed: {e}")

        if not results:
            return ToolResult(ok=False, content=f"No results found for: {q}")

        parts = [f"Deep Research: {q}\n{'='*60}"]

        fetched = 0
        for r in results:
            if fetched >= num_pages:
                break
            title = r.get("title", "(no title)")
            href  = r.get("href", "")
            snippet = r.get("body", "")

            # Try to fetch full page body
            page_result = self._fetch_page(href) if href else None
            if page_result and page_result.ok:
                body = page_result.content
            else:
                body = f"[snippet only]  {snippet}"

            parts.append(f"\n--- Source {fetched+1}: {title} ---\n{href}\n{body}")
            fetched += 1

        return ToolResult(ok=True, content="\n".join(parts))

    def _get_weather(self, location: str) -> ToolResult:
        """Get current weather for a location via Open-Meteo (free, no key)."""
        loc = (location or "").strip()
        if not loc:
            return ToolResult(ok=False, content="No location provided.")
        try:
            # Step 1: geocode the city name
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(loc)}&count=1"
            geo = requests.get(geo_url, timeout=8).json()
            results = geo.get("results")
            if not results:
                return ToolResult(ok=False, content=f"Location not found: {loc}")
            r = results[0]
            lat, lon, name, country = r["latitude"], r["longitude"], r["name"], r.get("country", "")

            # Step 2: fetch weather
            wx_url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
                f"precipitation,weather_code"
                f"&temperature_unit=celsius&wind_speed_unit=kmh&timezone=auto"
            )
            wx = requests.get(wx_url, timeout=8).json()
            cur = wx.get("current", {})

            WX_CODE = {
                0:"Clear sky", 1:"Mainly clear", 2:"Partly cloudy", 3:"Overcast",
                45:"Fog", 48:"Icy fog",
                51:"Light drizzle", 53:"Moderate drizzle", 55:"Dense drizzle",
                61:"Slight rain", 63:"Moderate rain", 65:"Heavy rain",
                71:"Slight snow", 73:"Moderate snow", 75:"Heavy snow",
                80:"Slight showers", 81:"Moderate showers", 82:"Violent showers",
                95:"Thunderstorm", 99:"Thunderstorm with hail",
            }
            code  = cur.get("weather_code", 0)
            desc  = WX_CODE.get(code, f"Code {code}")
            temp  = cur.get("temperature_2m", "?")
            hum   = cur.get("relative_humidity_2m", "?")
            wind  = cur.get("wind_speed_10m", "?")
            rain  = cur.get("precipitation", 0)

            content = (
                f"Weather for {name}, {country}:\n"
                f"  Condition  : {desc}\n"
                f"  Temperature: {temp}°C\n"
                f"  Humidity   : {hum}%\n"
                f"  Wind       : {wind} km/h\n"
                f"  Precip     : {rain} mm"
            )
            return ToolResult(ok=True, content=content)
        except Exception as e:
            return ToolResult(ok=False, content=f"Weather lookup failed: {e}")

    def _get_price(self, symbol: str) -> ToolResult:
        """Get live stock or crypto price via Yahoo Finance (no key required)."""
        sym = (symbol or "").strip().upper()
        if not sym:
            return ToolResult(ok=False, content="No symbol provided. Example: AAPL, BTC-USD, TSLA")
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?interval=1d&range=1d"
            headers = {"User-Agent": "Mozilla/5.0"}
            data = requests.get(url, headers=headers, timeout=8).json()
            meta = data["chart"]["result"][0]["meta"]
            price    = meta.get("regularMarketPrice", "?")
            prev     = meta.get("chartPreviousClose", price)
            currency = meta.get("currency", "")
            name     = meta.get("longName", sym)
            chg      = round(price - prev, 4) if isinstance(price, (int, float)) and isinstance(prev, (int, float)) else "?"
            pct      = round(chg / prev * 100, 2) if isinstance(prev, (int, float)) and prev else "?"
            direction = "▲" if isinstance(chg, (int, float)) and chg >= 0 else "▼"
            content = (
                f"{name} ({sym})\n"
                f"  Price   : {currency} {price}\n"
                f"  Change  : {direction} {chg} ({pct}%)\n"
                f"  Prev    : {currency} {prev}"
            )
            return ToolResult(ok=True, content=content)
        except Exception as e:
            return ToolResult(ok=False, content=f"Price lookup failed for '{sym}': {e}")

    def _submit_task(self, task_description: str, priority: int = 5) -> ToolResult:
        """Submit task for autonomous execution."""
        try:
            from DEEP.automation import create_automation_system
            from DEEP.personality import get_personality
            
            personality = get_personality()
            automation = create_automation_system(self._settings, self.execute_tool)
            automation.start()
            
            # Submit the task
            task = automation.submit_task(task_description, priority=priority)
            
            confirmation = personality.format_task_start(task.name)
            content = f"{confirmation}\n\nTask Details:"
            content += f"\n  ID: {task.id}"
            content += f"\n  Name: {task.name}"
            content += f"\n  Priority: {priority}/10"
            content += f"\n  Steps: {len(task.steps)}"
            content += "\n\nThe task is now running autonomously. Use get_task_status to check progress."
            
            return ToolResult(ok=True, content=content)
        except Exception as e:
            logger.error(f"Task submission error: {e}")
            return ToolResult(ok=False, content=f"Failed to submit task: {e}")

    def _get_all_tasks(self) -> ToolResult:
        """Get status of all tasks."""
        try:
            from DEEP.automation import create_automation_system
            
            automation = create_automation_system(self._settings, self.execute_tool)
            tasks = automation.list_tasks()
            
            if not tasks:
                return ToolResult(ok=True, content="No tasks found. Submit a task with submit_task.")
            
            content = f"Task Status ({len(tasks)} total):\n"
            content += "=" * 50 + "\n\n"
            
            for task in tasks[:10]:  # Show last 10
                status_icon = "✅" if task['status'] == 'completed' else \
                             "▶️" if task['status'] == 'running' else \
                             "⏳" if task['status'] == 'pending' else "❌"
                
                content += f"{status_icon} {task['name']}\n"
                content += f"   ID: {task['id']} | Status: {task['status'].upper()}\n"
                content += f"   Progress: {task['progress']}% | Created: {task['created_at'][:16]}\n\n"
            
            return ToolResult(ok=True, content=content)
        except Exception as e:
            logger.error(f"Task status error: {e}")
            return ToolResult(ok=False, content=f"Failed to get task status: {e}")

    # ---- ML algorithm knowledge base (Layer 1) ----

    def _ml_list(self) -> ToolResult:
        """List every ML algorithm Deep is aware of."""
        try:
            try:
                from ..ai import ml_catalog
            except ImportError:
                from ai import ml_catalog
            return ToolResult(ok=True, content=ml_catalog.list_all())
        except Exception as e:
            return ToolResult(ok=False, content=f"ML catalog unavailable: {e}")

    def _ml_explain(self, query: str) -> ToolResult:
        """Explain a single ML algorithm."""
        try:
            try:
                from ..ai import ml_catalog
            except ImportError:
                from ai import ml_catalog
            return ToolResult(ok=True, content=ml_catalog.explain(query))
        except Exception as e:
            return ToolResult(ok=False, content=f"ML catalog unavailable: {e}")

    def _ml_recommend(self, problem: str) -> ToolResult:
        """Recommend ML algorithms for a described problem."""
        try:
            try:
                from ..ai import ml_catalog
            except ImportError:
                from ai import ml_catalog
            return ToolResult(ok=True, content=ml_catalog.recommend(problem))
        except Exception as e:
            return ToolResult(ok=False, content=f"ML catalog unavailable: {e}")

    # ---- ML execution (Layer 2) ----

    @property
    def _models_dir(self) -> str:
        d = os.path.join(self._workspace_root, "ml_models")
        os.makedirs(d, exist_ok=True)
        return d

    def _resolve_dataset(self, data: str):
        """Resolve a data spec into a pandas DataFrame.

        Supports both:
          - workspace-relative CSV path (e.g. 'datasets/iris.csv')
          - internal Deep data: 'internal:processes', 'internal:network'
        Returns (DataFrame, error_message). Exactly one is non-None.
        """
        import pandas as pd
        spec = (data or "").strip()
        if not spec:
            return None, "No data source given. Use a workspace CSV path or 'internal:processes' / 'internal:network'."

        if spec.lower().startswith("internal:"):
            source = spec.split(":", 1)[1].strip().lower()
            if source == "processes":
                rows = []
                for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'num_threads']):
                    try:
                        i = p.info
                        rows.append({
                            "pid": i.get("pid"),
                            "cpu_percent": i.get("cpu_percent") or 0.0,
                            "memory_percent": i.get("memory_percent") or 0.0,
                            "num_threads": i.get("num_threads") or 0,
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                return pd.DataFrame(rows), None
            if source == "network":
                rows = []
                for c in psutil.net_connections(kind="inet"):
                    try:
                        rows.append({
                            "family": int(c.family),
                            "type": int(c.type),
                            "status_code": hash(c.status) % 1000,
                            "local_port": c.laddr.port if c.laddr else 0,
                            "remote_port": c.raddr.port if c.raddr else 0,
                            "pid": c.pid or 0,
                        })
                    except Exception:
                        continue
                return pd.DataFrame(rows), None
            return None, f"Unknown internal source '{source}'. Available: processes, network."

        # Otherwise treat as a workspace CSV path
        try:
            target = self._resolve_workspace_path(spec)
        except ValueError as e:
            return None, str(e)
        if not os.path.exists(target):
            return None, f"CSV not found in workspace: '{spec}'. Place it under the workspace folder first."
        try:
            return pd.read_csv(target), None
        except Exception as e:
            return None, f"Failed to read CSV '{spec}': {e}"

    def _ml_runnable(self) -> ToolResult:
        try:
            try:
                from ..ai import ml_runner
            except ImportError:
                from ai import ml_runner
            algos = ml_runner.runnable_algorithms()
            content = (
                "ML algorithms Deep can TRAIN/RUN right now (scikit-learn):\n  "
                + ", ".join(algos)
                + "\n\nAdvise-only for now (libs not installed / heavy): xgboost, "
                  "ann, cnn, rnn, lstm, transformer, autoencoder, and all reinforcement-learning algorithms."
            )
            return ToolResult(ok=True, content=content)
        except Exception as e:
            return ToolResult(ok=False, content=f"ML runner unavailable: {e}")

    def _ml_train(self, algorithm: str, data: str, target=None, save_as=None, params=None) -> ToolResult:
        try:
            try:
                from ..ai import ml_runner
            except ImportError:
                from ai import ml_runner
            # params may arrive as a dict or a JSON string from the LLM
            if isinstance(params, str):
                params = json.loads(params) if params.strip() else None
            if params is not None and not isinstance(params, dict):
                return ToolResult(ok=False, content="params must be a JSON object, e.g. {'n_clusters': 3}")
            df, err = self._resolve_dataset(data)
            if err:
                return ToolResult(ok=False, content=err)
            report = ml_runner.train(
                df, algorithm, target=target, params=params, save_as=save_as, models_dir=self._models_dir
            )
            return ToolResult(ok=True, content=report)
        except Exception as e:
            return ToolResult(ok=False, content=f"ml_train failed: {e}")

    def _ml_predict(self, model_name: str, data: str) -> ToolResult:
        try:
            try:
                from ..ai import ml_runner
            except ImportError:
                from ai import ml_runner
            df, err = self._resolve_dataset(data)
            if err:
                return ToolResult(ok=False, content=err)
            report = ml_runner.predict(df, model_name, self._models_dir)
            return ToolResult(ok=True, content=report)
        except Exception as e:
            return ToolResult(ok=False, content=f"ml_predict failed: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # ETIS Expert Domain Implementations
    # ══════════════════════════════════════════════════════════════════════════

    # ── Cybersecurity ──────────────────────────────────────────────────────────

    def _cve_lookup(self, cve_id: str) -> ToolResult:
        try:
            import asyncio
            try:
                from domains.cybersec.cve_intel import CVEIntel
            except ImportError:
                return ToolResult(ok=False, content="[CVE] Domain module not found. Run from DEEP root directory.")
            intel = CVEIntel()
            result = asyncio.run(intel.lookup(cve_id.strip().upper()))
            if result.error:
                return ToolResult(ok=False, content=f"[CVE] {result.error}")
            lines = [
                f"[CVE] {result.cve_id}",
                f"Severity: {result.severity} (CVSS {result.cvss_score:.1f})" if result.cvss_score else f"Severity: {result.severity}",
                f"Published: {result.published}",
                f"KEV: {'YES — actively exploited in the wild!' if result.is_kev else 'No'}",
                f"Description: {result.description}",
                f"CWEs: {', '.join(result.cwes) if result.cwes else 'None'}",
                f"Affected: {', '.join(result.affected_products[:5]) if result.affected_products else 'Unknown'}",
                f"References: {', '.join(result.references[:3])}",
            ]
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[CVE] Lookup failed: {e}")

    def _cve_search(self, keyword: str, min_cvss: float = 7.0, days_back: int = 30) -> ToolResult:
        try:
            import asyncio
            from domains.cybersec.cve_intel import CVEIntel
            intel = CVEIntel()
            results = asyncio.run(intel.search_recent(keyword=keyword, min_cvss=min_cvss, days_back=days_back))
            if not results:
                return ToolResult(ok=True, content=f"[CVE] No CVEs found for '{keyword}' (CVSS≥{min_cvss}) in last {days_back}d.")
            lines = [f"[CVE] Found {len(results)} CVEs for '{keyword}':"]
            for r in results:
                kev = " 🔴 KEV" if r.is_kev else ""
                lines.append(f"  {r.cve_id} | CVSS {r.cvss_score:.1f} | {r.severity}{kev}")
                lines.append(f"    {r.description[:120]}...")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[CVE] Search failed: {e}")

    def _mitre_ttp_search(self, query: str) -> ToolResult:
        try:
            import asyncio
            from domains.cybersec.mitre_attack import MITREAttack
            mitre = MITREAttack()
            results = asyncio.run(mitre.search_techniques(query))
            if not results:
                return ToolResult(ok=True, content=f"[MITRE] No techniques found for: {query}")
            lines = [f"[MITRE ATT&CK] Results for '{query}':"]
            for t in results[:8]:
                lines.append(f"  {t.technique_id} | {t.name} | Phase: {t.kill_chain_phase}")
                lines.append(f"    {t.description[:150]}...")
                if t.mitigations:
                    lines.append(f"    Mitigations: {'; '.join(t.mitigations[:2])}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[MITRE] Search failed: {e}")

    def _mitre_kill_chain(self, cve_id: str, description: str) -> ToolResult:
        try:
            import asyncio
            from domains.cybersec.mitre_attack import MITREAttack
            mitre = MITREAttack()
            mapping = asyncio.run(mitre.map_cve_to_ttps(cve_id=cve_id, vuln_description=description))
            lines = [f"[MITRE] Kill chain mapping for {cve_id or 'described vulnerability'}:"]
            for ttp in mapping:
                lines.append(f"  [{ttp.kill_chain_phase}] {ttp.technique_id} — {ttp.name}")
                lines.append(f"    {ttp.description[:120]}...")
            return ToolResult(ok=True, content="\n".join(lines) if mapping else f"[MITRE] No TTPs mapped.")
        except Exception as e:
            return ToolResult(ok=False, content=f"[MITRE] Mapping failed: {e}")

    def _osint_passive_recon(self, target: str) -> ToolResult:
        try:
            import asyncio
            from domains.cybersec.osint_engine import OSINTEngine
            engine = OSINTEngine()
            result = asyncio.run(engine.recon(target.strip()))
            if result.error:
                return ToolResult(ok=False, content=f"[OSINT] {result.error}")
            lines = [
                f"[OSINT] Passive recon: {result.target}",
                f"IPs: {', '.join(result.ip_addresses[:10])}",
                f"Subdomains ({len(result.subdomains)}): {', '.join(result.subdomains[:8])}",
                f"Open Ports: {', '.join(str(p) for p in result.open_ports[:20])}",
                f"SSL Issuer: {result.ssl_info.get('issuer', 'N/A') if result.ssl_info else 'N/A'}",
                f"SSL Expires: {result.ssl_info.get('not_after', 'N/A') if result.ssl_info else 'N/A'}",
                f"GeoIP: {result.geolocation.get('country', '?')}, {result.geolocation.get('org', '?')}",
                f"Email Addresses: {', '.join(result.email_addresses[:5]) or 'None found'}",
                f"Technology Stack: {', '.join(result.technology_stack[:5]) or 'Unknown'}",
            ]
            if result.shodan_data:
                lines.append(f"Shodan Hostnames: {', '.join(result.shodan_data.get('hostnames', [])[:3])}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[OSINT] Recon failed: {e}")

    def _osint_metadata(self, file_path: str) -> ToolResult:
        try:
            import asyncio
            from domains.cybersec.osint_engine import OSINTEngine
            engine = OSINTEngine()
            result = asyncio.run(engine.extract_file_metadata(file_path))
            if "error" in result:
                return ToolResult(ok=False, content=f"[OSINT] {result['error']}")
            import json
            return ToolResult(ok=True, content=f"[OSINT] Metadata:\n{json.dumps(result, indent=2, default=str)}")
        except Exception as e:
            return ToolResult(ok=False, content=f"[OSINT] Metadata extraction failed: {e}")

    def _exploit_search(self, cve_id: str) -> ToolResult:
        try:
            import asyncio
            from domains.cybersec.exploit_lookup import ExploitLookup
            lookup = ExploitLookup()
            results = asyncio.run(lookup.search(cve_id.strip().upper()))
            if not results:
                return ToolResult(ok=True, content=f"[EXPLOIT] No public exploits found for {cve_id}.")
            lines = [f"[EXPLOIT] {len(results)} exploit(s) found for {cve_id}:"]
            for e in results[:5]:
                lines.append(f"  [{e.exploit_type}] {e.title}")
                lines.append(f"    PoC: {e.poc_url}")
                if e.cvss_score:
                    lines.append(f"    CVSS: {e.cvss_score:.1f}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[EXPLOIT] Search failed: {e}")

    def _kev_feed(self, days_back: int = 30) -> ToolResult:
        try:
            import asyncio
            from domains.cybersec.cve_intel import CVEIntel
            intel = CVEIntel()
            items = asyncio.run(intel.get_kev_recent(days_back=days_back))
            if not items:
                return ToolResult(ok=True, content=f"[KEV] No new entries in last {days_back} days.")
            lines = [f"[KEV] CISA Known Exploited Vulnerabilities (last {days_back}d): {len(items)} entries"]
            for item in items[:15]:
                lines.append(f"  {item.get('cveID', '?')} | {item.get('vendorProject', '?')} {item.get('product', '')} | Due: {item.get('dueDate', '?')}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[KEV] Feed fetch failed: {e}")

    # ── RF / Wireless ──────────────────────────────────────────────────────────

    def _wifi_deep_scan(self) -> ToolResult:
        try:
            import asyncio
            from domains.rf_signals.wifi_scanner import WiFiScanner
            scanner = WiFiScanner()
            result = asyncio.run(scanner.deep_scan())
            if result.error:
                return ToolResult(ok=False, content=f"[WIFI] {result.error}")
            lines = [f"[WIFI] Found {len(result.networks)} networks:"]
            for net in sorted(result.networks, key=lambda n: n.signal_strength, reverse=True)[:15]:
                lines.append(f"  {net.ssid or '(hidden)'} | {net.bssid} | ch{net.channel} | {net.security} | {net.signal_strength} dBm")
            if result.evil_twins:
                lines.append(f"\n🚨 EVIL TWIN ALERTS ({len(result.evil_twins)}):")
                for et in result.evil_twins:
                    lines.append(f"  Possible evil twin of '{et.get('ssid')}': {et.get('bssid')} vs {et.get('legitimate_bssid')}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[WIFI] Scan failed: {e}")

    def _bt_enumerate(self, scan_duration: float = 10.0) -> ToolResult:
        try:
            import asyncio
            from domains.rf_signals.bt_enumerator import BTEnumerator
            enumerator = BTEnumerator()
            result = asyncio.run(enumerator.scan(duration=scan_duration))
            if result.error:
                return ToolResult(ok=False, content=f"[BT] {result.error}")
            lines = [f"[BT] Found {len(result.devices)} BLE devices in {scan_duration:.0f}s:"]
            for dev in sorted(result.devices, key=lambda d: d.rssi or -999, reverse=True)[:15]:
                lines.append(f"  {dev.address} | {dev.name or '(unnamed)'} | {dev.rssi} dBm | ~{dev.estimated_distance_m:.1f}m")
                if dev.is_airtag:
                    lines.append(f"    🍎 Apple AirTag detected!")
                if dev.manufacturer_data:
                    mfr_id = list(dev.manufacturer_data.keys())[0]
                    lines.append(f"    MFR ID: 0x{mfr_id:04X}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[BT] Scan failed: {e}")

    def _spectrum_analyze(self, center_freq: float, bandwidth: float, duration: float) -> ToolResult:
        try:
            import asyncio
            from domains.rf_signals.spectrum_analyzer import SpectrumAnalyzer
            analyzer = SpectrumAnalyzer()
            result = asyncio.run(analyzer.analyze_spectrum(center_freq=center_freq, bandwidth=bandwidth, duration=duration))
            if result.error:
                return ToolResult(ok=False, content=f"[SDR] {result.error}")
            lines = [
                f"[SPECTRUM] Center: {center_freq/1e6:.3f} MHz, BW: {bandwidth/1e6:.3f} MHz",
                f"Peak: {result.peak_frequency/1e6:.3f} MHz ({result.peak_power:.1f} dBm)",
                f"Noise floor: {result.noise_floor:.1f} dBm",
                f"SNR: {result.snr:.1f} dB",
            ]
            if result.detected_signals:
                lines.append(f"Detected signals ({len(result.detected_signals)}):")
                for sig in result.detected_signals[:5]:
                    lines.append(f"  {sig.center_freq/1e6:.3f} MHz | {sig.bandwidth/1e3:.0f} kHz BW | {sig.modulation} | {sig.power_dbm:.1f} dBm")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[SDR] Spectrum analysis failed: {e}")

    def _analyze_iq_file(self, path: str, sample_rate: float, center_freq: float) -> ToolResult:
        try:
            import asyncio
            from domains.rf_signals.spectrum_analyzer import SpectrumAnalyzer
            analyzer = SpectrumAnalyzer()
            result = asyncio.run(analyzer.analyze_iq_file(path=path, sample_rate=sample_rate, center_freq=center_freq))
            if result.error:
                return ToolResult(ok=False, content=f"[IQ] {result.error}")
            lines = [f"[IQ File] {path}", f"Signals: {len(result.detected_signals)}"]
            for sig in result.detected_signals[:8]:
                lines.append(f"  {sig.center_freq/1e6:.3f} MHz | {sig.modulation} | {sig.power_dbm:.1f} dBm")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[IQ] Analysis failed: {e}")

    def _identify_rf_protocol(self, center_freq: float, bandwidth: float) -> ToolResult:
        try:
            from domains.rf_signals.protocol_id import ProtocolIdentifier
            pid = ProtocolIdentifier()
            matches = pid.identify(center_freq_hz=center_freq, bandwidth_hz=bandwidth)
            if not matches:
                return ToolResult(ok=True, content=f"[RF] No known protocol matched at {center_freq/1e6:.3f} MHz.")
            lines = [f"[RF PROTOCOL] Best matches for {center_freq/1e6:.3f} MHz, BW {bandwidth/1e3:.0f} kHz:"]
            for m in matches[:5]:
                lines.append(f"  [{m.confidence:.0%}] {m.protocol_name}")
                lines.append(f"    Modulation: {m.modulation} | Range: {m.frequency_range}")
                lines.append(f"    Use: {m.typical_use}")
                if m.security_notes:
                    lines.append(f"    ⚠ {m.security_notes}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[RF] Protocol ID failed: {e}")

    # ── Protocol RE ────────────────────────────────────────────────────────────

    def _parse_pcap(self, file_path: str) -> ToolResult:
        try:
            import asyncio
            from domains.protocols.pcap_analyzer import PCAPAnalyzer
            analyzer = PCAPAnalyzer()
            report = asyncio.run(analyzer.analyze(file_path))
            if report.error:
                return ToolResult(ok=False, content=f"[PCAP] {report.error}")
            lines = [
                f"[PCAP] {file_path}",
                f"Packets: {report.total_packets:,} | Bytes: {report.total_bytes:,} | Duration: {report.duration_s:.1f}s",
                f"Flows: {len(report.flows)} | DNS queries: {len(report.dns_queries)} | TLS SNIs: {len(report.tls_snis)}",
                f"Top flows:",
            ]
            for flow in report.flows[:5]:
                lines.append(f"  {flow.src_ip}:{flow.src_port} → {flow.dst_ip}:{flow.dst_port} ({flow.app_layer}) {flow.byte_count:,}B")
            if report.findings:
                lines.append(f"\nSecurity Findings ({len(report.findings)}):")
                for f2 in report.findings[:5]:
                    lines.append(f"  [{f2.severity}] {f2.title}")
                    lines.append(f"    {f2.description}")
                    lines.append(f"    Recommendation: {f2.recommendation}")
            if report.dns_queries:
                lines.append(f"\nDNS queries: {', '.join(report.dns_queries[:10])}")
            if report.tls_snis:
                lines.append(f"TLS SNIs: {', '.join(report.tls_snis[:10])}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[PCAP] Analysis failed: {e}")

    def _analyze_binary_protocol(self, hex_samples: list) -> ToolResult:
        try:
            from domains.protocols.binary_protocol import BinaryProtocolRE
            samples = [bytes.fromhex(h.replace(" ", "")) for h in hex_samples]
            re_engine = BinaryProtocolRE()
            proto = re_engine.analyze(samples)
            lines = [
                f"[PROTO RE] Inferred Protocol from {len(samples)} samples",
                f"Entropy: {proto.entropy_bits_per_byte:.2f} bits/byte | Confidence: {proto.confidence:.0%}",
                f"Encrypted: {proto.is_encrypted} | Magic: {proto.has_magic} | Checksum: {proto.has_checksum} | Sequence: {proto.has_sequence}",
                f"Header size: {proto.header_size}B",
                f"Fields:",
            ]
            for field in proto.fields:
                lines.append(f"  @{field.offset}+{field.size}B [{field.field_type}]: {field.description}")
                lines.append(f"    Examples: {', '.join(field.example_values[:4])}")
            if proto.security_issues:
                lines.append(f"Security issues:")
                for iss in proto.security_issues:
                    lines.append(f"  ⚠ {iss}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[PROTO RE] Analysis failed: {e}")

    def _generate_dissector(self, hex_samples: list, protocol_name: str, port: int, transport: str, output_path=None) -> ToolResult:
        try:
            from domains.protocols.binary_protocol import BinaryProtocolRE
            from domains.protocols.dissector_gen import DissectorGenerator
            samples = [bytes.fromhex(h.replace(" ", "")) for h in hex_samples]
            re_engine = BinaryProtocolRE()
            proto = re_engine.analyze(samples)
            gen = DissectorGenerator()
            lua = gen.generate(proto, protocol_name, port, transport, output_path)
            preview = lua[:1000] + ("\n... [truncated]" if len(lua) > 1000 else "")
            return ToolResult(ok=True, content=f"[DISSECTOR] Wireshark Lua dissector:\n\n{preview}")
        except Exception as e:
            return ToolResult(ok=False, content=f"[DISSECTOR] Generation failed: {e}")

    # ── Hardware / Firmware ────────────────────────────────────────────────────

    def _analyze_firmware(self, file_path: str) -> ToolResult:
        try:
            import asyncio
            from domains.hardware.firmware_analyzer import FirmwareAnalyzer
            analyzer = FirmwareAnalyzer()
            report = asyncio.run(analyzer.analyze(file_path))
            if report.error:
                return ToolResult(ok=False, content=f"[FIRMWARE] {report.error}")
            lines = [
                f"[FIRMWARE] {file_path}",
                f"Size: {report.file_size:,}B | MD5: {report.md5} | SHA256: {report.sha256}",
                f"Architecture: {report.architecture.arch} ({report.architecture.endianness}-endian) [{report.architecture.confidence:.0%}]",
                f"Evidence: {report.architecture.evidence}",
                f"Entropy segments: {len(report.entropy_segments)}",
            ]
            type_counts: dict = {}
            for seg in report.entropy_segments:
                type_counts[seg.segment_type] = type_counts.get(seg.segment_type, 0) + 1
            for seg_type, count in type_counts.items():
                lines.append(f"  {seg_type}: {count} segment(s)")
            if report.filesystems:
                lines.append(f"\nFilesystem signatures ({len(report.filesystems)}):")
                for fs in report.filesystems[:5]:
                    lines.append(f"  @0x{fs.offset:08X}: {fs.description}")
            if report.security_findings:
                lines.append(f"\nSecurity Findings ({len(report.security_findings)}):")
                for finding in report.security_findings[:10]:
                    lines.append(f"  ⚠ {finding}")
            if report.entropy_plot_path:
                lines.append(f"\nEntropy plot: {report.entropy_plot_path}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[FIRMWARE] Analysis failed: {e}")

    # ── Physics ────────────────────────────────────────────────────────────────

    def _compute_physics(self, expression: str, variables: dict, output: str) -> ToolResult:
        try:
            from domains.physics.engine import PhysicsEngine
            engine = PhysicsEngine()
            result = engine.compute(expression=expression, variables=variables, output=output)
            if result.get("error"):
                return ToolResult(ok=False, content=f"[PHYSICS] {result['error']}")
            import json
            return ToolResult(ok=True, content=f"[PHYSICS]\n{json.dumps(result, indent=2, default=str)}")
        except Exception as e:
            return ToolResult(ok=False, content=f"[PHYSICS] Computation failed: {e}")

    def _simulate_physics(self, system: str, params: dict, t_span: tuple) -> ToolResult:
        try:
            from domains.physics.engine import PhysicsEngine
            engine = PhysicsEngine()
            result = engine.simulate(system=system, params=params, t_span=t_span)
            if result.get("error"):
                return ToolResult(ok=False, content=f"[PHYSICS] {result['error']}")
            import json
            return ToolResult(ok=True, content=f"[PHYSICS SIM]\n{json.dumps(result, indent=2, default=str)}")
        except Exception as e:
            return ToolResult(ok=False, content=f"[PHYSICS] Simulation failed: {e}")

    def _get_physics_constant(self, name: str) -> ToolResult:
        try:
            from domains.physics.engine import PhysicsEngine
            engine = PhysicsEngine()
            result = engine.get_constant(name)
            if result.get("error"):
                return ToolResult(ok=False, content=f"[PHYSICS] {result['error']}")
            return ToolResult(ok=True, content=f"[PHYSICS CONSTANT] {name}:\n  Value: {result['value']}\n  Units: {result['unit']}")
        except Exception as e:
            return ToolResult(ok=False, content=f"[PHYSICS] Constant lookup failed: {e}")

    # ── Robotics ───────────────────────────────────────────────────────────────

    def _robot_fk(self, joint_angles: list, robot_model: str = "ur5") -> ToolResult:
        try:
            from domains.robotics.kinematics import make_ur5, make_puma560
            arm = make_ur5() if robot_model.lower() == "ur5" else make_puma560()
            result = arm.forward_kinematics([float(a) for a in joint_angles])
            if result.error:
                return ToolResult(ok=False, content=f"[ROBOTICS FK] {result.error}")
            x, y, z = result.end_effector_position
            return ToolResult(ok=True, content=(
                f"[ROBOTICS FK] {robot_model.upper()} Forward Kinematics:\n"
                f"End Effector Position: x={x:.4f}m  y={y:.4f}m  z={z:.4f}m\n"
                f"Manipulability: {result.manipulability:.4f}\n"
                f"Singularity: {'⚠ YES' if result.singularity_detected else 'No'}"
            ))
        except Exception as e:
            return ToolResult(ok=False, content=f"[ROBOTICS FK] Failed: {e}")

    def _robot_ik(self, target_pos: tuple, robot_model: str = "ur5") -> ToolResult:
        try:
            from domains.robotics.kinematics import make_ur5, make_puma560
            import math
            arm = make_ur5() if robot_model.lower() == "ur5" else make_puma560()
            target = tuple(float(c) for c in target_pos)
            result = arm.inverse_kinematics(target)
            if result.error:
                return ToolResult(ok=False, content=f"[ROBOTICS IK] {result.error}")
            angles_deg = [math.degrees(q) for q in result.joint_angles_rad]
            x, y, z = result.end_effector_position
            error = ((x - target[0])**2 + (y - target[1])**2 + (z - target[2])**2) ** 0.5
            return ToolResult(ok=True, content=(
                f"[ROBOTICS IK] {robot_model.upper()} Inverse Kinematics:\n"
                f"Target: ({target[0]:.3f}, {target[1]:.3f}, {target[2]:.3f})m\n"
                f"Achieved: ({x:.4f}, {y:.4f}, {z:.4f})m | Error: {error*1000:.2f}mm\n"
                f"Joint angles (deg): {', '.join(f'{a:.1f}°' for a in angles_deg)}"
            ))
        except Exception as e:
            return ToolResult(ok=False, content=f"[ROBOTICS IK] Failed: {e}")

    # ── Sandbox Execution ──────────────────────────────────────────────────────

    def _run_sandboxed(self, code: str, language: str = "python", timeout: int = 30) -> ToolResult:
        try:
            import asyncio
            from core.sandbox_executor import SandboxExecutor
            executor = SandboxExecutor()
            result = asyncio.run(executor.execute(code=code, language=language, timeout_seconds=timeout))
            output_lines = [
                f"[SANDBOX] Exit: {result.exit_code} | Time: {result.execution_time_ms:.0f}ms | Runtime: {result.runtime}",
                f"--- stdout ---\n{result.stdout[:2000] or '(none)'}",
            ]
            if result.stderr:
                output_lines.append(f"--- stderr ---\n{result.stderr[:500]}")
            if result.timed_out:
                output_lines.append("⚠ TIMED OUT")
            return ToolResult(ok=result.exit_code == 0, content="\n".join(output_lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[SANDBOX] Execution failed: {e}")

    def _sandbox_status(self) -> ToolResult:
        try:
            from core.sandbox_executor import SandboxExecutor
            executor = SandboxExecutor()
            docker_ok = executor._docker_available()
            lines = [
                f"[SANDBOX] Docker available: {'YES' if docker_ok else 'NO (subprocess fallback)'}",
                f"Supported languages: Python 3, Bash, Node.js",
                f"Security: {'--network none --cap-drop ALL --read-only (memory-limited)' if docker_ok else 'Local subprocess (no isolation)'}",
                f"Max timeout: 120 seconds",
            ]
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[SANDBOX] Status check failed: {e}")

    # ── Intel Feeds ────────────────────────────────────────────────────────────

    def _intel_feed(self, days_back: int = 7) -> ToolResult:
        try:
            import asyncio
            from core.intel_feeds import get_intel_feeds
            feeds = get_intel_feeds()
            items = asyncio.run(feeds.fetch_all(days_back=days_back))
            if not items:
                return ToolResult(ok=True, content="[INTEL] No new intel items retrieved.")
            lines = [f"[INTEL FEED] {len(items)} items (last {days_back}d):"]
            for item in items[:20]:
                kev_marker = " 🔴 KEV!" if item.is_kev else ""
                lines.append(f"  [{item.severity}] [{item.source}] {item.published} {kev_marker}")
                lines.append(f"    {item.title}")
                if item.summary:
                    lines.append(f"    {item.summary[:120]}...")
                lines.append(f"    → {item.url}")
            return ToolResult(ok=True, content="\n".join(lines))
        except Exception as e:
            return ToolResult(ok=False, content=f"[INTEL] Feed fetch failed: {e}")

    # ── Cross-Domain Synthesis ─────────────────────────────────────────────────

    def _classify_domain(self, query: str) -> ToolResult:
        try:
            import asyncio
            from core.cross_domain_synthesizer import get_synthesizer
            synth = get_synthesizer()
            result = asyncio.run(synth.synthesize(query))
            return ToolResult(ok=True, content=result.synthesis)
        except Exception as e:
            return ToolResult(ok=False, content=f"[DOMAIN] Classification failed: {e}")

