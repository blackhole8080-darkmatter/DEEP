"""
core/tools/legacy.py

This module encapsulates the legacy tool registry.
It dynamically wraps all unmigrated tools into the modern @tool decorator registry.
"""
import asyncio
import json
import logging
from typing import Dict, Any

from core.domain.models import ToolResult
from core.tools.registry import tool, TOOL_SPECS
from core.integrations import integration_manager

logger = logging.getLogger(__name__)

LEGACY_TOOLS = {'search_web': {'description': 'Search the live internet for up-to-date information, news, or weather.', 'args': {'query': 'The search query string'}}, 'investigate': {'description': 'Build an intelligence dossier on an IP address, MAC address, hostname or domain (vendor, reverse-DNS, geolocation, ISP/ASN, private-vs-public, risk flags). Use this to identify unknown network/Bluetooth devices or remote hosts.', 'args': {'target': 'An IP (e.g. 8.8.8.8), MAC (e.g. C4:9A:31:FF:CA:A0), hostname or domain'}}, 'trust_device': {'description': 'ACTION: mark a network device as trusted (whitelist it) by its MAC address. Use when the user confirms a device is theirs/safe.', 'args': {'mac': 'Device MAC address'}}, 'block_device': {'description': 'ACTION (protective): flag a network device as blocked/suspicious by its MAC address. Use when the user wants to block a suspicious or unknown device.', 'args': {'mac': 'Device MAC address'}}, 'network_scan': {'description': 'ACTION: actively scan a specific device/IP for open ports and OS fingerprint. Use to inspect a suspicious host more deeply.', 'args': {'ip': 'Target IP on the local network, e.g. 192.168.1.42'}}, 'vpn_control': {'description': "ACTION (protective): bring the VPN up or down. Use 'up' to secure the connection, 'down' to disconnect.", 'args': {'action': "'up' or 'down'"}}, 'home_automation': {'description': 'Control smart home devices via Home Assistant.', 'args': {'action': "'turn_on', 'turn_off', or 'get_state'", 'entity_id': "e.g., 'light.living_room' or 'climate.home'", 'brightness': 'optional 0-255 for lights'}}, 'add_task': {'description': "Add a task/todo to the user's persistent list.", 'args': {'title': 'Task description', 'due': 'Optional ISO 8601 datetime, e.g. 2026-06-02T17:00:00', 'priority': "Optional: 'low', 'med', or 'high' (default 'med')"}}, 'list_tasks': {'description': "List the user's open (incomplete) tasks.", 'args': {}}, 'complete_task': {'description': 'Mark a task as done by its id.', 'args': {'id': 'The integer task id'}}, 'set_reminder': {'description': 'Set a time-based reminder that fires (notifies + optional SMS) when due.', 'args': {'text': 'What to remind the user about', 'at': 'When to fire, as an ISO 8601 datetime, e.g. 2026-06-01T18:00:00'}}, 'list_reminders': {'description': 'List pending (not-yet-fired) reminders.', 'args': {}}, 'calendar_upcoming': {'description': "List the user's upcoming Google Calendar events.", 'args': {'count': 'Optional number of events to return (default 5)'}}, 'calendar_create_event': {'description': "Create an event on the user's Google Calendar.", 'args': {'title': 'Event title', 'start': 'Start time, ISO 8601 datetime', 'end': 'Optional end time, ISO 8601 (defaults to start + 1 hour)'}}, 'science_compute': {'description': 'Run a scientific or technical computation across 16 domains (maths, physics, quantum mechanics, chemistry, biology, astrophysics, nuclear, ML, neural nets, quantum computing, robotics, engineering, cybersecurity, gaming, cloud, finance). Use for symbolic maths, simulations, option pricing, circuits, binding energies, Black-Scholes, Grover/VQE, PINNs, etc.', 'args': {'query': "Natural-language computation request, e.g. 'integrate x^2 from 0 to 3' or 'black hole 10 solar masses'"}}, 'solve_math': {'description': 'Symbolic & numerical mathematics: derivatives, integrals, limits, series, equation solving, matrices/eigenvalues, transforms, number theory, combinatorics.', 'args': {'query': "e.g. 'differentiate sin(x)*x^2' or 'factor 360' or 'solve x^2 - 5x + 6 = 0'"}}, 'run_simulation': {'description': 'Run a physics/chemistry/biology/astro/nuclear/quantum simulation: projectile, orbits, FDTD, Navier-Stokes, Schrödinger, reactions, SIR epidemics, black holes, reactor kinetics, Grover/VQE quantum circuits.', 'args': {'query': "e.g. 'projectile at 45 degrees 30 m/s' or 'run a grover search for 101' or 'SIR epidemic'"}}, 'quant_finance': {'description': 'Quantitative finance: Black-Scholes option pricing + Greeks, Monte Carlo, portfolio optimisation, VaR/CVaR risk, MACD/Bollinger indicators, strategy backtesting, pairs trading.', 'args': {'query': "e.g. 'price a call option stock 105 strike 100' or 'optimize my portfolio' or 'stock risk VaR'"}}, 'cyber_scan_network': {'description': 'Scans the local network using ARP to find connected devices.', 'args': {}}, 'cyber_scan_ports': {'description': 'Scans an IP address for open ports.', 'args': {'ip': 'The target IP address'}}, 'vision_screenshot': {'description': "Look at the user's screen RIGHT NOW: captures a screenshot and analyzes it with local AI vision (LLaVA). Use when the user asks 'what's on my screen', 'look at this', or wants DEEP to see what they're doing.", 'args': {'question': 'Optional: what to look for (default: describe the whole screen)'}}, 'vision_analyze': {'description': "Analyze an image using local AI vision (LLaVA). Understands what's in the image.", 'args': {'image_path': 'Path to the image file', 'question': 'Optional question about the image (default: describe it)'}}, 'vision_debug_ui': {'description': 'Analyze a UI screenshot for bugs, layout issues, and UX improvements.', 'args': {'image_path': 'Path to UI screenshot'}}, 'vision_analyze_circuit': {'description': 'Analyze a circuit board or electronic component image (for robotics).', 'args': {'image_path': 'Path to circuit image'}}, 'research_query': {'description': 'Search the local Academic database for information extracted from PDFs.', 'args': {'query': 'The search query'}}, 'research_ingest': {'description': 'Scan data/research_papers to add new PDFs into the academic database.', 'args': {}}, 'xr_send_command': {'description': 'Sends a command directly to a connected VR/AR headset running Unity/Unreal.', 'args': {'command': "e.g., 'spawn_object', 'change_color'", 'payload': 'JSON dict payload'}}, 'agent_create': {'description': 'Create a new specialized sub-agent with a specific role and tool access.', 'args': {'name': 'Unique name for the agent', 'role': "'researcher', 'coder', 'cybersec', 'robotics', 'data_analyst', 'writer', 'planner', or 'custom'", 'custom_prompt': 'Optional custom system prompt', 'allowed_tools': 'Optional list of tool names this agent can use'}}, 'agent_assign': {'description': 'Assign a task to an existing sub-agent and get the result.', 'args': {'agent_name': 'Name of the agent to use', 'task': 'Task description'}}, 'agent_list': {'description': 'List all active sub-agents and their status.', 'args': {}}, 'agent_terminate': {'description': 'Terminate and remove a sub-agent.', 'args': {'agent_name': 'Name of the agent to terminate'}}, 'agent_swarm': {'description': 'Execute a complex goal by auto-decomposing it into sub-tasks and running multiple agents in parallel.', 'args': {'goal': 'High-level goal description'}}, 'ask_options': {'description': 'Present multiple options/alternatives to the user for selection. Use when there are multiple valid approaches.', 'args': {'message': 'Question or context for the options', 'options': 'List of dicts with label, description, pros, cons, recommended'}}, 'ask_clarification': {'description': 'Ask clarifying questions before proceeding. Use when you need more information from the user.', 'args': {'message': 'Context message', 'questions': 'List of dicts with question, context, required, suggestions'}}, 'ask_confirmation': {'description': 'Ask for yes/no confirmation before taking an action.', 'args': {'message': "What you're asking about", 'action': 'The action that will be taken if confirmed'}}, 'ml_train': {'description': "Train a real ML model via scikit-learn/XGBoost. Data is a CSV path OR 'internal:processes'/'internal:network'. Supervised algos need a target column.", 'args': {'algorithm': "e.g. 'random_forest', 'xgboost', 'kmeans', 'isolation_forest'", 'data': "CSV path or 'internal:processes' / 'internal:network'", 'target': 'Target column name (supervised only)', 'params': 'Optional JSON object of hyperparameters, e.g. {"n_clusters": 3}', 'save_as': 'Optional name to save the trained model under'}}, 'ml_predict': {'description': 'Predict using a previously trained+saved model.', 'args': {'model_name': 'Saved model name', 'data': "CSV path or 'internal:...'"}}, 'predict_my_tasks': {'description': "Score Aryan's OPEN tasks by how likely he is to complete each, learned from his own task history. Trains on first use. Use to surface which tasks are at risk / need a nudge.", 'args': {}}, 'train_task_model': {'description': '(Re)train the personal task-completion model from the latest scheduler history.', 'args': {}}, 'add_transaction': {'description': 'Record a financial transaction (income or expense). DEEP auto-categorises based on description keywords.', 'args': {'date': 'YYYY-MM-DD', 'amount': 'Positive for income, negative for expense', 'description': "e.g. 'ICA Supermarket' or 'Salary June'", 'category': 'Optional override (auto-detected if omitted)', 'currency': 'Default SEK'}}, 'spending_summary': {'description': 'Get a spending breakdown by category for the last N months with net income/spent.', 'args': {'months': 'Default 1'}}, 'set_budget': {'description': 'Set a monthly budget limit for a spending category.', 'args': {'category': "e.g. 'food'", 'limit': 'Amount', 'currency': 'Default SEK'}}, 'get_budget_status': {'description': 'Show current spend vs budget for every category this month.', 'args': {}}, 'add_bill': {'description': 'Track a recurring bill or subscription with due date and frequency.', 'args': {'name': "e.g. 'Netflix'", 'amount': 'Amount', 'frequency': 'monthly/weekly/yearly (default monthly)', 'next_due': 'YYYY-MM-DD (optional, defaults to 30 days)'}}, 'upcoming_bills': {'description': 'List bills due within the next N days.', 'args': {'days': 'Default 14'}}, 'detect_spending_anomalies': {'description': 'Find unusual transactions that deviate from historical patterns in a category.', 'args': {'category': 'Optional: check one category; default checks all'}}, 'inbox_summary': {'description': 'Check unread count and recent email subjects.', 'args': {'limit': 'Number of recent messages (default 20)'}}, 'search_emails': {'description': 'Search inbox by sender, subject, or body keyword.', 'args': {'query': 'Search term', 'limit': 'Default 10'}}, 'send_email': {'description': 'Send an email via SMTP.', 'args': {'to': 'Recipient address', 'subject': 'Email subject', 'body': 'Email body (plain text)'}}, 'track_email': {'description': 'Flag an email thread as needing a reply (follow-up tracking).', 'args': {'msg_id': 'Message ID', 'sender': 'Sender address', 'subject': 'Subject line', 'notes': 'Optional reminder note'}}, 'awaiting_replies': {'description': "List email threads you've flagged as needing a reply.", 'args': {}}, 'create_mission': {'description': 'Start a complex, multi-step autonomous mission that DEEP executes in the background over minutes or hours. Examples: research a topic, plan a trip, audit a codebase, generate a report.', 'args': {'goal': "High-level mission description, e.g. 'Research quantum AI and write a blog summary'"}}, 'list_missions': {'description': 'List active and recent autonomous missions with their progress.', 'args': {'status': 'Optional filter: pending, running, completed, failed'}}, 'mission_status': {'description': 'Get detailed status of a specific mission including subtasks.', 'args': {'mission_id': 'The mission ID'}}, 'cancel_mission': {'description': 'Cancel an in-progress mission.', 'args': {'mission_id': 'The mission ID'}}, 'phone_status': {'description': 'Check whether DEEP can control the phone: lists connected Android devices (adb) and iPhone shortcut readiness. Use FIRST before other phone tools.', 'args': {}}, 'phone_connect': {'description': "Connect to an Android phone over Wi-Fi (wireless ADB) at host:port, e.g. '192.168.1.42:5555' or the port shown under Wireless debugging. Makes it the active device for subsequent phone tools. Run phone_pair first on Android 11+ if not already paired.", 'args': {'address': 'host:port, e.g. 192.168.1.42:5555'}}, 'phone_pair': {'description': "Android 11+ one-time wireless pairing. Use the host:port and 6-digit code from Settings → Developer options → Wireless debugging → 'Pair device with pairing code'. After pairing, use phone_connect with the (different) connect port.", 'args': {'address': 'pairing host:port', 'code': '6-digit pairing code'}}, 'phone_screenshot': {'description': "Capture the Android phone's screen RIGHT NOW and look at it with local AI vision (LLaVA). Use to see what's on the phone before deciding where to tap. Returns a description + the saved frame path.", 'args': {'question': 'Optional: what to look for on the phone screen'}}, 'phone_tap': {'description': 'Tap the Android phone screen at pixel coordinates (x, y). Get coordinates by calling phone_screenshot first.', 'args': {'x': 'X pixel', 'y': 'Y pixel'}}, 'phone_swipe': {'description': 'Swipe/scroll on the Android phone from (x1,y1) to (x2,y2). Use for scrolling, unlocking, or dragging.', 'args': {'x1': 'start X', 'y1': 'start Y', 'x2': 'end X', 'y2': 'end Y', 'duration_ms': 'Optional swipe duration in ms (default 300)'}}, 'phone_text': {'description': 'Type text into the currently focused field on the Android phone.', 'args': {'text': 'The text to type'}}, 'phone_key': {'description': 'Press a hardware/navigation key on the Android phone. Accepts aliases: home, back, enter, recents, power, wake, volup, voldown, search, del, space — or any raw KEYCODE_*.', 'args': {'key': "e.g. 'back', 'home', 'enter'"}}, 'phone_open_app': {'description': 'Launch an app on the Android phone by its package name (e.g. com.whatsapp, com.android.chrome).', 'args': {'package': 'Android package name'}}, 'phone_shortcut': {'description': 'iPhone: trigger a Siri Shortcut by name (iOS blocks raw taps; this is the command-driven path). Requires DEEP_IPHONE_SHORTCUT_WEBHOOK configured.', 'args': {'name': 'Shortcut name', 'input': 'Optional text input to pass to the shortcut'}}}

_deep_orchestrator = None

def _science_compute(query: str) -> dict:
    """Route a natural-language request through the DEEP science/tech engine."""
    try:
        global _deep_orchestrator
        if _deep_orchestrator is None:
            from engine.main import DEEP
            _deep_orchestrator = DEEP()
        return _deep_orchestrator.process_command(query)
    except Exception as e:
        logger.exception('science_compute failed')
        return {'result': None, 'verbal': f'Science engine error: {e}', 'module': None}

async def execute_legacy_tool(ctx, tool_name: str, args: Dict[str, Any]) -> ToolResult:
    import asyncio
    from datetime import datetime
    logger.info(f'[TOOL] Executing {tool_name} with {args}')
    try:
        spec = TOOL_SPECS.get(tool_name)
        if spec is not None:
            return await spec.handler(self, args)
        if tool_name in ('science_compute', 'solve_math', 'run_simulation', 'quant_finance'):
            query = args.get('query', '')
            if not query:
                return ToolResult(False, 'Missing query', tool_name)
            out = await asyncio.to_thread(_science_compute, query)
            return ToolResult(out.get('module') is not None or out.get('result') is not None, out.get('verbal', 'No result.'), tool_name)
        elif tool_name == 'search_web':
            query = args.get('query', '')
            if not query:
                return ToolResult(False, 'Missing query', tool_name)
            if integration_manager.p1_loaded and integration_manager.get('brave_search'):
                try:
                    bs = integration_manager.get('brave_search')
                    res = await bs.quick_answer(query)
                    return ToolResult(True, str(res), tool_name)
                except Exception:
                    pass
            def _ddg(q):
                try:
                    from ddgs import DDGS
                    return list(DDGS().text(q, max_results=5))
                except Exception:
                    from duckduckgo_search import DDGS
                    with DDGS() as d:
                        return list(d.text(q, max_results=5))
            try:
                results = await asyncio.wait_for(asyncio.to_thread(_ddg, query), timeout=15)
                if results:
                    lines = []
                    for i, r in enumerate(results):
                        lines.append(f"{i + 1}. {r.get('title', '')}\n   {str(r.get('body', '')).strip()[:220]}\n   {r.get('href', '')}")
                    return ToolResult(True, f"Live web results for '{query}':\n\n" + '\n\n'.join(lines), tool_name)
            except Exception as e:
                logger.debug(f'DDG search failed: {e}')
            return ToolResult(False, f"Web search for '{query}' returned no results (search backend unavailable right now).", tool_name)
        elif tool_name == 'investigate':
            target = args.get('target', '') or args.get('ip', '') or args.get('mac', '')
            if not target:
                return ToolResult(False, 'Missing target (IP/MAC/host/domain)', tool_name)
            import asyncio as _asyncio, json as _json
            from network.investigator import investigate as _investigate
            dossier = await _asyncio.to_thread(_investigate, str(target))
            summary = dossier.get('summary', '')
            findings = '; '.join((f"{f['label']}: {f['value']}" for f in dossier.get('findings', [])))
            return ToolResult(True, f'{summary}\n{findings}' if findings else summary, tool_name)
        elif tool_name in ('trust_device', 'block_device', 'network_scan', 'vpn_control'):
            _is_destructive = tool_name == 'block_device' or (tool_name == 'vpn_control' and str(args.get('action', '')).lower() == 'down')
            if _is_destructive and (not args.get('_approved')):
                from core.pending_actions import enqueue
                label = 'Block device ' + str(args.get('mac', '?')) if tool_name == 'block_device' else 'Disconnect the VPN'
                enqueue(tool_name, {k: v for k, v in args.items() if k != '_approved'}, label, detail='Protective action — needs your confirmation.')
                return ToolResult(True, f"⏳ This action needs your confirmation: {label}. I've sent it to your Approvals panel — approve it there and I'll proceed.", tool_name)
            import httpx as _httpx
            BASE = 'http://localhost:7768'
            try:
                async with _httpx.AsyncClient(timeout=25) as _c:
                    if tool_name == 'trust_device':
                        mac = args.get('mac', '')
                        if not mac:
                            return ToolResult(False, 'Missing mac', tool_name)
                        r = await _c.post(f'{BASE}/api/security/trust', json={'mac': mac})
                        ok = r.json().get('success')
                        return ToolResult(bool(ok), f'Device {mac} marked TRUSTED.' if ok else 'Trust failed.', tool_name)
                    if tool_name == 'block_device':
                        mac = args.get('mac', '')
                        if not mac:
                            return ToolResult(False, 'Missing mac', tool_name)
                        r = await _c.post(f'{BASE}/api/security/block', json={'mac': mac})
                        ok = r.json().get('success')
                        return ToolResult(bool(ok), f'Device {mac} BLOCKED / flagged suspicious.' if ok else 'Block failed.', tool_name)
                    if tool_name == 'network_scan':
                        ip = args.get('ip', '')
                        if not ip:
                            return ToolResult(False, 'Missing ip', tool_name)
                        r = await _c.post(f'{BASE}/network/scan/{ip}')
                        return ToolResult(True, f'Scan of {ip}: {str(r.json())[:300]}', tool_name)
                    if tool_name == 'vpn_control':
                        act = str(args.get('action', '')).lower()
                        if act not in ('up', 'down'):
                            return ToolResult(False, "action must be 'up' or 'down'", tool_name)
                        r = await _c.post(f'{BASE}/network/vpn/{act}')
                        return ToolResult(True, f'VPN {act.upper()} requested: {str(r.json())[:200]}', tool_name)
            except Exception as _e:
                return ToolResult(False, f"Action '{tool_name}' failed: {_e}", tool_name)
        elif tool_name == 'home_automation':
            action = args.get('action')
            entity = args.get('entity_id', '')
            if integration_manager.p0_loaded and integration_manager.get('home_assistant'):
                ha = integration_manager.get('home_assistant')
                if action == 'get_state':
                    state = await ha.get_state(entity)
                    return ToolResult(True, f'State of {entity}: {state}', tool_name)
                else:
                    svc_data = {'entity_id': entity}
                    if args.get('brightness'):
                        svc_data['brightness'] = args['brightness']
                    domain = entity.split('.')[0] if '.' in entity else 'homeassistant'
                    res = await ha.call_service(domain, action, svc_data)
                    return ToolResult(res.success, f'Executed {action} on {entity}. Result: {res.data or res.error}', tool_name)
            return ToolResult(True, f"Successfully simulated '{action}' on '{entity}'. (Home Assistant token required in .env)", tool_name)
        elif tool_name in ('add_task', 'list_tasks', 'complete_task', 'set_reminder', 'list_reminders', 'calendar_upcoming', 'calendar_create_event'):
            sched = ctx.plugin_manager.get_plugin('scheduler') if ctx.plugin_manager else None
            if sched is None:
                return ToolResult(False, 'Scheduler plugin is not loaded.', tool_name)
            res = None
            if tool_name == 'add_task':
                res = await sched.add_task(args.get('title', ''), args.get('due'), args.get('priority', 'med'))
            elif tool_name == 'list_tasks':
                tasks = await sched.get_open_tasks()
                if not tasks:
                    return ToolResult(True, 'No open tasks.', tool_name)
                lines = [f"#{t['id']} [{t['priority']}] {t['title']}" + (f" (due {t['due']})" if t.get('due') else '') for t in tasks]
                return ToolResult(True, 'Open tasks:\n' + '\n'.join(lines), tool_name)
            elif tool_name == 'complete_task':
                try:
                    res = await sched.complete_task(int(args.get('id')))
                except (TypeError, ValueError):
                    return ToolResult(False, 'id must be an integer.', tool_name)
            elif tool_name == 'set_reminder':
                res = await sched.add_reminder(args.get('text', ''), args.get('at', ''))
            elif tool_name == 'list_reminders':
                rems = await sched.get_pending_reminders()
                if not rems:
                    return ToolResult(True, 'No pending reminders.', tool_name)
                lines = [f"#{r['id']} {r['text']} @ {r['fire_at']}" for r in rems]
                return ToolResult(True, 'Pending reminders:\n' + '\n'.join(lines), tool_name)
            elif tool_name == 'calendar_upcoming':
                try:
                    count = int(args.get('count', 5))
                except (TypeError, ValueError):
                    count = 5
                res = await sched.calendar_upcoming(count)
            elif tool_name == 'calendar_create_event':
                res = await sched.calendar_create_event(args.get('title', ''), args.get('start', ''), args.get('end'))
            if isinstance(res, dict) and res.get('error'):
                return ToolResult(False, str(res['error']), tool_name)
            return ToolResult(True, json.dumps(res), tool_name)
        elif tool_name == 'cyber_scan_network':
            res = await ctx.cyber.scan_network_arp()
            return ToolResult(True, res, tool_name)
        elif tool_name == 'cyber_scan_ports':
            ip = args.get('ip', '')
            res = await ctx.cyber.scan_ports(ip)
            return ToolResult(True, res, tool_name)
        elif tool_name == 'vision_screenshot':
            import os as _os
            path = await ctx.vision.take_screenshot()
            if not isinstance(path, str) or not path.lower().endswith('.png') or (not _os.path.exists(path)):
                return ToolResult(False, f'Could not capture the screen: {path}', tool_name)
            from ..integrations.vision_llava import llava_vision
            q = args.get('question') or 'Describe what is currently on the screen — the apps/windows open and any notable content.'
            analysis = await llava_vision.analyze_image(path, q)
            return ToolResult(True, f'[Screen captured -> {path}]\n\n{analysis}', tool_name)
        elif tool_name == 'vision_analyze':
            from ..integrations.vision_llava import llava_vision
            image_path = args.get('image_path', '')
            question = args.get('question', 'Describe this image in detail')
            analysis = await llava_vision.analyze_image(image_path, question)
            return ToolResult(True, analysis, tool_name)
        elif tool_name == 'vision_debug_ui':
            from ..integrations.vision_llava import llava_vision
            image_path = args.get('image_path', '')
            analysis = await llava_vision.debug_ui(image_path)
            return ToolResult(True, analysis, tool_name)
        elif tool_name == 'vision_analyze_circuit':
            from ..integrations.vision_llava import llava_vision
            image_path = args.get('image_path', '')
            analysis = await llava_vision.analyze_circuit(image_path)
            return ToolResult(True, analysis, tool_name)
        elif tool_name == 'research_ingest':
            res = ctx.rag.ingest_directory()
            return ToolResult(True, res, tool_name)
        elif tool_name == 'research_query':
            query = args.get('query', '')
            res = ctx.rag.query_research(query)
            return ToolResult(True, res, tool_name)
        elif tool_name == 'xr_send_command':
            cmd = args.get('command', '')
            payload = args.get('payload', {})
            res = await ctx.xr.send_to_xr(cmd, payload)
            return ToolResult(True, res, tool_name)
        elif tool_name == 'ask_options':
            message = args.get('message', '')
            options = args.get('options', [])
            if not isinstance(options, list):
                return ToolResult(False, 'Options must be a list', tool_name)
            response = ctx.interactive.create_and_store('options', message, options)
            return ToolResult(True, f'[INTERACTIVE_RESPONSE:{response.to_json()}]', tool_name)
        elif tool_name == 'ask_clarification':
            message = args.get('message', '')
            questions = args.get('questions', [])
            if not isinstance(questions, list):
                return ToolResult(False, 'Questions must be a list', tool_name)
            response = ctx.interactive.create_and_store('clarification', message, questions)
            return ToolResult(True, f'[INTERACTIVE_RESPONSE:{response.to_json()}]', tool_name)
        elif tool_name == 'ask_confirmation':
            message = args.get('message', '')
            action = args.get('action', '')
            response = ctx.interactive.create_and_store('confirmation', message, [{'action': action}])
            return ToolResult(True, f'[INTERACTIVE_RESPONSE:{response.to_json()}]', tool_name)
        elif tool_name == 'ml_train':
            try:
                from ...ai import ml_runner
            except ImportError:
                from ai import ml_runner
            df, err = ctx._ml_resolve_dataset(args.get('data', ''))
            if err:
                return ToolResult(False, err, tool_name)
            params = args.get('params')
            if isinstance(params, str):
                params = json.loads(params) if params.strip() else None
            if params is not None and (not isinstance(params, dict)):
                return ToolResult(False, 'params must be a JSON object, e.g. {"n_clusters": 3}', tool_name)
            report = ml_runner.train(df, args.get('algorithm', ''), target=args.get('target') or None, params=params, save_as=args.get('save_as') or None, models_dir=ctx._ml_models_dir())
            return ToolResult(True, report, tool_name)
        elif tool_name == 'ml_predict':
            try:
                from ...ai import ml_runner
            except ImportError:
                from ai import ml_runner
            df, err = ctx._ml_resolve_dataset(args.get('data', ''))
            if err:
                return ToolResult(False, err, tool_name)
            report = ml_runner.predict(df, args.get('model_name', ''), ctx._ml_models_dir())
            return ToolResult(True, report, tool_name)
        elif tool_name in ('predict_my_tasks', 'train_task_model'):
            try:
                from ...ai import personal_models
            except ImportError:
                from ai import personal_models
            db_path = ctx._scheduler_db_path()
            if tool_name == 'train_task_model':
                return ToolResult(True, personal_models.train_task_completion(db_path, ctx._ml_models_dir()), tool_name)
            return ToolResult(True, personal_models.predict_task_completion(db_path, ctx._ml_models_dir()), tool_name)
        elif tool_name == 'add_transaction':
            r = ctx.finance.add_transaction(args.get('date', datetime.now().strftime('%Y-%m-%d')), float(args.get('amount', 0)), args.get('description', ''), category=args.get('category'), currency=args.get('currency', 'SEK'))
            return ToolResult(True, r.get('verbal', 'Recorded.'), tool_name)
        elif tool_name == 'spending_summary':
            r = ctx.finance.spending_summary(months=int(args.get('months', 1)))
            return ToolResult(True, r.get('verbal', json.dumps(r)), tool_name)
        elif tool_name == 'set_budget':
            r = ctx.finance.set_budget(args.get('category', ''), float(args.get('limit', 0)), args.get('currency', 'SEK'))
            return ToolResult(True, r.get('verbal', 'Budget set.'), tool_name)
        elif tool_name == 'get_budget_status':
            r = ctx.finance.get_budget_status()
            lines = [f"{b['category']}: {b['spent']:.0f}/{b['limit']:.0f} ({b['percent']:.0f}%)" for b in r]
            return ToolResult(True, 'Budgets this month:\n' + '\n'.join(lines), tool_name)
        elif tool_name == 'add_bill':
            r = ctx.finance.add_bill(args.get('name', ''), float(args.get('amount', 0)), frequency=args.get('frequency', 'monthly'), next_due=args.get('next_due'))
            return ToolResult(True, r.get('verbal', 'Bill added.'), tool_name)
        elif tool_name == 'upcoming_bills':
            r = ctx.finance.upcoming_bills(days=int(args.get('days', 14)))
            if not r:
                return ToolResult(True, 'No upcoming bills.', tool_name)
            lines = [f"{b['name']} ({b['amount']:.0f}) due {b['next_due']}" for b in r]
            return ToolResult(True, 'Upcoming bills:\n' + '\n'.join(lines), tool_name)
        elif tool_name == 'detect_spending_anomalies':
            r = ctx.finance.detect_anomalies(category=args.get('category'))
            if not r:
                return ToolResult(True, 'No spending anomalies detected.', tool_name)
            lines = [f"{a['description']} ({a['amount']:.0f}) — {a['z_score']:.1f}σ" for a in r]
            return ToolResult(True, 'Anomalies:\n' + '\n'.join(lines), tool_name)
        elif tool_name == 'inbox_summary':
            r = ctx.email.inbox_summary(limit=int(args.get('limit', 20)))
            return ToolResult(True, r.get('verbal', json.dumps(r)), tool_name)
        elif tool_name == 'search_emails':
            r = ctx.email.search(args.get('query', ''), limit=int(args.get('limit', 10)))
            return ToolResult(True, r.get('verbal', json.dumps(r)), tool_name)
        elif tool_name == 'send_email':
            r = ctx.email.send(args.get('to', ''), args.get('subject', ''), args.get('body', ''))
            return ToolResult(r.get('ok', False), r.get('verbal', ''), tool_name)
        elif tool_name == 'track_email':
            r = ctx.email.track_thread(args.get('msg_id', ''), args.get('sender', ''), args.get('subject', ''), notes=args.get('notes', ''))
            return ToolResult(True, r.get('verbal', ''), tool_name)
        elif tool_name == 'awaiting_replies':
            r = ctx.email.awaiting_reply()
            if not r:
                return ToolResult(True, 'No emails awaiting reply.', tool_name)
            lines = [f"{t['subject']} from {t['sender']}" for t in r]
            return ToolResult(True, 'Awaiting replies:\n' + '\n'.join(lines), tool_name)
        elif tool_name == 'create_mission':
            from ..long_running_orchestrator import LongRunningOrchestrator
            orch = LongRunningOrchestrator()
            m = orch.create_mission(args.get('goal', ''))
            return ToolResult(True, f"Mission '{m.id}' created: {m.goal}. Planning subtasks now…", tool_name)
        elif tool_name == 'list_missions':
            from ..long_running_orchestrator import LongRunningOrchestrator
            orch = LongRunningOrchestrator()
            status = args.get('status')
            missions = orch.list_missions(status=status, limit=10)
            if not missions:
                return ToolResult(True, 'No missions found.', tool_name)
            lines = [f'{m.id} | {m.status} | {m.progress_pct:.0f}% | {m.goal[:50]}' for m in missions]
            return ToolResult(True, 'Missions:\n' + '\n'.join(lines), tool_name)
        elif tool_name == 'mission_status':
            from ..long_running_orchestrator import LongRunningOrchestrator
            orch = LongRunningOrchestrator()
            try:
                d = orch.get_mission_detail(args.get('mission_id', ''))
                m = d['mission']
                subs = d['subtasks']
                lines = [f"Mission {m['id']} — {m['status']} ({m['progress_pct']:.0f}%)"]
                lines.append(f"Goal: {m['goal']}")
                for s in subs:
                    lines.append(f"  [{s['status']}] {s['description']}")
                return ToolResult(True, '\n'.join(lines), tool_name)
            except Exception as e:
                return ToolResult(False, str(e), tool_name)
        elif tool_name == 'cancel_mission':
            from ..long_running_orchestrator import LongRunningOrchestrator
            orch = LongRunningOrchestrator()
            orch.cancel_mission(args.get('mission_id', ''))
            return ToolResult(True, 'Mission cancelled.', tool_name)
        elif tool_name == 'phone_status':
            return ToolResult(True, await ctx.phone.status(), tool_name)
        elif tool_name == 'phone_connect':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            addr = args.get('address', '')
            if not addr:
                return ToolResult(False, 'Missing address (host:port).', tool_name)
            ok, msg = await ctx.phone.android.connect(addr)
            return ToolResult(ok, msg, tool_name)
        elif tool_name == 'phone_pair':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            addr, code = (args.get('address', ''), args.get('code', ''))
            if not addr or not code:
                return ToolResult(False, 'Need both address (host:port) and the 6-digit code.', tool_name)
            ok, msg = await ctx.phone.android.pair(addr, code)
            return ToolResult(ok, msg, tool_name)
        elif tool_name == 'phone_screenshot':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            ok, path = await ctx.phone.android.screenshot()
            if not ok:
                return ToolResult(False, f'Could not capture the phone screen: {path}', tool_name)
            from ..integrations.vision_llava import llava_vision
            q = args.get('question') or 'Describe what is on this phone screen — the app, UI elements, and any tappable buttons with their rough positions.'
            analysis = await llava_vision.analyze_image(path, q)
            return ToolResult(True, f'[Phone screen captured -> {path}]\n\n{analysis}', tool_name)
        elif tool_name == 'phone_tap':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            try:
                x, y = (int(args.get('x')), int(args.get('y')))
            except (TypeError, ValueError):
                return ToolResult(False, 'x and y must be integers.', tool_name)
            ok, msg = await ctx.phone.android.tap(x, y)
            return ToolResult(ok, msg, tool_name)
        elif tool_name == 'phone_swipe':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            try:
                x1, y1 = (int(args.get('x1')), int(args.get('y1')))
                x2, y2 = (int(args.get('x2')), int(args.get('y2')))
                dur = int(args.get('duration_ms', 300))
            except (TypeError, ValueError):
                return ToolResult(False, 'x1,y1,x2,y2 must be integers.', tool_name)
            ok, msg = await ctx.phone.android.swipe(x1, y1, x2, y2, dur)
            return ToolResult(ok, msg, tool_name)
        elif tool_name == 'phone_text':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            ok, msg = await ctx.phone.android.text(args.get('text', ''))
            return ToolResult(ok, msg, tool_name)
        elif tool_name == 'phone_key':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            ok, msg = await ctx.phone.android.key(args.get('key', ''))
            return ToolResult(ok, msg, tool_name)
        elif tool_name == 'phone_open_app':
            err = ctx.phone._need_android()
            if err:
                return ToolResult(False, err, tool_name)
            pkg = args.get('package', '')
            if not pkg:
                return ToolResult(False, 'Missing package name.', tool_name)
            ok, msg = await ctx.phone.android.open_app(pkg)
            return ToolResult(ok, msg, tool_name)
        elif tool_name == 'phone_shortcut':
            name = args.get('name', '')
            if not name:
                return ToolResult(False, 'Missing shortcut name.', tool_name)
            ok, msg = await ctx.phone.iphone.run_shortcut(name, args.get('input', ''))
            return ToolResult(ok, msg, tool_name)
        else:
            return ToolResult(False, f'Unknown tool: {tool_name}', tool_name)
    except Exception as e:
        logger.error(f'[TOOL ERROR] {e}')
        return ToolResult(False, str(e), tool_name, str(e))


for name, info in LEGACY_TOOLS.items():
    if name in TOOL_SPECS:
        continue # Already ported
    def make_handler(tool_name):
        async def handler(ctx, args):
            return await execute_legacy_tool(ctx, tool_name, args)
        return handler
    # Register it!
    tool(name, info["description"], info.get("args", {}))(make_handler(name))
