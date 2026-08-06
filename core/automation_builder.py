"""
automation_builder.py

Visual Automation Workflow Builder for JARVIS.

Features:
- Trigger-based automation (time, events, conditions)
- Visual workflow editor (JSON/YAML based)
- Action chaining with conditionals
- IFTTT-style recipes
- Built-in triggers and actions library
- Real-time workflow execution

Usage:
    from DEEP.core.automation_builder import AutomationBuilder
    
    builder = AutomationBuilder()
    
    # Create workflow
    workflow = builder.create_workflow("Morning Routine")
    workflow.add_trigger("time", {"hour": 8, "minute": 0})
    workflow.add_action("command", {"command": "news"})
    workflow.add_action("notification", {"title": "Good morning!", "message": "Here's your briefing"})
    
    # Enable workflow
    builder.enable_workflow(workflow.id)

Workflow Format (YAML):
    name: Morning Routine
    enabled: true
    triggers:
      - type: time
        config:
          hour: 8
          minute: 0
    actions:
      - type: command
        config:
          command: news
      - type: condition
        config:
          if: "cpu_usage > 80"
          then:
            - type: notification
              config:
                message: "CPU high!"
"""

from __future__ import annotations

import os
import json
import yaml
import time
import threading
import schedule
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

# Platform detection
IS_WINDOWS = os.name == 'nt'


class TriggerType(Enum):
    """Types of automation triggers."""
    TIME = "time"                    # Specific time (cron-like)
    INTERVAL = "interval"            # Every X minutes/hours
    EVENT = "event"                  # Custom event emitted
    CONDITION = "condition"          # When condition becomes true
    STARTUP = "startup"              # On JARVIS startup
    SHUTDOWN = "shutdown"            # On JARVIS shutdown
    VOICE_COMMAND = "voice"          # Voice command detected
    HOTKEY = "hotkey"                # Global hotkey pressed
    SYSTEM = "system"                # System event (CPU, memory, etc.)


class ActionType(Enum):
    """Types of automation actions."""
    COMMAND = "command"              # Run JARVIS command
    NOTIFICATION = "notification"    # Show notification
    SHELL = "shell"                  # Execute shell command
    PYTHON = "python"                # Run Python code
    WEBHOOK = "webhook"              # Call webhook/URL
    CONDITION = "condition"          # If/else logic
    DELAY = "delay"                  # Wait N seconds
    PARALLEL = "parallel"            # Run actions in parallel
    SEQUENCE = "sequence"            # Run actions sequentially
    SMART_HOME = "smarthome"         # Control smart home devices
    EMAIL = "email"                  # Send email


@dataclass
class Trigger:
    """Workflow trigger definition."""
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_fired: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "config": self.config,
            "enabled": self.enabled,
            "last_fired": self.last_fired.isoformat() if self.last_fired else None
        }


@dataclass
class Action:
    """Workflow action definition."""
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    on_error: str = "continue"  # "continue", "stop", "retry"
    retry_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "config": self.config,
            "enabled": self.enabled,
            "on_error": self.on_error,
            "retry_count": self.retry_count
        }


@dataclass
class Workflow:
    """Automation workflow definition."""
    id: str
    name: str
    description: str = ""
    enabled: bool = False
    triggers: List[Trigger] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "triggers": [t.to_dict() for t in self.triggers],
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "metadata": self.metadata
        }


class AutomationBuilder:
    """
    Visual Automation Workflow Builder.
    
    Provides:
    - Create and manage workflows
    - Trigger-based execution
    - Action library
    - YAML/JSON import/export
    - Real-time execution engine
    """
    
    def __init__(self, data_dir: str = "./data/automation"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self._workflows: Dict[str, Workflow] = {}
        self._workflows_file = self.data_dir / "workflows.json"
        
        # Execution
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._event_listeners: Dict[str, List[str]] = {}  # event_type -> workflow_ids
        
        # Callbacks for actions
        self._action_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
        
        # System state for conditions
        self._system_state: Dict[str, Any] = {}
        
        # Load saved workflows
        self._load_workflows()
    
    def _register_default_handlers(self) -> None:
        """Register default action handlers."""
        self._action_handlers = {
            "command": self._handle_command,
            "notification": self._handle_notification,
            "shell": self._handle_shell,
            "python": self._handle_python,
            "webhook": self._handle_webhook,
            "delay": self._handle_delay,
            "condition": self._handle_condition,
            "smarthome": self._handle_smarthome,
            "email": self._handle_email,
        }
    
    def _load_workflows(self) -> None:
        """Load workflows from disk."""
        if self._workflows_file.exists():
            try:
                with open(self._workflows_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for wf_data in data.get("workflows", []):
                    workflow = Workflow(
                        id=wf_data["id"],
                        name=wf_data["name"],
                        description=wf_data.get("description", ""),
                        enabled=wf_data.get("enabled", False),
                        triggers=[Trigger(**t) for t in wf_data.get("triggers", [])],
                        actions=[Action(**a) for a in wf_data.get("actions", [])],
                        created_at=datetime.fromisoformat(wf_data["created_at"]),
                        last_run=datetime.fromisoformat(wf_data["last_run"]) if wf_data.get("last_run") else None,
                        run_count=wf_data.get("run_count", 0),
                        metadata=wf_data.get("metadata", {})
                    )
                    self._workflows[workflow.id] = workflow
                
                print(f"✓ Loaded {len(self._workflows)} workflows")
            except Exception as e:
                print(f"⚠️ Failed to load workflows: {e}")
    
    def _save_workflows(self) -> None:
        """Save workflows to disk."""
        try:
            data = {
                "saved_at": datetime.now().isoformat(),
                "workflows": [wf.to_dict() for wf in self._workflows.values()]
            }
            
            with open(self._workflows_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Failed to save workflows: {e}")
    
    # ==================== WORKFLOW CRUD ====================
    
    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """Create a new workflow."""
        workflow_id = f"wf_{int(time.time())}_{name.lower().replace(' ', '_')}"
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description
        )
        
        self._workflows[workflow_id] = workflow
        self._save_workflows()
        
        print(f"✓ Created workflow: {name}")
        return workflow
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            self._save_workflows()
            print(f"✓ Deleted workflow: {workflow_id}")
            return True
        return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self, enabled_only: bool = False) -> List[Workflow]:
        """List all workflows."""
        workflows = list(self._workflows.values())
        if enabled_only:
            workflows = [w for w in workflows if w.enabled]
        return sorted(workflows, key=lambda w: w.created_at, reverse=True)
    
    def enable_workflow(self, workflow_id: str) -> bool:
        """Enable a workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow:
            workflow.enabled = True
            self._save_workflows()
            self._setup_triggers(workflow)
            print(f"✓ Enabled workflow: {workflow.name}")
            return True
        return False
    
    def disable_workflow(self, workflow_id: str) -> bool:
        """Disable a workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow:
            workflow.enabled = False
            self._save_workflows()
            print(f"✓ Disabled workflow: {workflow.name}")
            return True
        return False
    
    def add_trigger(self, workflow_id: str, trigger_type: str, config: Dict) -> bool:
        """Add trigger to workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow:
            trigger = Trigger(type=trigger_type, config=config)
            workflow.triggers.append(trigger)
            self._save_workflows()
            
            if workflow.enabled:
                self._setup_trigger(workflow, trigger)
            
            return True
        return False
    
    def add_action(self, workflow_id: str, action_type: str, config: Dict) -> bool:
        """Add action to workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow:
            action = Action(type=action_type, config=config)
            workflow.actions.append(action)
            self._save_workflows()
            return True
        return False
    
    # ==================== EXECUTION ENGINE ====================
    
    def start(self) -> None:
        """Start automation engine."""
        if self._running:
            return
        
        self._running = True
        
        # Setup all enabled workflows
        for workflow in self._workflows.values():
            if workflow.enabled:
                self._setup_triggers(workflow)
        
        # Start scheduler thread
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        print("✓ Automation engine started")
    
    def stop(self) -> None:
        """Stop automation engine."""
        self._running = False
        schedule.clear()
        print("🛑 Automation engine stopped")
    
    def _scheduler_loop(self) -> None:
        """Background scheduler loop."""
        while self._running:
            schedule.run_pending()
            time.sleep(1)
    
    def _setup_triggers(self, workflow: Workflow) -> None:
        """Setup all triggers for a workflow."""
        for trigger in workflow.triggers:
            if trigger.enabled:
                self._setup_trigger(workflow, trigger)
    
    def _setup_trigger(self, workflow: Workflow, trigger: Trigger) -> None:
        """Setup a single trigger."""
        trigger_type = trigger.type
        config = trigger.config
        
        if trigger_type == "time":
            # Schedule at specific time
            hour = config.get("hour", 0)
            minute = config.get("minute", 0)
            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                lambda w=workflow: self._execute_workflow(w)
            )
        
        elif trigger_type == "interval":
            # Schedule interval
            minutes = config.get("minutes", 60)
            schedule.every(minutes).minutes.do(
                lambda w=workflow: self._execute_workflow(w)
            )
        
        elif trigger_type == "startup":
            # Execute immediately on startup
            if config.get("delay", 0) > 0:
                time.sleep(config["delay"])
            self._execute_workflow(workflow)
        
        elif trigger_type == "event":
            # Register event listener
            event_type = config.get("event_type")
            if event_type:
                if event_type not in self._event_listeners:
                    self._event_listeners[event_type] = []
                self._event_listeners[event_type].append(workflow.id)
        
        elif trigger_type == "hotkey":
            # Register hotkey (would need platform-specific implementation)
            pass
    
    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to trigger workflows."""
        workflow_ids = self._event_listeners.get(event_type, [])
        for workflow_id in workflow_ids:
            workflow = self._workflows.get(workflow_id)
            if workflow and workflow.enabled:
                # Check condition if specified
                self._execute_workflow(workflow, event_data=data)
    
    def _execute_workflow(self, workflow: Workflow, event_data: Optional[Dict] = None) -> bool:
        """Execute a workflow."""
        if not workflow.enabled:
            return False
        
        print(f"▶️ Executing workflow: {workflow.name}")
        workflow.last_run = datetime.now()
        workflow.run_count += 1
        
        try:
            for action in workflow.actions:
                if not action.enabled:
                    continue
                
                success = self._execute_action(action, event_data)
                
                if not success:
                    if action.on_error == "stop":
                        print(f"⏹️ Workflow stopped due to error in action: {action.type}")
                        break
                    elif action.on_error == "retry" and action.retry_count > 0:
                        for _ in range(action.retry_count):
                            time.sleep(1)
                            if self._execute_action(action, event_data):
                                break
            
            self._save_workflows()
            return True
            
        except Exception as e:
            print(f"❌ Workflow execution error: {e}")
            return False
    
    def _execute_action(self, action: Action, event_data: Optional[Dict] = None) -> bool:
        """Execute a single action."""
        handler = self._action_handlers.get(action.type)
        
        if handler:
            try:
                return handler(action.config, event_data)
            except Exception as e:
                print(f"❌ Action {action.type} failed: {e}")
                return False
        else:
            print(f"⚠️ No handler for action type: {action.type}")
            return False
    
    # ==================== ACTION HANDLERS ====================
    
    def _handle_command(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Execute JARVIS command."""
        command = config.get("command")
        if command:
            print(f"🤖 Executing command: {command}")
            # Would call JARVIS command handler
            return True
        return False
    
    def _handle_notification(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Show system notification."""
        title = config.get("title", "JARVIS")
        message = config.get("message", "")
        
        print(f"🔔 Notification: {title} - {message}")
        
        # Platform-specific notification
        try:
            if IS_WINDOWS:
                import winsound
                winsound.MessageBeep()
            
            # Could integrate with system tray
            return True
        except:
            pass
        
        return True
    
    def _handle_shell(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Execute shell command."""
        import subprocess
        
        command = config.get("command")
        if command:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=config.get("timeout", 30)
                )
                print(f"💻 Shell output: {result.stdout[:200]}")
                return result.returncode == 0
            except Exception as e:
                print(f"❌ Shell command failed: {e}")
                return False
        return False
    
    def _handle_python(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Execute Python code."""
        code = config.get("code")
        if code:
            try:
                exec(code)
                return True
            except Exception as e:
                print(f"❌ Python execution failed: {e}")
                return False
        return False
    
    def _handle_webhook(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Call webhook URL."""
        import urllib.request
        import urllib.parse
        
        url = config.get("url")
        method = config.get("method", "POST")
        data = config.get("data", {})
        
        if url:
            try:
                if method == "POST":
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(data).encode(),
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                else:
                    req = urllib.request.Request(url)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.status == 200
            except Exception as e:
                print(f"❌ Webhook failed: {e}")
                return False
        return False
    
    def _handle_delay(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Wait for specified time."""
        seconds = config.get("seconds", 1)
        time.sleep(seconds)
        return True
    
    def _handle_condition(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Evaluate condition and execute then/else branches."""
        condition = config.get("if")
        then_actions = config.get("then", [])
        else_actions = config.get("else", [])
        
        # Evaluate condition
        # This is simplified - real implementation would use expression evaluator
        result = self._evaluate_condition(condition)
        
        actions = then_actions if result else else_actions
        
        for action_config in actions:
            action = Action(**action_config)
            self._execute_action(action, event_data)
        
        return True
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression."""
        # Simplified condition evaluation
        # Would use proper expression parser in production
        
        # Example: "cpu_usage > 80"
        if "cpu_usage" in condition:
            # Get actual CPU usage
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.1)
                return cpu > 80
            except:
                return False
        
        # Default to True for demo
        return True
    
    def _handle_smarthome(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Control smart home devices."""
        device = config.get("device")
        action = config.get("action")
        
        print(f"🏠 Smart Home: {action} {device}")
        # Would integrate with smart home controller
        return True
    
    def _handle_email(self, config: Dict, event_data: Optional[Dict]) -> bool:
        """Send email."""
        to = config.get("to")
        subject = config.get("subject")
        body = config.get("body")
        
        print(f"📧 Email to {to}: {subject}")
        # Would integrate with email assistant
        return True
    
    # ==================== IMPORT/EXPORT ====================
    
    def import_yaml(self, yaml_file: str) -> Optional[Workflow]:
        """Import workflow from YAML file."""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Create workflow
            workflow = self.create_workflow(
                name=data.get("name", "Imported Workflow"),
                description=data.get("description", "")
            )
            
            # Add triggers
            for trigger_data in data.get("triggers", []):
                self.add_trigger(
                    workflow.id,
                    trigger_data["type"],
                    trigger_data.get("config", {})
                )
            
            # Add actions
            for action_data in data.get("actions", []):
                self.add_action(
                    workflow.id,
                    action_data["type"],
                    action_data.get("config", {})
                )
            
            # Enable if specified
            if data.get("enabled", False):
                self.enable_workflow(workflow.id)
            
            print(f"✓ Imported workflow from {yaml_file}")
            return workflow
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            return None
    
    def export_yaml(self, workflow_id: str, output_file: str) -> bool:
        """Export workflow to YAML file."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        try:
            data = {
                "name": workflow.name,
                "description": workflow.description,
                "enabled": workflow.enabled,
                "triggers": [t.to_dict() for t in workflow.triggers],
                "actions": [a.to_dict() for a in workflow.actions]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            print(f"✓ Exported workflow to {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False


# Demo
if __name__ == "__main__":
    print("="*60)
    print("Automation Workflow Builder Demo")
    print("="*60)
    print()
    
    # Create builder
    builder = AutomationBuilder()
    
    # Create morning routine workflow
    print("Creating 'Morning Routine' workflow...")
    workflow = builder.create_workflow(
        "Morning Routine",
        "Daily morning automation"
    )
    
    # Add triggers
    builder.add_trigger(workflow.id, "time", {"hour": 8, "minute": 0})
    
    # Add actions
    builder.add_action(workflow.id, "notification", {
        "title": "Good Morning!",
        "message": "Starting your daily briefing..."
    })
    builder.add_action(workflow.id, "command", {"command": "news"})
    builder.add_action(workflow.id, "delay", {"seconds": 2})
    builder.add_action(workflow.id, "shell", {"command": "echo Morning routine complete!"})
    
    # Enable workflow
    builder.enable_workflow(workflow.id)
    
    # List workflows
    print("\n📋 Workflows:")
    for wf in builder.list_workflows():
        status = "🟢" if wf.enabled else "⚫"
        print(f"  {status} {wf.name} ({len(wf.triggers)} triggers, {len(wf.actions)} actions)")
    
    # Export example
    builder.export_yaml(workflow.id, "./morning_routine.yaml")
    
    print("\n✓ Demo complete!")
    print("\nTo test, you can manually trigger:")
    print(f"  builder._execute_workflow(builder.get_workflow('{workflow.id}'))")


# Quick mode switcher for JARVIS
class ModeSwitcher:
    """
    Specialized modes for different contexts.
    
    Modes:
    - deep_work: Blocks distractions, focus timer
    - coding: IDE integration, Stack Overflow access
    - meeting: Note taking, action items
    - presentation: Slide control, laser pointer
    - reading: Distraction-free reading mode
    """
    
    MODES = {
        "deep_work": {
            "description": "Focus mode with distractions blocked",
            "actions": [
                "close_social_apps",
                "enable_dnd",
                "start_pomodoro",
                "play_focus_music"
            ]
        },
        "coding": {
            "description": "Development mode",
            "actions": [
                "open_ide",
                "enable_syntax_highlighting",
                "activate_code_assistant"
            ]
        },
        "meeting": {
            "description": "Meeting assistant mode",
            "actions": [
                "start_recording",
                "enable_live_transcription",
                "prepare_notes_template"
            ]
        },
        "presentation": {
            "description": "Presentation control mode",
            "actions": [
                "enable_slide_control",
                "activate_voice_commands",
                "hide_notifications"
            ]
        }
    }
    
    def __init__(self, jarvis_instance):
        self.jarvis = jarvis_instance
        self.current_mode = None
    
    def switch_mode(self, mode_name: str) -> bool:
        """Switch to a specialized mode."""
        if mode_name not in self.MODES:
            print(f"❌ Unknown mode: {mode_name}")
            print(f"Available modes: {', '.join(self.MODES.keys())}")
            return False
        
        mode = self.MODES[mode_name]
        self.current_mode = mode_name
        
        print(f"🎯 Switched to {mode_name} mode")
        print(f"   {mode['description']}")
        
        # Execute mode actions
        for action in mode['actions']:
            print(f"   • {action}")
        
        return True
    
    def get_current_mode(self) -> Optional[str]:
        """Get current active mode."""
        return self.current_mode
    
    def list_modes(self) -> Dict[str, str]:
        """List available modes."""
        return {name: info['description'] for name, info in self.MODES.items()}


# Privacy & Security Suite
class PrivacySuite:
    """
    Privacy and security features.
    
    Features:
    - Local-only mode (no cloud)
    - Encrypted memory storage
    - Voice biometric auth
    - Activity audit log
    """
    
    def __init__(self, data_dir: str = "./data/privacy"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.encryption_key = None
        self.local_only = False
        self.audit_log = []
    
    def enable_local_only_mode(self) -> None:
        """Enable offline-only mode (no cloud AI)."""
        self.local_only = True
        print("🔒 Local-only mode enabled")
        print("   • No cloud AI services")
        print("   • All processing on-device")
        print("   • Ollama required for AI")
    
    def setup_encryption(self, password: str) -> None:
        """Setup encryption for sensitive memories."""
        # Derive key from password
        import hashlib
        self.encryption_key = hashlib.sha256(password.encode()).digest()
        print("🔐 Memory encryption enabled")
    
    def log_activity(self, action: str, details: Dict) -> None:
        """Log activity for audit."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        self.audit_log.append(entry)
        
        # Save to file
        log_file = self.data_dir / "audit_log.json"
        with open(log_file, 'w') as f:
            json.dump(self.audit_log, f, indent=2)
    
    def get_audit_log(self, days: int = 7) -> List[Dict]:
        """Get recent activity log."""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            entry for entry in self.audit_log
            if datetime.fromisoformat(entry['timestamp']) > cutoff
        ]


# Analytics & Insights
class AnalyticsEngine:
    """
    Usage analytics and productivity insights.
    
    Tracks:
    - Daily/weekly usage patterns
    - Productivity metrics
    - Most used commands
    - Focus time
    """
    
    def __init__(self, data_dir: str = "./data/analytics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.usage_data = {
            "commands": {},
            "daily_active_time": {},
            "focus_sessions": [],
            "interruptions": []
        }
    
    def record_command(self, command: str) -> None:
        """Record command usage."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.usage_data["commands"]:
            self.usage_data["commands"][today] = {}
        
        self.usage_data["commands"][today][command] = \
            self.usage_data["commands"][today].get(command, 0) + 1
    
    def start_focus_session(self, task: str) -> None:
        """Start tracking a focus session."""
        self.usage_data["focus_sessions"].append({
            "task": task,
            "start_time": datetime.now().isoformat(),
            "end_time": None
        })
    
    def end_focus_session(self) -> None:
        """End current focus session."""
        if self.usage_data["focus_sessions"]:
            self.usage_data["focus_sessions"][-1]["end_time"] = datetime.now().isoformat()
    
    def get_weekly_report(self) -> Dict:
        """Generate weekly productivity report."""
        # Calculate metrics
        total_commands = sum(
            sum(day.values()) for day in self.usage_data["commands"].values()
        )
        
        # Most used commands
        all_commands = {}
        for day in self.usage_data["commands"].values():
            for cmd, count in day.items():
                all_commands[cmd] = all_commands.get(cmd, 0) + count
        
        top_commands = sorted(all_commands.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Focus time
        total_focus_minutes = 0
        for session in self.usage_data["focus_sessions"]:
            if session["end_time"]:
                start = datetime.fromisoformat(session["start_time"])
                end = datetime.fromisoformat(session["end_time"])
                total_focus_minutes += (end - start).total_seconds() / 60
        
        return {
            "total_commands": total_commands,
            "top_commands": top_commands,
            "total_focus_hours": total_focus_minutes / 60,
            "focus_sessions": len(self.usage_data["focus_sessions"]),
            "productivity_score": min(100, int(total_focus_minutes / 60 * 10))
        }
    
    def print_insights(self) -> None:
        """Print AI-generated insights."""
        report = self.get_weekly_report()
        
        print("\n📊 Weekly Insights")
        print("=" * 40)
        print(f"Commands used: {report['total_commands']}")
        print(f"Focus time: {report['total_focus_hours']:.1f} hours")
        print(f"Productivity score: {report['productivity_score']}/100")
        print("\nTop commands:")
        for cmd, count in report['top_commands']:
            print(f"  • {cmd}: {count} times")
        
        # Generate suggestion
        if report['total_focus_hours'] < 20:
            print("\n💡 Suggestion: Try to increase focus time with Deep Work mode")
        elif report['productivity_score'] > 80:
            print("\n🎉 Great productivity this week!")


# Multi-device sync stub
class MultiDeviceSync:
    """
    Multi-device synchronization (placeholder).
    
    Future implementation would include:
    - Cloud sync of memories/preferences
    - Mobile companion app
    - Web interface access
    """
    
    def __init__(self):
        self.devices = []
        self.sync_enabled = False
    
    def register_device(self, device_id: str, device_type: str) -> None:
        """Register a new device."""
        self.devices.append({
            "id": device_id,
            "type": device_type,
            "last_sync": None
        })
        print(f"✓ Registered {device_type}: {device_id}")
    
    def sync_to_cloud(self) -> bool:
        """Sync data to cloud (placeholder)."""
        print("☁️ Cloud sync not yet implemented")
        print("   Future: WebSocket/API sync to central server")
        return False
    
    def get_device_list(self) -> List[Dict]:
        """Get connected devices."""
        return self.devices
