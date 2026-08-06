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

LEGACY_TOOLS = {
    'search_web': {
        'description': 'Search the live internet for up-to-date information, news, or weather.',
        'args': {
            'query': 'The search query string',
        },
    },
    'investigate': {
        'description': 'Build an intelligence dossier on an IP address, MAC address, hostname or domain (vendor, reverse-DNS, geolocation, ISP/ASN, private-vs-public, risk flags). Use this to identify unknown network/Bluetooth devices or remote hosts.',
        'args': {
            'target': 'An IP (e.g. 8.8.8.8), MAC (e.g. C4:9A:31:FF:CA:A0), hostname or domain',
        },
    },
    'trust_device': {
        'description': 'ACTION: mark a network device as trusted (whitelist it) by its MAC address. Use when the user confirms a device is theirs/safe.',
        'args': {
            'mac': 'Device MAC address',
        },
    },
    'block_device': {
        'description': 'ACTION (protective): flag a network device as blocked/suspicious by its MAC address. Use when the user wants to block a suspicious or unknown device.',
        'args': {
            'mac': 'Device MAC address',
        },
    },
    'network_scan': {
        'description': 'ACTION: actively scan a specific device/IP for open ports and OS fingerprint. Use to inspect a suspicious host more deeply.',
        'args': {
            'ip': 'Target IP on the local network, e.g. 192.168.1.42',
        },
    },
    'vpn_control': {
        'description': "ACTION (protective): bring the VPN up or down. Use 'up' to secure the connection, 'down' to disconnect.",
        'args': {
            'action': "'up' or 'down'",
        },
    },
    'add_task': {
        'description': "Add a task/todo to the user's persistent list.",
        'args': {
            'title': 'Task description',
            'due': 'Optional ISO 8601 datetime, e.g. 2026-06-02T17:00:00',
            'priority': "Optional: 'low', 'med', or 'high' (default 'med')",
        },
    },
    'list_tasks': {
        'description': "List the user's open (incomplete) tasks.",
        'args': {},
    },
    'complete_task': {
        'description': 'Mark a task as done by its id.',
        'args': {
            'id': 'The integer task id',
        },
    },
    'set_reminder': {
        'description': 'Set a time-based reminder that fires (notifies + optional SMS) when due.',
        'args': {
            'text': 'What to remind the user about',
            'at': 'When to fire, as an ISO 8601 datetime, e.g. 2026-06-01T18:00:00',
        },
    },
    'list_reminders': {
        'description': 'List pending (not-yet-fired) reminders.',
        'args': {},
    },
    'calendar_upcoming': {
        'description': "List the user's upcoming Google Calendar events.",
        'args': {
            'count': 'Optional number of events to return (default 5)',
        },
    },
    'calendar_create_event': {
        'description': "Create an event on the user's Google Calendar.",
        'args': {
            'title': 'Event title',
            'start': 'Start time, ISO 8601 datetime',
            'end': 'Optional end time, ISO 8601 (defaults to start + 1 hour)',
        },
    },
    'cyber_scan_network': {
        'description': 'Scans the local network using ARP to find connected devices.',
        'args': {},
    },
    'cyber_scan_ports': {
        'description': 'Scans an IP address for open ports.',
        'args': {
            'ip': 'The target IP address',
        },
    },
    'vision_screenshot': {
        'description': "Look at the user's screen RIGHT NOW: captures a screenshot and analyzes it with local AI vision (LLaVA). Use when the user asks 'what's on my screen', 'look at this', or wants DEEP to see what they're doing.",
        'args': {
            'question': 'Optional: what to look for (default: describe the whole screen)',
        },
    },
    'vision_analyze': {
        'description': "Analyze an image using local AI vision (LLaVA). Understands what's in the image.",
        'args': {
            'image_path': 'Path to the image file',
            'question': 'Optional question about the image (default: describe it)',
        },
    },
    'vision_debug_ui': {
        'description': 'Analyze a UI screenshot for bugs, layout issues, and UX improvements.',
        'args': {
            'image_path': 'Path to UI screenshot',
        },
    },
    'vision_analyze_circuit': {
        'description': 'Analyze a circuit board or electronic component image (for robotics).',
        'args': {
            'image_path': 'Path to circuit image',
        },
    },
    'ask_options': {
        'description': 'Present multiple options/alternatives to the user for selection. Use when there are multiple valid approaches.',
        'args': {
            'message': 'Question or context for the options',
            'options': 'List of dicts with label, description, pros, cons, recommended',
        },
    },
    'ask_clarification': {
        'description': 'Ask clarifying questions before proceeding. Use when you need more information from the user.',
        'args': {
            'message': 'Context message',
            'questions': 'List of dicts with question, context, required, suggestions',
        },
    },
    'ask_confirmation': {
        'description': 'Ask for yes/no confirmation before taking an action.',
        'args': {
            'message': "What you're asking about",
            'action': 'The action that will be taken if confirmed',
        },
    },
    'ml_train': {
        'description': "Train a real ML model via scikit-learn/XGBoost. Data is a CSV path OR 'internal:processes'/'internal:network'. Supervised algos need a target column.",
        'args': {
            'algorithm': "e.g. 'random_forest', 'xgboost', 'kmeans', 'isolation_forest'",
            'data': "CSV path or 'internal:processes' / 'internal:network'",
            'target': 'Target column name (supervised only)',
            'params': 'Optional JSON object of hyperparameters, e.g. {"n_clusters": 3}',
            'save_as': 'Optional name to save the trained model under',
        },
    },
    'ml_predict': {
        'description': 'Predict using a previously trained+saved model.',
        'args': {
            'model_name': 'Saved model name',
            'data': "CSV path or 'internal:...'",
        },
    },
    'predict_my_tasks': {
        'description': "Score Aryan's OPEN tasks by how likely he is to complete each, learned from his own task history. Trains on first use. Use to surface which tasks are at risk / need a nudge.",
        'args': {},
    },
    'train_task_model': {
        'description': '(Re)train the personal task-completion model from the latest scheduler history.',
        'args': {},
    },
    'create_mission': {
        'description': 'Start a complex, multi-step autonomous mission that DEEP executes in the background over minutes or hours. Examples: research a topic, plan a trip, audit a codebase, generate a report.',
        'args': {
            'goal': "High-level mission description, e.g. 'Research quantum AI and write a blog summary'",
        },
    },
    'list_missions': {
        'description': 'List active and recent autonomous missions with their progress.',
        'args': {
            'status': 'Optional filter: pending, running, completed, failed',
        },
    },
    'mission_status': {
        'description': 'Get detailed status of a specific mission including subtasks.',
        'args': {
            'mission_id': 'The mission ID',
        },
    },
    'cancel_mission': {
        'description': 'Cancel an in-progress mission.',
        'args': {
            'mission_id': 'The mission ID',
        },
    },
}

async def execute_legacy_tool(ctx, tool_name: str, args: Dict[str, Any]) -> ToolResult:
    """Dispatch one not-yet-migrated tool.

    NOTE: do not add a `TOOL_SPECS[tool_name]` delegation here. The only caller
    of this function is the handler registered under that very name (see the
    loop at the bottom of this module), so such a lookup always resolves to the
    caller and recurses until the stack blows. That branch used to exist and
    made every legacy tool fail — first with a NameError on an undefined
    `self`, then, once that was "fixed", with RecursionError.
    """
    from datetime import datetime
    logger.info(f'[TOOL] Executing {tool_name} with {args}')
    try:
        if tool_name == 'search_web':
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
            import asyncio as _asyncio
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
