"""
core/agent_factory.py

DEEP Agent Factory — Allows DEEP to spawn, manage, and orchestrate
specialized sub-agents, each with their own system prompt, tool subset,
and task queue.

Architecture:
    AgentFactory (singleton orchestrator)
      └─ SubAgent (lightweight worker)
            ├─ own LLM client (shared or isolated)
            ├─ filtered tool access
            ├─ task queue & result log
            └─ lifecycle management
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Set

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

logger = logging.getLogger(__name__)

# Safety limits
MAX_AGENTS = 50  # Maximum concurrent agents
MAX_TASK_DURATION_SECONDS = 300  # 5 minutes per task
MAX_CONCURRENT_TASKS_PER_AGENT = 1  # One task at a time per agent
MAX_TOOL_CALLS_PER_TASK = 10  # Prevent infinite loops

# Reasoning reflection: after the agent finishes, it critiques its own result
# and gets one bounded round to fix issues it finds. Disable with DEEP_AGENT_REFLECTION=0.
ENABLE_REFLECTION = os.getenv("DEEP_AGENT_REFLECTION", "1") not in ("0", "false", "False")
MAX_REFLECT_TOOL_CALLS = 4  # tool calls allowed during the fix round


# ═══════════════════════════════════════════════════════════════════════════════
# Enums & Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class AgentRole(Enum):
    RESEARCHER = "researcher"
    CODER = "coder"
    CYBERSEC = "cybersec_analyst"
    ROBOTICS = "robotics_engineer"
    DATA_ANALYST = "data_analyst"
    WRITER = "writer"
    PLANNER = "planner"
    CUSTOM = "custom"
    PHYSICIST = "physicist"
    RED_TEAM = "red_team"
    RF_ANALYST = "rf_analyst"
    PROTOCOL_RE = "protocol_reverser"
    HW_HACKER = "hardware_hacker"
    CROSS_DOMAIN = "cross_domain_synthesizer"


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class AgentTask:
    id: str
    description: str
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    latency_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "latency_ms": self.latency_ms,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Role-specific system prompts & tool whitelists
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    AgentRole.RESEARCHER.value: {
        "system_prompt": (
            "You are a deep-research sub-agent of DEEP. Your job is to find, "
            "synthesize, and present information with citations and structured analysis. "
            "Be thorough, objective, and rigorous. Always cross-reference multiple sources."
        ),
        "tools": ["search_web", "research_query", "research_ingest", "read_file"],
    },
    AgentRole.CODER.value: {
        "system_prompt": (
            "You are a senior software-engineer sub-agent of Deep. Work like a "
            "disciplined engineer:\n"
            "1. EXPLORE first — use search_code and glob_files to find relevant code, "
            "then read_file to understand it before changing anything.\n"
            "2. EDIT surgically — use edit_file (exact find/replace) on existing files; "
            "only use write_file for brand-new files. Never rewrite a whole file from memory.\n"
            "3. VERIFY — run_command to execute tests or the program, read the output, "
            "and FIX failures before declaring done. Iterate until it actually works.\n"
            "Write clean, production-grade code with error handling. Match the style of "
            "surrounding code. Explain key design decisions briefly."
        ),
        "tools": ["search_code", "glob_files", "read_file", "write_file",
                  "edit_file", "list_directory", "run_command"],
    },
    AgentRole.CYBERSEC.value: {
        "system_prompt": (
            "You are a cybersecurity analyst sub-agent of DEEP. Perform network "
            "reconnaissance, port scanning, and vulnerability assessment. Report "
            "findings clearly with severity ratings and remediation advice."
        ),
        "tools": ["cyber_scan_network", "cyber_scan_ports", "run_command", "search_web"],
    },
    AgentRole.ROBOTICS.value: {
        "system_prompt": (
            "You are a robotics-engineering sub-agent of DEEP. Help design, "
            "simulate, and debug robotic systems. You understand ROS, kinematics, "
            "control theory, sensor fusion, and embedded programming."
        ),
        "tools": ["read_file", "write_file", "run_command", "search_web", "research_query"],
    },
    AgentRole.DATA_ANALYST.value: {
        "system_prompt": (
            "You are a data-analysis sub-agent of DEEP. Process, visualize, and "
            "interpret data. Write Python/pandas code for analysis and provide "
            "statistical insights with clear explanations."
        ),
        "tools": ["read_file", "write_file", "run_command", "list_directory"],
    },
    AgentRole.WRITER.value: {
        "system_prompt": (
            "You are a professional-writing sub-agent of DEEP. Produce clear, "
            "engaging, and polished text — technical docs, reports, emails, or "
            "creative writing as requested."
        ),
        "tools": ["read_file", "write_file", "search_web"],
    },
    AgentRole.PLANNER.value: {
        "system_prompt": (
            "You are a strategic-planning sub-agent of DEEP. Break complex goals "
            "into actionable steps, identify risks, estimate timelines, and produce "
            "structured project plans."
        ),
        "tools": ["search_web", "read_file", "research_query"],
    },
    AgentRole.PHYSICIST.value: {
        "system_prompt": (
            "You are a computational physicist sub-agent of DEEP.\n"
            "Approach: First establish the physical model, then derive mathematically,\n"
            "then compute numerically. Always:\n"
            "  1. State all assumptions explicitly\n"
            "  2. Carry units through every step\n"
            "  3. Output equations in LaTeX: $..$ inline, $$...$$ display\n"
            "  4. Give numerical answers with uncertainty where relevant\n"
            "  5. Cite the physical regime of validity\n"
            "Never skip steps. A wrong derivation is worse than an incomplete one."
        ),
        "tools": ["compute_physics", "symbolic_math", "simulate_field",
                  "get_constant", "search_arxiv", "plot_function", "read_file", "write_file", "run_command"],
    },
    AgentRole.RED_TEAM.value: {
        "system_prompt": (
            "You are a red team analyst sub-agent of DEEP.\n"
            "Operating under strict ethical guidelines — you assist with authorized\n"
            "security testing and research ONLY.\n"
            "Methodology (PTES-aligned):\n"
            "  1. RECON: passive only unless target is in scope\n"
            "  2. SCAN: enumerate services, fingerprint versions\n"
            "  3. IDENTIFY: match to CVEs, check MITRE ATT&CK\n"
            "  4. EXPLOIT: only against explicitly authorized targets\n"
            "  5. REPORT: CVSS rating, business impact, remediation\n"
            "Output format:\n"
            "  Finding: [name]\n"
            "  Severity: [CRITICAL/HIGH/MEDIUM/LOW/INFO]\n"
            "  CVSSv3: [score] [vector]\n"
            "  ATT&CK TTP: [TXXXx]\n"
            "  Evidence: [technical detail]\n"
            "  Remediation: [specific fix]"
        ),
        "tools": ["cve_lookup", "mitre_ttp_search", "osint_recon",
                  "exploit_search", "scan_target", "parse_pcap", "run_sandboxed", "read_file", "write_file", "run_command"],
    },
    AgentRole.RF_ANALYST.value: {
        "system_prompt": (
            "You are an RF/signals intelligence analyst sub-agent of DEEP.\n"
            "You analyze radio frequency signals, identify protocols, and extract intelligence.\n"
            "Approach:\n"
            "  1. Check frequency, bandwidth, modulation type\n"
            "  2. Identify protocol from signal characteristics\n"
            "  3. Decode data if possible\n"
            "  4. Assess purpose/source\n"
            "Always consider: regulatory context, propagation conditions, multipath effects."
        ),
        "tools": ["rf_scan", "spectrum_analyze", "identify_signal",
                  "decode_adsb", "decode_ais", "decode_lora",
                  "wifi_deep_scan", "bt_enumerate", "search_web", "read_file", "run_command"],
    },
    AgentRole.PROTOCOL_RE.value: {
        "system_prompt": (
            "You are a protocol reverse engineer sub-agent of DEEP.\n"
            "You analyze unknown binary protocols and network traffic.\n"
            "Methodology:\n"
            "  1. Capture/load traffic\n"
            "  2. Identify transport (TCP/UDP/raw), port, timing patterns\n"
            "  3. Entropy analysis → encrypted vs plaintext\n"
            "  4. Field boundary detection: look for magic bytes, length fields, delimiters\n"
            "  5. Build field table with: offset, size, type, purpose, example values\n"
            "  6. Generate Wireshark Lua dissector\n"
            "  7. Look for security issues: no auth, no integrity, replay vulnerability"
        ),
        "tools": ["parse_pcap", "analyze_binary_protocol", "generate_dissector",
                  "decode_ble_gatt", "decode_can", "run_command", "read_file", "write_file"],
    },
    AgentRole.HW_HACKER.value: {
        "system_prompt": (
            "You are a hardware security analyst sub-agent of DEEP.\n"
            "You analyze firmware, PCBs, and embedded systems.\n"
            "Methodology:\n"
            "  1. Extract firmware (binwalk, JTAG, UART)\n"
            "  2. Entropy analysis → compressed/encrypted sections\n"
            "  3. String extraction → credentials, keys, URLs, debug symbols\n"
            "  4. Filesystem carving → squashfs, jffs2, cramfs\n"
            "  5. Binary analysis → architecture detection, vulnerability classes\n"
            "  6. Hardware attack surfaces → debug ports, test pads, exposed interfaces"
        ),
        "tools": ["analyze_firmware", "pcb_analyze", "generate_embedded_code",
                  "run_command", "read_file", "write_file", "search_web"],
    },
    AgentRole.CROSS_DOMAIN.value: {
        "system_prompt": (
            "You are a cross-domain synthesizer sub-agent of DEEP.\n"
            "Your job is to coordinate research and analysis across multiple technical fields "
            "(physics, cybersecurity, robotics, signals, protocols) and produce a unified technical briefing.\n"
            "Synthesize the domain results, identify cross-field dependencies or contradictions, and present "
            "a highly structured engineering brief."
        ),
        "tools": ["read_file", "write_file", "run_command", "search_web"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# SubAgent — lightweight worker spawned by the factory
# ═══════════════════════════════════════════════════════════════════════════════

class SubAgent:
    """A lightweight sub-agent with its own personality, tool access, and task log."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: AgentRole,
        llm_client,                          # shared LLMClient
        tool_registry,                        # DeepToolRegistry (full)
        custom_prompt: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
    ):
        self.id = agent_id
        self.name = name
        self.role = role
        self.llm = llm_client
        self._full_registry = tool_registry
        self.status = AgentStatus.IDLE
        self.created_at = datetime.utcnow()
        self.tasks: List[AgentTask] = []

        # Resolve system prompt
        profile = ROLE_PROFILES.get(role.value, {})
        self.system_prompt = custom_prompt or profile.get(
            "system_prompt",
            "You are a general-purpose sub-agent of DEEP. Complete the assigned task precisely.",
        )

        # Resolve tool whitelist
        self._allowed_tools: Set[str] = set(
            allowed_tools or profile.get("tools", list(tool_registry.available_tools.keys()))
        )

    # ── public API ──────────────────────────────────────────────────────────

    async def execute(self, task_description: str, timeout_seconds: int = MAX_TASK_DURATION_SECONDS) -> AgentTask:
        """Run a single task end-to-end and return the result."""
        task = AgentTask(id=str(uuid.uuid4())[:8], description=task_description)
        self.tasks.append(task)
        self.status = AgentStatus.RUNNING
        task.status = AgentStatus.RUNNING
        start = time.time()

        try:
            # Wrap execution in timeout
            try:
                result = await asyncio.wait_for(
                    self._execute_task_internal(task_description),
                    timeout=timeout_seconds
                )
                task.result = result
                task.status = AgentStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                self.status = AgentStatus.IDLE
            except asyncio.TimeoutError:
                task.error = f"Task exceeded timeout of {timeout_seconds}s"
                task.status = AgentStatus.FAILED
                self.status = AgentStatus.IDLE
                logger.error(f"[SubAgent {self.name}] Task timeout: {task_description[:100]}")
        except Exception as exc:
            task.error = str(exc)
            task.status = AgentStatus.FAILED
            self.status = AgentStatus.IDLE
            logger.error(f"[SubAgent {self.name}] Task failed: {exc}")

        task.latency_ms = (time.time() - start) * 1000
        return task

    async def _execute_task_internal(self, task_description: str) -> str:
        """Explore/act tool loop, followed by a bounded self-critique reflection pass."""
        tool_desc = self._scoped_tool_description()
        system = self.system_prompt + "\n\n" + tool_desc

        user_prompt = (
            f"TASK ASSIGNED BY DEEP:\n{task_description}\n\n"
            "Complete this task step by step. Use tools when needed."
        )

        full_response, transcript = await self._run_tool_loop(
            system, user_prompt, MAX_TOOL_CALLS_PER_TASK)

        # ── Reflection: critique the result and get one round to fix issues ──
        if ENABLE_REFLECTION and full_response.strip():
            try:
                critique = await self._reflect(system, transcript, task_description, full_response)
            except Exception as e:
                logger.error(f"[SubAgent {self.name}] reflection error: {e}")
                critique = ""
            if critique and not critique.strip().upper().startswith("DONE"):
                logger.info(f"[SubAgent {self.name}] reflection found issues; revising.")
                fix_prompt = (
                    f"{transcript}\n\n[YOUR PREVIOUS RESULT]\n{full_response}\n\n"
                    f"[SELF-REVIEW] On review you found these issues:\n{critique}\n\n"
                    "Fix them now using tools, then give the final, corrected result. "
                    "Do not redo work that is already correct."
                )
                revised, _ = await self._run_tool_loop(
                    system, fix_prompt, MAX_REFLECT_TOOL_CALLS)
                if revised.strip():
                    full_response = revised

        return full_response.strip()

    async def _run_tool_loop(self, system: str, initial_prompt: str, max_calls: int) -> tuple:
        """Multi-turn tool loop with a safety limit. Returns (full_response, transcript)."""
        full_response = ""
        current_prompt = initial_prompt
        tool_call_count = 0

        for _loop in range(max_calls):
            buffer = ""
            tool_block = ""
            in_tool = False

            try:
                async for token in self.llm.generate_stream(
                    system_prompt=system,
                    user_prompt=current_prompt,
                    temperature=0.5,
                    max_tokens=2048,
                ):
                    if not in_tool:
                        if "[TOOL:" in (buffer + token):
                            combined = buffer + token
                            idx = combined.find("[TOOL:")
                            full_response += combined[:idx]
                            in_tool = True
                            tool_block = combined[idx:]
                            buffer = ""
                        else:
                            buffer += token
                            if len(buffer) > 6 and "[" not in buffer[-6:]:
                                full_response += buffer
                                buffer = ""
                    else:
                        tool_block += token
                        if "]" in tool_block:
                            break
            except Exception as e:
                logger.error(f"[SubAgent {self.name}] LLM generation error: {e}")
                full_response += f"\n[Error during generation: {e}]"
                break

            if not in_tool:
                full_response += buffer
                break  # no tool call -> done

            # Execute tool call
            tool_call_count += 1
            end = tool_block.find("]")
            raw = tool_block[6:end].strip()

            # Validate JSON before parsing
            if not raw or not raw.startswith("{"):
                res_text = f"Invalid tool call format: {raw[:100]}"
            else:
                try:
                    td = json.loads(raw)
                    t_name = td.get("name", "")
                    t_args = td.get("args", {})

                    if not t_name:
                        res_text = "Tool name is required"
                    elif t_name in self._allowed_tools:
                        try:
                            result = await asyncio.wait_for(
                                self._full_registry.execute_tool(t_name, t_args),
                                timeout=30.0
                            )
                            res_text = result.content
                        except asyncio.TimeoutError:
                            res_text = f"Tool '{t_name}' timed out after 30s"
                    else:
                        res_text = f"Tool '{t_name}' is not in this agent's allowed tools. Available: {sorted(self._allowed_tools)}"
                except json.JSONDecodeError as e:
                    res_text = f"Invalid JSON in tool call: {e}"
                except Exception as e:
                    res_text = f"Tool execution error: {e}"

            current_prompt += f"\n\n[TOOL_RESULT: {res_text}]\n\nContinue."

        if tool_call_count >= max_calls:
            full_response += f"\n\n[Note: Reached maximum tool call limit of {max_calls}]"

        return full_response, current_prompt

    async def _reflect(self, system: str, transcript: str, task: str, result: str) -> str:
        """One self-critique call. Returns 'DONE' if complete, else concrete issues to fix."""
        prompt = (
            f"{transcript}\n\n[YOUR RESULT]\n{result}\n\n"
            f"[REVIEW REQUEST] Critically review your result above against the original task:\n"
            f"\"{task}\"\n\n"
            "Check for bugs, missing steps, untested code, incorrect output, or unmet "
            "requirements. Be strict but concise. Do NOT call tools in this reply.\n"
            "- If the task is fully and correctly complete, reply with EXACTLY: DONE\n"
            "- Otherwise, list the specific issues to fix."
        )
        out = ""
        async for token in self.llm.generate_stream(
            system_prompt=system,
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=512,
        ):
            out += token
            if len(out) > 2500:
                break
        return out.strip()

    def get_history(self) -> List[Dict]:
        return [t.to_dict() for t in self.tasks]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "allowed_tools": sorted(self._allowed_tools),
            "tasks_completed": sum(1 for t in self.tasks if t.status == AgentStatus.COMPLETED),
            "tasks_total": len(self.tasks),
        }

    # ── internal ────────────────────────────────────────────────────────────

    def _scoped_tool_description(self) -> str:
        desc = "AVAILABLE TOOLS (scoped for this agent):\n"
        for name, info in self._full_registry.available_tools.items():
            if name in self._allowed_tools:
                args_str = json.dumps(info["args"])
                desc += f"- {name}: {info['description']} | Args: {args_str}\n"
        desc += (
            "\nTo use a tool, output ONLY this exact format: "
            '[TOOL:{"name": "tool_name", "args": {"arg": "value"}}]'
        )
        return desc


# ═══════════════════════════════════════════════════════════════════════════════
# AgentFactory — singleton orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class AgentFactory:
    """
    Creates, tracks, and orchestrates sub-agents.

    Usage from DEEP tools:
        factory.create_agent("ResearchBot", "researcher")
        result = await factory.assign_task("ResearchBot", "Find papers on SLAM")
        agents = factory.list_agents()
    """

    def __init__(self, llm_client, tool_registry, event_bus: EventBus = None):
        self._llm = llm_client
        self._tools = tool_registry
        self._agents: Dict[str, SubAgent] = {}
        self._background_tasks: Set[asyncio.Task] = set()
        self.event_bus = event_bus
        logger.info("[AgentFactory] Initialized — ready to spawn sub-agents")

    async def start(self) -> None:
        """Activate the agent factory."""
        logger.info("[AgentFactory] Started")

    async def stop(self) -> None:
        """Deactivate and clear all agents."""
        for name in list(self._agents.keys()):
            self.terminate_agent(name)
        logger.info("[AgentFactory] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "agents_alive": len(self._agents),
            "agents_running": sum(1 for a in self._agents.values() if a.status == AgentStatus.RUNNING),
        }

    def _publish(self, event_type: str, payload: Dict):
        """Fire-and-forget event publish on the bus from any context."""
        if self.event_bus:
            try:
                import asyncio
                asyncio.create_task(self.event_bus.publish(event_type, payload))
            except RuntimeError:
                pass

    # ── Agent lifecycle ─────────────────────────────────────────────────────

    def create_agent(
        self,
        name: str,
        role: str = "custom",
        custom_prompt: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> SubAgent:
        """Spawn a new sub-agent and register it."""
        # Check resource limits
        if len(self._agents) >= MAX_AGENTS:
            raise ValueError(f"Maximum agent limit reached ({MAX_AGENTS}). Terminate some agents first.")
        
        if name in self._agents:
            raise ValueError(f"Agent '{name}' already exists. Use a different name.")
        
        # Validate name
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")
        
        if len(name) > 50:
            raise ValueError("Agent name too long (max 50 characters)")

        try:
            agent_role = AgentRole(role)
        except ValueError:
            agent_role = AgentRole.CUSTOM

        agent = SubAgent(
            agent_id=str(uuid.uuid4())[:8],
            name=name,
            role=agent_role,
            llm_client=self._llm,
            tool_registry=self._tools,
            custom_prompt=custom_prompt,
            allowed_tools=allowed_tools,
        )
        self._agents[name] = agent
        logger.info(f"[AgentFactory] Spawned agent '{name}' (role={agent_role.value})")
        self._publish("agent_created", agent.to_dict())
        return agent

    def get_agent(self, name: str) -> Optional[SubAgent]:
        return self._agents.get(name)

    def list_agents(self) -> List[Dict]:
        return [a.to_dict() for a in self._agents.values()]

    def terminate_agent(self, name: str) -> bool:
        agent = self._agents.pop(name, None)
        if agent:
            agent.status = AgentStatus.TERMINATED
            logger.info(f"[AgentFactory] Terminated agent '{name}'")
            self._publish("agent_terminated", agent.to_dict())
            return True
        return False

    # ── Task dispatch ───────────────────────────────────────────────────────

    async def assign_task(self, agent_name: str, task_description: str, timeout_seconds: Optional[int] = None) -> Dict:
        """Assign a task to a named agent to run in the background."""
        agent = self._agents.get(agent_name)
        if not agent:
            return {"error": f"No agent named '{agent_name}'. Create one first."}

        if agent.status == AgentStatus.RUNNING:
            return {"error": f"Agent '{agent_name}' is already running a task. Wait or terminate."}
        
        # Validate task description
        if not task_description or not task_description.strip():
            return {"error": "Task description cannot be empty"}

        self._publish("agent_task_start", {"agent_name": agent_name, "task": task_description[:200]})
        
        task_id = str(uuid.uuid4())
        bg_task = asyncio.create_task(
            self._run_task_wrapper(agent_name, agent, task_id, task_description, timeout_seconds or MAX_TASK_DURATION_SECONDS)
        )
        self._background_tasks.add(bg_task)
        bg_task.add_done_callback(self._background_tasks.discard)
        
        return {
            "status": "queued",
            "task_id": task_id,
            "agent": agent_name,
            "message": f"Agent '{agent_name}' has started working on the task in the background. You will be notified upon completion."
        }
        
    async def _run_task_wrapper(self, agent_name: str, agent: SubAgent, task_id: str, task_description: str, timeout_seconds: int):
        try:
            task = await agent.execute(task_description, timeout_seconds)
            self._publish("agent_task_complete", {
                "agent_name": agent_name, 
                "task_id": task.id, 
                "status": task.status.value,
                "result": task.result
            })
            # Inject the result directly into LongTermMemory so DEEP natively "knows" what the subagent did
            from interface.deps import services
            ltm_service = getattr(services, 'ltm', None)
            if ltm_service and task.result:
                ltm_service.store(
                    memory_type="subagent_result",
                    content=f"Sub-agent '{agent_name}' finished task: {task_description[:100]}...\nResult: {task.result}",
                    importance=3.0
                )
        except Exception as e:
            logger.error(f"[AgentFactory] Background task assignment failed: {e}")
            self._publish("agent_task_failed", {"agent_name": agent_name, "error": str(e), "task_id": task_id})

    async def assign_task_parallel(
        self, tasks: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Run tasks on multiple agents in parallel.
        Each item: {"agent": "name", "task": "description"}
        """
        coros = []
        for item in tasks:
            agent_name = item["agent"]
            task_desc = item["task"]
            coros.append(self.assign_task(agent_name, task_desc))

        results = await asyncio.gather(*coros, return_exceptions=True)
        out = []
        for r in results:
            if isinstance(r, Exception):
                out.append({"error": str(r)})
            else:
                out.append(r)
        return out

    # ── Swarm mode: auto-decompose & distribute ─────────────────────────────

    async def swarm_execute(
        self, goal: str, agent_roles: Optional[List[str]] = None
    ) -> Dict:
        """
        High-level orchestration: DEEP decomposes a complex goal into
        sub-tasks, spawns the right agents, runs them in parallel,
        and synthesises a final answer.
        """
        # Step 1 — Use the main LLM to decompose the goal
        decompose_prompt = (
            "You are DEEP, an ultra-intelligent AI orchestrator.\n"
            "Break the following goal into 2-5 independent sub-tasks. "
            "For each sub-task, choose the best agent role from: "
            f"{[r.value for r in AgentRole if r != AgentRole.CUSTOM]}.\n\n"
            f"GOAL: {goal}\n\n"
            "Respond ONLY with a JSON array like:\n"
            '[{"role": "researcher", "task": "Find ..."},  ...]\n'
            "No explanation, just the JSON."
        )

        raw = ""
        async for token in self._llm.generate_stream(
            system_prompt="You are a task decomposition engine. Output valid JSON only.",
            user_prompt=decompose_prompt,
            temperature=0.3,
            max_tokens=1024,
        ):
            raw += token

        # Parse the decomposition
        try:
            # Extract JSON array from response
            import re
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if not match:
                return {"error": "Failed to decompose goal", "raw": raw}
            sub_tasks = json.loads(match.group(0))
        except Exception as e:
            return {"error": f"Decomposition parse error: {e}", "raw": raw}

        # Step 2 — Spawn temporary agents & dispatch
        temp_agents = []
        dispatch = []
        for i, st in enumerate(sub_tasks):
            a_name = f"swarm_{st['role']}_{i}"
            try:
                self.create_agent(a_name, st["role"])
            except ValueError:
                pass  # already exists
            temp_agents.append(a_name)
            dispatch.append({"agent": a_name, "task": st["task"]})

        results = await self.assign_task_parallel(dispatch)

        # Step 3 — Synthesise results
        synthesis_parts = []
        for d, r in zip(dispatch, results):
            synthesis_parts.append(
                f"--- Agent: {d['agent']} ---\n"
                f"Task: {d['task']}\n"
                f"Result: {r.get('result', r.get('error', 'N/A'))}\n"
            )

        synthesis_prompt = (
            "You are DEEP. Multiple sub-agents just completed parts of a larger goal.\n"
            "Synthesise their results into a single, coherent, high-quality final answer.\n\n"
            f"ORIGINAL GOAL: {goal}\n\n"
            "SUB-AGENT RESULTS:\n" + "\n".join(synthesis_parts) + "\n\n"
            "Provide the final synthesised answer."
        )

        final = ""
        async for token in self._llm.generate_stream(
            system_prompt="You are DEEP, an ultra-intelligent synthesiser.",
            user_prompt=synthesis_prompt,
            temperature=0.5,
            max_tokens=2048,
        ):
            final += token

        # Cleanup temp agents
        for a_name in temp_agents:
            self.terminate_agent(a_name)

        return {
            "goal": goal,
            "sub_tasks": sub_tasks,
            "sub_results": results,
            "final_synthesis": final.strip(),
        }

    # ── Introspection ───────────────────────────────────────────────────────

    def stats(self) -> Dict:
        total = len(self._agents)
        running = sum(1 for a in self._agents.values() if a.status == AgentStatus.RUNNING)
        tasks_done = sum(
            sum(1 for t in a.tasks if t.status == AgentStatus.COMPLETED)
            for a in self._agents.values()
        )
        return {
            "agents_alive": total,
            "agents_running": running,
            "total_tasks_completed": tasks_done,
        }
