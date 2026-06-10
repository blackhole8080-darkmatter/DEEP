"""
Tool Registry - Bridges IntegrationManager and AsyncBrain ToolExecutor
"""
import json
import logging
from typing import Dict, Any, List
from ..domain.interfaces import ToolExecutor
from ..domain.models import ToolResult
from ..integrations import integration_manager

logger = logging.getLogger(__name__)

class DeepToolRegistry(ToolExecutor):
    """
    Exposes available integrations as tools to the LLM.
    """
    
    def __init__(self):
        from ..academic_rag import AcademicResearchEngine
        from ..integrations.cyber_sec import CyberSecurityIntegration
        from ..integrations.vision import VisionIntegration
        from ..integrations.xr_bridge import XRBridgeIntegration
        from ..interactive_response import interactive_manager
        
        self.rag = AcademicResearchEngine()
        self.cyber = CyberSecurityIntegration()
        self.vision = VisionIntegration()
        self.xr = XRBridgeIntegration()
        self.interactive = interactive_manager
        
        from ..integrations.local_system import LocalSystem

        self.local_system = LocalSystem()  # sandboxed FS + code intelligence
        self.agent_factory = None
        self.plugin_manager = None  # set by server after plugins start; bridges plugin tools

        self.available_tools = {
            "search_web": {
                "description": "Search the live internet for up-to-date information, news, or weather.",
                "args": {"query": "The search query string"}
            },
            "investigate": {
                "description": "Build an intelligence dossier on an IP address, MAC address, hostname or domain (vendor, reverse-DNS, geolocation, ISP/ASN, private-vs-public, risk flags). Use this to identify unknown network/Bluetooth devices or remote hosts.",
                "args": {"target": "An IP (e.g. 8.8.8.8), MAC (e.g. C4:9A:31:FF:CA:A0), hostname or domain"}
            },
            "trust_device": {
                "description": "ACTION: mark a network device as trusted (whitelist it) by its MAC address. Use when the user confirms a device is theirs/safe.",
                "args": {"mac": "Device MAC address"}
            },
            "block_device": {
                "description": "ACTION (protective): flag a network device as blocked/suspicious by its MAC address. Use when the user wants to block a suspicious or unknown device.",
                "args": {"mac": "Device MAC address"}
            },
            "network_scan": {
                "description": "ACTION: actively scan a specific device/IP for open ports and OS fingerprint. Use to inspect a suspicious host more deeply.",
                "args": {"ip": "Target IP on the local network, e.g. 192.168.1.42"}
            },
            "vpn_control": {
                "description": "ACTION (protective): bring the VPN up or down. Use 'up' to secure the connection, 'down' to disconnect.",
                "args": {"action": "'up' or 'down'"}
            },
            "home_automation": {
                "description": "Control smart home devices via Home Assistant.",
                "args": {
                    "action": "'turn_on', 'turn_off', or 'get_state'",
                    "entity_id": "e.g., 'light.living_room' or 'climate.home'",
                    "brightness": "optional 0-255 for lights"
                }
            },
            "add_task": {
                "description": "Add a task/todo to the user's persistent list.",
                "args": {
                    "title": "Task description",
                    "due": "Optional ISO 8601 datetime, e.g. 2026-06-02T17:00:00",
                    "priority": "Optional: 'low', 'med', or 'high' (default 'med')"
                }
            },
            "list_tasks": {
                "description": "List the user's open (incomplete) tasks.",
                "args": {}
            },
            "complete_task": {
                "description": "Mark a task as done by its id.",
                "args": {"id": "The integer task id"}
            },
            "set_reminder": {
                "description": "Set a time-based reminder that fires (notifies + optional SMS) when due.",
                "args": {
                    "text": "What to remind the user about",
                    "at": "When to fire, as an ISO 8601 datetime, e.g. 2026-06-01T18:00:00"
                }
            },
            "list_reminders": {
                "description": "List pending (not-yet-fired) reminders.",
                "args": {}
            },
            "calendar_upcoming": {
                "description": "List the user's upcoming Google Calendar events.",
                "args": {"count": "Optional number of events to return (default 5)"}
            },
            "calendar_create_event": {
                "description": "Create an event on the user's Google Calendar.",
                "args": {
                    "title": "Event title",
                    "start": "Start time, ISO 8601 datetime",
                    "end": "Optional end time, ISO 8601 (defaults to start + 1 hour)"
                }
            },
            "get_time": {
                "description": "Get current exact date and time.",
                "args": {}
            },
            "science_compute": {
                "description": ("Run a scientific or technical computation across 16 domains "
                                "(maths, physics, quantum mechanics, chemistry, biology, "
                                "astrophysics, nuclear, ML, neural nets, quantum computing, "
                                "robotics, engineering, cybersecurity, gaming, cloud, finance). "
                                "Use for symbolic maths, simulations, option pricing, circuits, "
                                "binding energies, Black-Scholes, Grover/VQE, PINNs, etc."),
                "args": {"query": "Natural-language computation request, e.g. "
                                  "'integrate x^2 from 0 to 3' or 'black hole 10 solar masses'"}
            },
            "solve_math": {
                "description": ("Symbolic & numerical mathematics: derivatives, integrals, "
                                "limits, series, equation solving, matrices/eigenvalues, "
                                "transforms, number theory, combinatorics."),
                "args": {"query": "e.g. 'differentiate sin(x)*x^2' or 'factor 360' or "
                                  "'solve x^2 - 5x + 6 = 0'"}
            },
            "run_simulation": {
                "description": ("Run a physics/chemistry/biology/astro/nuclear/quantum "
                                "simulation: projectile, orbits, FDTD, Navier-Stokes, "
                                "Schrödinger, reactions, SIR epidemics, black holes, "
                                "reactor kinetics, Grover/VQE quantum circuits."),
                "args": {"query": "e.g. 'projectile at 45 degrees 30 m/s' or "
                                  "'run a grover search for 101' or 'SIR epidemic'"}
            },
            "quant_finance": {
                "description": ("Quantitative finance: Black-Scholes option pricing + Greeks, "
                                "Monte Carlo, portfolio optimisation, VaR/CVaR risk, MACD/"
                                "Bollinger indicators, strategy backtesting, pairs trading."),
                "args": {"query": "e.g. 'price a call option stock 105 strike 100' or "
                                  "'optimize my portfolio' or 'stock risk VaR'"}
            },
            "read_file": {
                "description": "Read a file. Optionally pass start/end line numbers to read a range (returns numbered lines).",
                "args": {"filepath": "Path to the file (absolute or relative to workspace)",
                         "start": "Optional 1-based start line", "end": "Optional end line"}
            },
            "write_file": {
                "description": "Create or fully overwrite a file. Use for NEW files; for editing existing code use edit_file instead.",
                "args": {"filepath": "Path to the file", "content": "The full text to write"}
            },
            "edit_file": {
                "description": "Surgically edit an existing file via exact find/replace (no clobbering). 'old' must match the file exactly and be unique unless replace_all is true.",
                "args": {"filepath": "Path to the file", "old": "Exact text to replace",
                         "new": "Replacement text", "replace_all": "Optional bool, replace every occurrence"}
            },
            "list_directory": {
                "description": "List all files and folders in a directory.",
                "args": {"path": "Path to the directory (absolute or relative to workspace)"}
            },
            "glob_files": {
                "description": "Find files by glob pattern (e.g. '**/*.py') under the workspace or a given path.",
                "args": {"pattern": "Glob pattern, e.g. **/*.py", "path": "Optional base directory"}
            },
            "search_code": {
                "description": "Search file contents across the codebase (grep). Returns file:line: matches. Use this to FIND code before reading/editing.",
                "args": {"query": "Text/regex to search for", "path": "Optional base directory",
                         "glob": "Optional file filter, e.g. *.py"}
            },
            "run_command": {
                "description": "Execute a terminal command on the local machine (e.g. python script.py). Use cautiously.",
                "args": {"command": "The terminal command to run"}
            },
            "cyber_scan_network": {
                "description": "Scans the local network using ARP to find connected devices.",
                "args": {}
            },
            "cyber_scan_ports": {
                "description": "Scans an IP address for open ports.",
                "args": {"ip": "The target IP address"}
            },
            "vision_screenshot": {
                "description": "Look at the user's screen RIGHT NOW: captures a screenshot and analyzes it with local AI vision (LLaVA). Use when the user asks 'what's on my screen', 'look at this', or wants DEEP to see what they're doing.",
                "args": {"question": "Optional: what to look for (default: describe the whole screen)"}
            },
            "vision_analyze": {
                "description": "Analyze an image using local AI vision (LLaVA). Understands what's in the image.",
                "args": {
                    "image_path": "Path to the image file",
                    "question": "Optional question about the image (default: describe it)"
                }
            },
            "vision_debug_ui": {
                "description": "Analyze a UI screenshot for bugs, layout issues, and UX improvements.",
                "args": {"image_path": "Path to UI screenshot"}
            },
            "vision_analyze_circuit": {
                "description": "Analyze a circuit board or electronic component image (for robotics).",
                "args": {"image_path": "Path to circuit image"}
            },
            "research_query": {
                "description": "Search the local Academic database for information extracted from PDFs.",
                "args": {"query": "The search query"}
            },
            "research_ingest": {
                "description": "Scan data/research_papers to add new PDFs into the academic database.",
                "args": {}
            },
            "xr_send_command": {
                "description": "Sends a command directly to a connected VR/AR headset running Unity/Unreal.",
                "args": {"command": "e.g., 'spawn_object', 'change_color'", "payload": "JSON dict payload"}
            },
            "agent_create": {
                "description": "Create a new specialized sub-agent with a specific role and tool access.",
                "args": {
                    "name": "Unique name for the agent",
                    "role": "'researcher', 'coder', 'cybersec', 'robotics', 'data_analyst', 'writer', 'planner', or 'custom'",
                    "custom_prompt": "Optional custom system prompt",
                    "allowed_tools": "Optional list of tool names this agent can use"
                }
            },
            "agent_assign": {
                "description": "Assign a task to an existing sub-agent and get the result.",
                "args": {
                    "agent_name": "Name of the agent to use",
                    "task": "Task description"
                }
            },
            "agent_list": {
                "description": "List all active sub-agents and their status.",
                "args": {}
            },
            "agent_terminate": {
                "description": "Terminate and remove a sub-agent.",
                "args": {"agent_name": "Name of the agent to terminate"}
            },
            "agent_swarm": {
                "description": "Execute a complex goal by auto-decomposing it into sub-tasks and running multiple agents in parallel.",
                "args": {"goal": "High-level goal description"}
            },
            "ask_options": {
                "description": "Present multiple options/alternatives to the user for selection. Use when there are multiple valid approaches.",
                "args": {
                    "message": "Question or context for the options",
                    "options": "List of dicts with label, description, pros, cons, recommended"
                }
            },
            "ask_clarification": {
                "description": "Ask clarifying questions before proceeding. Use when you need more information from the user.",
                "args": {
                    "message": "Context message",
                    "questions": "List of dicts with question, context, required, suggestions"
                }
            },
            "ask_confirmation": {
                "description": "Ask for yes/no confirmation before taking an action.",
                "args": {
                    "message": "What you're asking about",
                    "action": "The action that will be taken if confirmed"
                }
            },
            # ---- Machine learning: knowledge + real model training ----
            "ml_list": {
                "description": "List every ML algorithm Deep knows, grouped by family.",
                "args": {}
            },
            "ml_explain": {
                "description": "Explain one ML algorithm: what it does, when to use it, and the library.",
                "args": {"query": "Algorithm name, e.g. 'xgboost', 'lstm', 'dbscan'"}
            },
            "ml_recommend": {
                "description": "Recommend the best ML algorithm(s) for a described problem.",
                "args": {"problem": "e.g. 'detect anomalies in network traffic'"}
            },
            "ml_runnable": {
                "description": "List which ML algorithms Deep can actually TRAIN/RUN right now.",
                "args": {}
            },
            "ml_train": {
                "description": "Train a real ML model via scikit-learn/XGBoost. Data is a CSV path OR 'internal:processes'/'internal:network'. Supervised algos need a target column.",
                "args": {
                    "algorithm": "e.g. 'random_forest', 'xgboost', 'kmeans', 'isolation_forest'",
                    "data": "CSV path or 'internal:processes' / 'internal:network'",
                    "target": "Target column name (supervised only)",
                    "params": "Optional JSON object of hyperparameters, e.g. {\"n_clusters\": 3}",
                    "save_as": "Optional name to save the trained model under"
                }
            },
            "ml_predict": {
                "description": "Predict using a previously trained+saved model.",
                "args": {"model_name": "Saved model name", "data": "CSV path or 'internal:...'"}
            },
            # ---- Layer 3: models of Aryan himself ----
            "predict_my_tasks": {
                "description": "Score Aryan's OPEN tasks by how likely he is to complete each, learned from his own task history. Trains on first use. Use to surface which tasks are at risk / need a nudge.",
                "args": {}
            },
            "train_task_model": {
                "description": "(Re)train the personal task-completion model from the latest scheduler history.",
                "args": {}
            }
        }
        
    def describe_tools(self) -> str:
        desc = "AVAILABLE TOOLS:\n"
        for name, info in self.available_tools.items():
            args_str = json.dumps(info['args'])
            desc += f"- {name}: {info['description']} | Args: {args_str}\n"
        desc += "\nTo use a tool, YOU MUST output ONLY this exact format: [TOOL:{\"name\": \"tool_name\", \"args\": {\"arg\": \"value\"}}]"
        return desc
        
    _deep_orchestrator = None

    def _science_compute(self, query: str) -> dict:
        """Route a natural-language request through the DEEP science/tech engine."""
        try:
            if DeepToolRegistry._deep_orchestrator is None:
                from engine.main import DEEP  # lazy import; heavy science deps
                DeepToolRegistry._deep_orchestrator = DEEP()
            return DeepToolRegistry._deep_orchestrator.process_command(query)
        except Exception as e:  # noqa: BLE001
            logger.exception("science_compute failed")
            return {"result": None, "verbal": f"Science engine error: {e}", "module": None}

    def list_tools(self) -> List[str]:
        return list(self.available_tools.keys())
        
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        import asyncio
        from datetime import datetime
        logger.info(f"[TOOL] Executing {tool_name} with {args}")
        
        try:
            if tool_name == "get_time":
                return ToolResult(True, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tool_name)

            elif tool_name in ("science_compute", "solve_math", "run_simulation", "quant_finance"):
                query = args.get("query", "")
                if not query:
                    return ToolResult(False, "Missing query", tool_name)
                # All four route through the DEEP Engineering-Bible engine; the
                # distinct tool names just give the LLM clearer affordances.
                out = await asyncio.to_thread(self._science_compute, query)
                return ToolResult(out.get("module") is not None or out.get("result") is not None,
                                  out.get("verbal", "No result."), tool_name)


            elif tool_name == "search_web":
                query = args.get("query", "")
                if not query: return ToolResult(False, "Missing query", tool_name)

                # 1. Brave if configured (richest)
                if integration_manager.p1_loaded and integration_manager.get("brave_search"):
                    try:
                        bs = integration_manager.get("brave_search")
                        res = await bs.quick_answer(query)
                        return ToolResult(True, str(res), tool_name)
                    except Exception:
                        pass

                # 2. Real DuckDuckGo search — no API key required
                def _ddg(q):
                    try:
                        from ddgs import DDGS                       # current package
                        return list(DDGS().text(q, max_results=5))
                    except Exception:
                        from duckduckgo_search import DDGS          # legacy fallback
                        with DDGS() as d:
                            return list(d.text(q, max_results=5))
                try:
                    results = await asyncio.wait_for(asyncio.to_thread(_ddg, query), timeout=15)
                    if results:
                        lines = []
                        for i, r in enumerate(results):
                            lines.append(f"{i+1}. {r.get('title','')}\n   {str(r.get('body','')).strip()[:220]}\n   {r.get('href','')}")
                        return ToolResult(True, f"Live web results for '{query}':\n\n" + "\n\n".join(lines), tool_name)
                except Exception as e:
                    logger.debug(f"DDG search failed: {e}")

                return ToolResult(False, f"Web search for '{query}' returned no results (search backend unavailable right now).", tool_name)

            elif tool_name == "investigate":
                target = args.get("target", "") or args.get("ip", "") or args.get("mac", "")
                if not target:
                    return ToolResult(False, "Missing target (IP/MAC/host/domain)", tool_name)
                import asyncio as _asyncio, json as _json
                from network.investigator import investigate as _investigate
                dossier = await _asyncio.to_thread(_investigate, str(target))
                summary = dossier.get("summary", "")
                findings = "; ".join(f"{f['label']}: {f['value']}" for f in dossier.get("findings", []))
                return ToolResult(True, f"{summary}\n{findings}" if findings else summary, tool_name)

            elif tool_name in ("trust_device", "block_device", "network_scan", "vpn_control"):
                # Human-in-the-loop: destructive/irreversible actions are parked
                # for your approval instead of executing immediately.
                _is_destructive = (tool_name == "block_device") or \
                                  (tool_name == "vpn_control" and str(args.get("action", "")).lower() == "down")
                if _is_destructive and not args.get("_approved"):
                    from core.pending_actions import enqueue
                    label = ("Block device " + str(args.get("mac", "?"))) if tool_name == "block_device" \
                            else "Disconnect the VPN"
                    enqueue(tool_name, {k: v for k, v in args.items() if k != "_approved"}, label,
                            detail="Protective action — needs your confirmation.")
                    return ToolResult(True, f"⏳ This action needs your confirmation: {label}. "
                                            f"I've sent it to your Approvals panel — approve it there and I'll proceed.", tool_name)

                # ACTION tools — DEEP executes against the local control API.
                import httpx as _httpx
                BASE = "http://localhost:7768"
                try:
                    async with _httpx.AsyncClient(timeout=25) as _c:
                        if tool_name == "trust_device":
                            mac = args.get("mac", "")
                            if not mac: return ToolResult(False, "Missing mac", tool_name)
                            r = await _c.post(f"{BASE}/api/security/trust", json={"mac": mac})
                            ok = r.json().get("success")
                            return ToolResult(bool(ok), f"Device {mac} marked TRUSTED." if ok else "Trust failed.", tool_name)
                        if tool_name == "block_device":
                            mac = args.get("mac", "")
                            if not mac: return ToolResult(False, "Missing mac", tool_name)
                            r = await _c.post(f"{BASE}/api/security/block", json={"mac": mac})
                            ok = r.json().get("success")
                            return ToolResult(bool(ok), f"Device {mac} BLOCKED / flagged suspicious." if ok else "Block failed.", tool_name)
                        if tool_name == "network_scan":
                            ip = args.get("ip", "")
                            if not ip: return ToolResult(False, "Missing ip", tool_name)
                            r = await _c.post(f"{BASE}/network/scan/{ip}")
                            return ToolResult(True, f"Scan of {ip}: {str(r.json())[:300]}", tool_name)
                        if tool_name == "vpn_control":
                            act = str(args.get("action", "")).lower()
                            if act not in ("up", "down"): return ToolResult(False, "action must be 'up' or 'down'", tool_name)
                            r = await _c.post(f"{BASE}/network/vpn/{act}")
                            return ToolResult(True, f"VPN {act.upper()} requested: {str(r.json())[:200]}", tool_name)
                except Exception as _e:
                    return ToolResult(False, f"Action '{tool_name}' failed: {_e}", tool_name)

            elif tool_name == "home_automation":
                action = args.get("action")
                entity = args.get("entity_id", "")
                
                if integration_manager.p0_loaded and integration_manager.get("home_assistant"):
                    ha = integration_manager.get("home_assistant")
                    if action == "get_state":
                        state = await ha.get_state(entity)
                        return ToolResult(True, f"State of {entity}: {state}", tool_name)
                    else:
                        svc_data = {"entity_id": entity}
                        if args.get("brightness"):
                            svc_data["brightness"] = args["brightness"]
                        domain = entity.split(".")[0] if "." in entity else "homeassistant"
                        res = await ha.call_service(domain, action, svc_data)
                        return ToolResult(res.success, f"Executed {action} on {entity}. Result: {res.data or res.error}", tool_name)
                
                return ToolResult(True, f"Successfully simulated '{action}' on '{entity}'. (Home Assistant token required in .env)", tool_name)
                
            elif tool_name in (
                "add_task", "list_tasks", "complete_task", "set_reminder",
                "list_reminders", "calendar_upcoming", "calendar_create_event",
            ):
                sched = self.plugin_manager.get_plugin("scheduler") if self.plugin_manager else None
                if sched is None:
                    return ToolResult(False, "Scheduler plugin is not loaded.", tool_name)

                res = None
                if tool_name == "add_task":
                    res = await sched.add_task(
                        args.get("title", ""), args.get("due"), args.get("priority", "med"))
                elif tool_name == "list_tasks":
                    tasks = await sched.get_open_tasks()
                    if not tasks:
                        return ToolResult(True, "No open tasks.", tool_name)
                    lines = [
                        f"#{t['id']} [{t['priority']}] {t['title']}"
                        + (f" (due {t['due']})" if t.get('due') else "")
                        for t in tasks
                    ]
                    return ToolResult(True, "Open tasks:\n" + "\n".join(lines), tool_name)
                elif tool_name == "complete_task":
                    try:
                        res = await sched.complete_task(int(args.get("id")))
                    except (TypeError, ValueError):
                        return ToolResult(False, "id must be an integer.", tool_name)
                elif tool_name == "set_reminder":
                    res = await sched.add_reminder(args.get("text", ""), args.get("at", ""))
                elif tool_name == "list_reminders":
                    rems = await sched.get_pending_reminders()
                    if not rems:
                        return ToolResult(True, "No pending reminders.", tool_name)
                    lines = [f"#{r['id']} {r['text']} @ {r['fire_at']}" for r in rems]
                    return ToolResult(True, "Pending reminders:\n" + "\n".join(lines), tool_name)
                elif tool_name == "calendar_upcoming":
                    try:
                        count = int(args.get("count", 5))
                    except (TypeError, ValueError):
                        count = 5
                    res = await sched.calendar_upcoming(count)
                elif tool_name == "calendar_create_event":
                    res = await sched.calendar_create_event(
                        args.get("title", ""), args.get("start", ""), args.get("end"))

                if isinstance(res, dict) and res.get("error"):
                    return ToolResult(False, str(res["error"]), tool_name)
                return ToolResult(True, json.dumps(res), tool_name)

            elif tool_name == "read_file":
                def _as_int(v):
                    try:
                        return int(v)
                    except (TypeError, ValueError):
                        return None
                content = await self.local_system.read_file(
                    args.get("filepath", ""), _as_int(args.get("start")), _as_int(args.get("end")))
                ok = not content.startswith("ERROR")
                return ToolResult(ok, content, tool_name)

            elif tool_name == "write_file":
                res = await self.local_system.write_file(
                    args.get("filepath", ""), args.get("content", ""))
                return ToolResult(not res.startswith("ERROR"), res, tool_name)

            elif tool_name == "edit_file":
                ra = args.get("replace_all")
                replace_all = ra in (True, "true", "True", "1", 1)
                res = await self.local_system.edit_file(
                    args.get("filepath", ""), args.get("old", ""),
                    args.get("new", ""), replace_all)
                return ToolResult(not res.startswith("ERROR"), res, tool_name)

            elif tool_name == "list_directory":
                res = await self.local_system.list_directory(args.get("path", "."))
                return ToolResult(not res.startswith("ERROR"), str(res), tool_name)

            elif tool_name == "glob_files":
                res = await self.local_system.glob_files(
                    args.get("pattern", "*"), args.get("path"))
                return ToolResult(not res.startswith("ERROR"), res, tool_name)

            elif tool_name == "search_code":
                res = await self.local_system.search_code(
                    args.get("query", ""), args.get("path"), args.get("glob"))
                return ToolResult(not res.startswith("ERROR"), res, tool_name)

            elif tool_name == "run_command":
                cmd = args.get("command", "")
                res = await self.local_system.run_command(cmd)
                output = f"Exit code: {res['exit_code']}\nSTDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}"
                return ToolResult(res["exit_code"] == 0, output, tool_name)
                
            elif tool_name == "cyber_scan_network":
                res = await self.cyber.scan_network_arp()
                return ToolResult(True, res, tool_name)
                
            elif tool_name == "cyber_scan_ports":
                ip = args.get("ip", "")
                res = await self.cyber.scan_ports(ip)
                return ToolResult(True, res, tool_name)
                
            elif tool_name == "vision_screenshot":
                import os as _os
                path = await self.vision.take_screenshot()
                if not isinstance(path, str) or not path.lower().endswith(".png") or not _os.path.exists(path):
                    return ToolResult(False, f"Could not capture the screen: {path}", tool_name)
                from ..integrations.vision_llava import llava_vision
                q = args.get("question") or "Describe what is currently on the screen — the apps/windows open and any notable content."
                analysis = await llava_vision.analyze_image(path, q)
                return ToolResult(True, f"[Screen captured -> {path}]\n\n{analysis}", tool_name)
                
            elif tool_name == "vision_analyze":
                from ..integrations.vision_llava import llava_vision
                image_path = args.get("image_path", "")
                question = args.get("question", "Describe this image in detail")
                analysis = await llava_vision.analyze_image(image_path, question)
                return ToolResult(True, analysis, tool_name)
                
            elif tool_name == "vision_debug_ui":
                from ..integrations.vision_llava import llava_vision
                image_path = args.get("image_path", "")
                analysis = await llava_vision.debug_ui(image_path)
                return ToolResult(True, analysis, tool_name)
                
            elif tool_name == "vision_analyze_circuit":
                from ..integrations.vision_llava import llava_vision
                image_path = args.get("image_path", "")
                analysis = await llava_vision.analyze_circuit(image_path)
                return ToolResult(True, analysis, tool_name)
                
            elif tool_name == "research_ingest":
                res = self.rag.ingest_directory()
                return ToolResult(True, res, tool_name)
                
            elif tool_name == "research_query":
                query = args.get("query", "")
                res = self.rag.query_research(query)
                return ToolResult(True, res, tool_name)
                
            elif tool_name == "xr_send_command":
                cmd = args.get("command", "")
                payload = args.get("payload", {})
                res = await self.xr.send_to_xr(cmd, payload)
                return ToolResult(True, res, tool_name)
                
            elif tool_name == "agent_create":
                if not self.agent_factory:
                    return ToolResult(False, "Agent Factory not initialized. Contact system admin.", tool_name)
                name = args.get("name", "")
                role = args.get("role", "custom")
                custom_prompt = args.get("custom_prompt")
                allowed_tools = args.get("allowed_tools")
                try:
                    agent = self.agent_factory.create_agent(name, role, custom_prompt, allowed_tools)
                    return ToolResult(True, f"Created agent '{name}' with role '{role}'. ID: {agent.id}", tool_name)
                except Exception as e:
                    return ToolResult(False, f"Failed to create agent: {e}", tool_name)
                    
            elif tool_name == "agent_assign":
                if not self.agent_factory:
                    return ToolResult(False, "Agent Factory not initialized.", tool_name)
                agent_name = args.get("agent_name", "")
                task = args.get("task", "")
                result = await self.agent_factory.assign_task(agent_name, task)
                return ToolResult(True, json.dumps(result, indent=2), tool_name)
                
            elif tool_name == "agent_list":
                if not self.agent_factory:
                    return ToolResult(False, "Agent Factory not initialized.", tool_name)
                agents = self.agent_factory.list_agents()
                stats = self.agent_factory.stats()
                output = f"Active Agents: {len(agents)}\n\n"
                for a in agents:
                    output += f"- {a['name']} ({a['role']}) - Status: {a['status']} - Tasks: {a['tasks_completed']}/{a['tasks_total']}\n"
                output += f"\nStats: {json.dumps(stats)}"
                return ToolResult(True, output, tool_name)
                
            elif tool_name == "agent_terminate":
                if not self.agent_factory:
                    return ToolResult(False, "Agent Factory not initialized.", tool_name)
                agent_name = args.get("agent_name", "")
                success = self.agent_factory.terminate_agent(agent_name)
                if success:
                    return ToolResult(True, f"Terminated agent '{agent_name}'.", tool_name)
                return ToolResult(False, f"Agent '{agent_name}' not found.", tool_name)
                
            elif tool_name == "agent_swarm":
                if not self.agent_factory:
                    return ToolResult(False, "Agent Factory not initialized.", tool_name)
                goal = args.get("goal", "")
                result = await self.agent_factory.swarm_execute(goal)
                return ToolResult(True, json.dumps(result, indent=2), tool_name)
                
            elif tool_name == "ask_options":
                message = args.get("message", "")
                options = args.get("options", [])
                if not isinstance(options, list):
                    return ToolResult(False, "Options must be a list", tool_name)
                response = self.interactive.create_and_store("options", message, options)
                return ToolResult(True, f"[INTERACTIVE_RESPONSE:{response.to_json()}]", tool_name)
                
            elif tool_name == "ask_clarification":
                message = args.get("message", "")
                questions = args.get("questions", [])
                if not isinstance(questions, list):
                    return ToolResult(False, "Questions must be a list", tool_name)
                response = self.interactive.create_and_store("clarification", message, questions)
                return ToolResult(True, f"[INTERACTIVE_RESPONSE:{response.to_json()}]", tool_name)
                
            elif tool_name == "ask_confirmation":
                message = args.get("message", "")
                action = args.get("action", "")
                response = self.interactive.create_and_store("confirmation", message, [{"action": action}])
                return ToolResult(True, f"[INTERACTIVE_RESPONSE:{response.to_json()}]", tool_name)
                
            elif tool_name in ("ml_list", "ml_explain", "ml_recommend"):
                try:
                    from ...ai import ml_catalog
                except ImportError:
                    from ai import ml_catalog
                if tool_name == "ml_list":
                    return ToolResult(True, ml_catalog.list_all(), tool_name)
                if tool_name == "ml_explain":
                    return ToolResult(True, ml_catalog.explain(args.get("query", "")), tool_name)
                return ToolResult(True, ml_catalog.recommend(args.get("problem", "")), tool_name)

            elif tool_name == "ml_runnable":
                try:
                    from ...ai import ml_runner
                except ImportError:
                    from ai import ml_runner
                algos = ml_runner.runnable_algorithms()
                return ToolResult(True, "Trainable now: " + ", ".join(algos), tool_name)

            elif tool_name == "ml_train":
                try:
                    from ...ai import ml_runner
                except ImportError:
                    from ai import ml_runner
                df, err = self._ml_resolve_dataset(args.get("data", ""))
                if err:
                    return ToolResult(False, err, tool_name)
                params = args.get("params")
                if isinstance(params, str):
                    params = json.loads(params) if params.strip() else None
                if params is not None and not isinstance(params, dict):
                    return ToolResult(False, "params must be a JSON object, e.g. {\"n_clusters\": 3}", tool_name)
                report = ml_runner.train(
                    df, args.get("algorithm", ""), target=args.get("target") or None,
                    params=params, save_as=args.get("save_as") or None,
                    models_dir=self._ml_models_dir(),
                )
                return ToolResult(True, report, tool_name)

            elif tool_name == "ml_predict":
                try:
                    from ...ai import ml_runner
                except ImportError:
                    from ai import ml_runner
                df, err = self._ml_resolve_dataset(args.get("data", ""))
                if err:
                    return ToolResult(False, err, tool_name)
                report = ml_runner.predict(df, args.get("model_name", ""), self._ml_models_dir())
                return ToolResult(True, report, tool_name)

            elif tool_name in ("predict_my_tasks", "train_task_model"):
                try:
                    from ...ai import personal_models
                except ImportError:
                    from ai import personal_models
                db_path = self._scheduler_db_path()
                if tool_name == "train_task_model":
                    return ToolResult(True, personal_models.train_task_completion(db_path, self._ml_models_dir()), tool_name)
                return ToolResult(True, personal_models.predict_task_completion(db_path, self._ml_models_dir()), tool_name)

            else:
                return ToolResult(False, f"Unknown tool: {tool_name}", tool_name)

        except Exception as e:
            logger.error(f"[TOOL ERROR] {e}")
            return ToolResult(False, str(e), tool_name, str(e))

    # ---- ML helpers ----

    def _ml_models_dir(self) -> str:
        import os
        d = os.path.join("data", "ml_models")
        os.makedirs(d, exist_ok=True)
        return d

    def _scheduler_db_path(self) -> str:
        """Locate the scheduler SQLite DB (via the loaded plugin if available)."""
        import os
        sched = self.plugin_manager.get_plugin("scheduler") if self.plugin_manager else None
        path = getattr(sched, "db_path", None)
        return path or os.path.join("data", "scheduler.db")

    def _ml_resolve_dataset(self, data: str):
        """Resolve a data spec to a DataFrame. Supports CSV paths and internal sources.

        Returns (DataFrame, error_message); exactly one is non-None.
        """
        import os
        import pandas as pd
        spec = (data or "").strip()
        if not spec:
            return None, "No data source. Use a CSV path or 'internal:processes' / 'internal:network'."

        if spec.lower().startswith("internal:"):
            import psutil
            source = spec.split(":", 1)[1].strip().lower()
            if source == "processes":
                rows = []
                for p in psutil.process_iter(['pid', 'cpu_percent', 'memory_percent', 'num_threads']):
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
                            "family": int(c.family), "type": int(c.type),
                            "local_port": c.laddr.port if c.laddr else 0,
                            "remote_port": c.raddr.port if c.raddr else 0,
                            "pid": c.pid or 0,
                        })
                    except Exception:
                        continue
                return pd.DataFrame(rows), None
            return None, f"Unknown internal source '{source}'. Available: processes, network."

        if not os.path.exists(spec):
            return None, f"CSV not found: '{spec}'."
        try:
            return pd.read_csv(spec), None
        except Exception as e:
            return None, f"Failed to read CSV '{spec}': {e}"