"""
deep/ai/agent_swarm.py

AutoGen-style multi-agent system for DEEP.
Spawned ONLY when the Pipeline intent is one of:
    - research_task
    - planning_task
    - multi_step_execution

All agents share a single asyncio.Queue for messages.
Message format:
    AgentMessage(sender, recipient, type, content, task_id, timestamp)

Agents:
    OrchestratorAgent — decomposes missions, assigns sub-tasks,
                        aggregates results, publishes "swarm_complete".
    ResearcherAgent   — DuckDuckGo instant answers + Ollama summarisation.
    PlannerAgent      — Ollama → structured JSON plan.
    ExecutorAgent     — publishes "skill_invoke" on EventBus,
                        monitors "skill_result" with timeout.

Configuration (from config.py):
    SWARM_AGENT_TIMEOUT_SECONDS  — per-agent timeout
    SWARM_MAX_PARALLEL           — max concurrent agents
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed — AgentSwarm LLM calls will fail")

try:
    from core.config import Settings
except ImportError:
    from config import Settings

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus


# ═══════════════════════════════════════════════════════════════════════════════
# Message Bus (shared Queue)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentMessage:
    """Message passed between swarm agents."""

    sender: str
    recipient: str
    type: str          # "task", "result", "status", "heartbeat"
    content: Any
    task_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Swarm
# ═══════════════════════════════════════════════════════════════════════════════

class AgentSwarm:
    """
    Top-level coordinator for the multi-agent swarm.

    Lifecycle: __init__ → start() → receive_mission() → stop() → status()
    """

    # Intents that trigger the swarm (keep in sync with Pipeline)
    TRIGGER_INTENTS = {"research_task", "planning_task", "multi_step_execution"}

    def __init__(
        self,
        event_bus: EventBus,
        settings: Optional[Settings] = None,
        knowledge_store=None,
        ingester=None,
    ) -> None:
        self.event_bus = event_bus
        self.settings = settings or Settings()
        self.queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._started = False
        self._client: Optional[Any] = None
        if HTTPX_AVAILABLE:
            self._client = httpx.AsyncClient(timeout=30.0)

        # Child agents
        self.orchestrator = OrchestratorAgent(self.queue, self.settings, self._client)
        self.researcher = ResearcherAgent(
            self.queue, self.settings, self._client,
            knowledge_store=knowledge_store, ingester=ingester,
        )
        self.planner = PlannerAgent(self.queue, self.settings, self._client)
        self.executor = ExecutorAgent(self.queue, self.settings, self._client, self.event_bus)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to pipeline decisions and boot background workers."""
        self.event_bus.subscribe("routed_command", self._on_routed_command)
        self._started = True
        logger.info("[AgentSwarm] Started — listening for routed_command events")

    async def stop(self) -> None:
        """Cancel background tasks, drain queue, close client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._started = False
        logger.info("[AgentSwarm] Stopped")

    def status(self) -> Dict[str, Any]:
        return {
            "started": self._started,
            "queue_size": self.queue.qsize(),
            "trigger_intents": list(self.TRIGGER_INTENTS),
        }

    # ── Entry point ───────────────────────────────────────────────────────

    async def _on_routed_command(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Intercept routed commands that need the swarm."""
        intent = payload.get("intent", "")
        if intent in self.TRIGGER_INTENTS:
            mission = payload.get("command", "")
            logger.info(f"[AgentSwarm] Swarm triggered for intent='{intent}'")
            await self.receive_mission(mission)

    async def receive_mission(self, mission: str) -> List[AgentMessage]:
        """
        Public API: hand a high-level mission to the Orchestrator.
        Returns the full message trace (for introspection / testing).
        """
        if not self._started:
            logger.warning("[AgentSwarm] receive_mission called before start()")
            return []

        # Seed the queue with the mission
        await self.queue.put(AgentMessage(
            sender="user",
            recipient="orchestrator",
            type="task",
            content={"mission": mission},
            task_id=f"mission-{int(time.time())}",
        ))

        # Launch agents with max concurrency limit
        max_parallel = getattr(self.settings, "swarm_max_parallel", 4)
        sem = asyncio.Semaphore(max_parallel)

        async def _run_with_sem(agent_name: str, coro):
            async with sem:
                try:
                    await coro
                except Exception as e:
                    logger.error(f"[AgentSwarm] {agent_name} crashed: {e}")

        # Start all agent loops concurrently
        await asyncio.gather(
            _run_with_sem("orchestrator", self.orchestrator.run()),
            _run_with_sem("researcher", self.researcher.run()),
            _run_with_sem("planner", self.planner.run()),
            _run_with_sem("executor", self.executor.run()),
            return_exceptions=True,
        )

        # Drain remaining messages for trace
        trace: List[AgentMessage] = []
        while not self.queue.empty():
            try:
                msg = self.queue.get_nowait()
                trace.append(msg)
            except asyncio.QueueEmpty:
                break
        return trace


# ═══════════════════════════════════════════════════════════════════════════════
# OrchestratorAgent
# ═══════════════════════════════════════════════════════════════════════════════

class OrchestratorAgent:
    """
    Mission control: decomposes, assigns, aggregates, signals completion.
    """

    def __init__(
        self,
        queue: asyncio.Queue[AgentMessage],
        settings: Settings,
        client: Optional[Any],
    ) -> None:
        self.queue = queue
        self.settings = settings
        self._client = client

    async def run(self) -> None:
        """Main loop: wait for a mission task, decompose, assign, aggregate."""
        while True:
            msg = await self.queue.get()
            if msg.type == "task" and msg.recipient == "orchestrator":
                mission = msg.content.get("mission", "")
                task_id = msg.task_id

                # Step 1 — Decompose
                subtasks = await self._decompose(mission)
                if not subtasks:
                    logger.warning(f"[Orchestrator] Decomposition returned empty for: {mission[:40]}")
                    continue

                # Step 2 — Assign to agents via queue
                results: List[Dict[str, Any]] = []
                for st in subtasks:
                    await self.queue.put(AgentMessage(
                        sender="orchestrator",
                        recipient=st["agent"],
                        type="task",
                        content=st,
                        task_id=task_id,
                    ))

                # Step 3 — Collect results (with timeout per subtask)
                timeout = getattr(self.settings, "swarm_agent_timeout_seconds", 30)
                pending = len(subtasks)
                start = time.monotonic()
                while pending > 0 and (time.monotonic() - start) < timeout * len(subtasks):
                    try:
                        result_msg = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                        if result_msg.type == "result" and result_msg.recipient == "orchestrator":
                            results.append({
                                "agent": result_msg.sender,
                                "output": result_msg.content,
                            })
                            pending -= 1
                    except asyncio.TimeoutError:
                        logger.warning("[Orchestrator] Result collection timed out")
                        break

                # Step 4 — Aggregate
                summary = await self._aggregate(mission, results)
                logger.info(f"[Orchestrator] Swarm complete for '{mission[:40]}'")

                # Publish completion event
                # We don't have direct access to EventBus here, but the outer
                # AgentSwarm can pick it up if we put it back on the queue.
                await self.queue.put(AgentMessage(
                    sender="orchestrator",
                    recipient="swarm_complete",
                    type="result",
                    content={"summary": summary, "subtask_results": results},
                    task_id=task_id,
                ))

            # Graceful exit condition — empty queue after all work done
            if self.queue.empty():
                await asyncio.sleep(0.1)
                if self.queue.empty():
                    break

    async def _decompose(self, mission: str) -> List[Dict[str, Any]]:
        """
        Ask Ollama to decompose the mission into subtasks.
        Expected response: JSON list of {"task": str, "agent": str, "input": str}
        """
        if not HTTPX_AVAILABLE or not self._client:
            # Fallback — single executor subtask
            return [{"task": mission, "agent": "executor", "input": mission}]

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        prompt = (
            f"Decompose this mission into subtasks.\n"
            f"Mission: {mission}\n\n"
            f"Reply ONLY as a JSON list:\n"
            f"[{{'task': str, 'agent': str, 'input': str}}]\n"
            f"Available agents: researcher, planner, executor.\n"
            f"No extra text — just the JSON list."
        )

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "")

            # Strip markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw.rsplit("\n", 1)[0]
            raw = raw.strip()

            subtasks = json.loads(raw)
            if isinstance(subtasks, list) and len(subtasks) > 0:
                # Validate agent names
                valid_agents = {"researcher", "planner", "executor"}
                return [st for st in subtasks if st.get("agent") in valid_agents]
        except Exception as e:
            logger.warning(f"[Orchestrator] Decomposition failed: {e}")

        # Fallback — single executor subtask
        return [{"task": mission, "agent": "executor", "input": mission}]

    async def _aggregate(self, mission: str, results: List[Dict[str, Any]]) -> str:
        """
        Ask Ollama to synthesise a final summary from subtask results.
        """
        if not HTTPX_AVAILABLE or not self._client:
            # Simple concat fallback
            return "\n".join(
                f"[{r['agent']}] {r['output']}" for r in results
            )

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        results_text = json.dumps(results, indent=2)
        prompt = (
            f"Synthesise a final summary for this mission.\n"
            f"Mission: {mission}\n\n"
            f"Subtask results:\n{results_text}\n\n"
            f"Provide a concise, well-structured summary."
        )

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "(no summary generated)")
        except Exception as e:
            logger.warning(f"[Orchestrator] Aggregation failed: {e}")
            return "\n".join(
                f"[{r['agent']}] {r['output']}" for r in results
            )


# ═══════════════════════════════════════════════════════════════════════════════
# ResearcherAgent
# ═══════════════════════════════════════════════════════════════════════════════

class ResearcherAgent:
    """
    Uses DuckDuckGo instant answer API (no key needed) and
    summarises findings with Ollama.
    """

    DUCKDUCKGO_API = "https://api.duckduckgo.com/"

    def __init__(
        self,
        queue: asyncio.Queue[AgentMessage],
        settings: Settings,
        client: Optional[Any],
        knowledge_store=None,
        ingester=None,
    ) -> None:
        self.queue = queue
        self.settings = settings
        self._client = client
        self.knowledge_store = knowledge_store
        self.ingester = ingester

    async def run(self) -> None:
        while True:
            msg = await self.queue.get()
            if msg.type == "task" and msg.recipient == "researcher":
                query = msg.content.get("input", "")
                result = await self._research(query)
                await self.queue.put(AgentMessage(
                    sender="researcher",
                    recipient="orchestrator",
                    type="result",
                    content=result,
                    task_id=msg.task_id,
                ))
            if self.queue.empty():
                await asyncio.sleep(0.1)
                if self.queue.empty():
                    break

    async def _research(self, query: str) -> Dict[str, Any]:
        """
        Two-stage search:
            1. Search knowledge_store (instant)
            2. If < 3 results: ingest domain + search again
            3. Fallback: DuckDuckGo instant answer
        """
        # Stage 1 — Knowledge store search (instant)
        local_results: List[Any] = []
        if self.knowledge_store and self.knowledge_store._started:
            try:
                local_results = await self.knowledge_store.search(query, n_results=5)
            except Exception as e:
                logger.debug(f"[ResearcherAgent] knowledge_store search error: {e}")

        # Stage 2 — If sparse, try live ingestion
        if len(local_results) < 3 and self.ingester:
            try:
                # Detect domain from query keywords
                domain_map = {
                    "quantum": "quantum",
                    "ai": "ai_ml",
                    "machine learning": "ai_ml",
                    "robot": "robotics",
                    "cyber": "cybersecurity",
                    "security": "cybersecurity",
                    "space": "space",
                    "astro": "space",
                    "physics": "physics",
                    "math": "mathematics",
                    "protein": "biomedical",
                    "crispr": "biomedical",
                    "neural": "ai_ml",
                }
                detected_domain = None
                query_lower = query.lower()
                for keyword, domain in domain_map.items():
                    if keyword in query_lower:
                        detected_domain = domain
                        break

                if detected_domain:
                    await self.ingester.ingest_domain(detected_domain)
                    local_results = await self.knowledge_store.search(query, n_results=5)
            except Exception as e:
                logger.debug(f"[ResearcherAgent] live ingestion error: {e}")

        if len(local_results) >= 3:
            # Build findings from local papers
            findings = "\n".join(
                f"- {p.title} ({p.domain}): {p.abstract[:200]}"
                for p in local_results[:5]
            )
            sources = [p.url for p in local_results[:5] if p.url]
            return {
                "query": query,
                "findings": findings,
                "sources": sources,
                "from_store": True,
            }

        # Stage 3 — DuckDuckGo fallback
        if not HTTPX_AVAILABLE or not self._client:
            return {"query": query, "findings": "(httpx unavailable)", "sources": []}

        try:
            url = (
                f"{self.DUCKDUCKGO_API}?"
                f"{urllib.parse.urlencode({'q': query, 'format': 'json', 'no_html': '1', 'skip_disambig': '1'})}"
            )
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()

            abstract = data.get("Abstract", "")
            related = data.get("RelatedTopics", [])
            sources = [rt.get("FirstURL", "") for rt in related if rt.get("FirstURL")]
            sources = [s for s in sources if s]

            # Summarise with Ollama
            findings = await self._summarise(query, abstract, related)
            return {
                "query": query,
                "findings": findings,
                "sources": sources[:5],
                "from_store": False,
            }
        except Exception as e:
            logger.warning(f"[ResearcherAgent] Research error: {e}")
            return {"query": query, "findings": f"(error: {e})", "sources": []}

    async def _summarise(
        self,
        query: str,
        abstract: str,
        related: List[Dict[str, Any]],
    ) -> str:
        """Ask Ollama to condense raw DDG results."""
        if not self._client:
            return abstract or "(no summary available)"

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        # Build a concise context string
        related_text = "\n".join(
            f"- {rt.get('Text', '')}" for rt in related[:3]
        )
        context = f"Abstract: {abstract}\nRelated:\n{related_text}"

        prompt = (
            f"Summarise the following research results for the query: {query}\n\n"
            f"{context}\n\n"
            f"Provide a concise 2-3 sentence summary."
        )

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "(no summary)")
        except Exception as e:
            logger.warning(f"[ResearcherAgent] Summarisation failed: {e}")
            return abstract or "(no summary available)"


# ═══════════════════════════════════════════════════════════════════════════════
# PlannerAgent
# ═══════════════════════════════════════════════════════════════════════════════

class PlannerAgent:
    """
    Generates a structured JSON plan via Ollama.
    """

    def __init__(
        self,
        queue: asyncio.Queue[AgentMessage],
        settings: Settings,
        client: Optional[Any],
    ) -> None:
        self.queue = queue
        self.settings = settings
        self._client = client

    async def run(self) -> None:
        while True:
            msg = await self.queue.get()
            if msg.type == "task" and msg.recipient == "planner":
                goal = msg.content.get("input", "")
                context = msg.content.get("context", "")
                plan = await self._plan(goal, context)
                await self.queue.put(AgentMessage(
                    sender="planner",
                    recipient="orchestrator",
                    type="result",
                    content=plan,
                    task_id=msg.task_id,
                ))
            if self.queue.empty():
                await asyncio.sleep(0.1)
                if self.queue.empty():
                    break

    async def _plan(self, goal: str, context: str) -> Dict[str, Any]:
        """Ask Ollama for a structured plan."""
        if not HTTPX_AVAILABLE or not self._client:
            return {"goal": goal, "steps": [], "error": "httpx unavailable"}

        ollama_url = getattr(self.settings, "ollama_base_url", "http://localhost:11434")
        ollama_model = getattr(self.settings, "ollama_model", "llama3.2")

        prompt = (
            f"Create a structured plan for this goal.\n"
            f"Goal: {goal}\n"
            f"Context: {context}\n\n"
            f"Reply ONLY as a JSON list:\n"
            f"[{{'step': int, 'action': str, 'estimated_minutes': int, 'depends_on': [int]}}]\n"
            f"No extra text."
        )

        try:
            resp = await self._client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "")

            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw.rsplit("\n", 1)[0]
            raw = raw.strip()

            steps = json.loads(raw)
            if isinstance(steps, list):
                return {"goal": goal, "steps": steps}
        except Exception as e:
            logger.warning(f"[PlannerAgent] Planning failed: {e}")

        return {"goal": goal, "steps": [], "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutorAgent
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutorAgent:
    """
    Executes plan steps by publishing "skill_invoke" on the EventBus
    and monitoring "skill_result" events with timeout.
    """

    def __init__(
        self,
        queue: asyncio.Queue[AgentMessage],
        settings: Settings,
        client: Optional[Any],
        event_bus: EventBus,
    ) -> None:
        self.queue = queue
        self.settings = settings
        self._client = client
        self.event_bus = event_bus

    async def run(self) -> None:
        while True:
            msg = await self.queue.get()
            if msg.type == "task" and msg.recipient == "executor":
                input_data = msg.content.get("input", "")
                # If input is a plan (dict with steps), execute each step.
                # Otherwise treat it as a single skill invocation.
                if isinstance(input_data, dict) and "steps" in input_data:
                    result = await self._execute_plan(input_data)
                else:
                    result = await self._execute_skill(input_data)

                await self.queue.put(AgentMessage(
                    sender="executor",
                    recipient="orchestrator",
                    type="result",
                    content=result,
                    task_id=msg.task_id,
                ))
            if self.queue.empty():
                await asyncio.sleep(0.1)
                if self.queue.empty():
                    break

    async def _execute_skill(self, skill_request: str) -> Dict[str, Any]:
        """Publish a single skill invocation and wait for result."""
        if not self.event_bus:
            return {"status": "error", "detail": "EventBus unavailable"}

        timeout = getattr(self.settings, "tool_timeout_seconds", 10)
        result_future = asyncio.get_event_loop().create_future()

        def _make_handler(fut):
            async def _handler(event_name: str, payload: dict):
                if not fut.done():
                    fut.set_result(payload.get("result", "(no result)"))
            return _handler

        handler = _make_handler(result_future)
        self.event_bus.subscribe("skill_result", handler)

        await self.event_bus.publish("skill_invoke", {
            "skill": "general",
            "params": {"request": skill_request},
        })

        try:
            result = await asyncio.wait_for(result_future, timeout=timeout)
            return {"status": "success", "result": result}
        except asyncio.TimeoutError:
            return {"status": "timeout", "detail": f"no skill_result within {timeout}s"}
        finally:
            self.event_bus.unsubscribe("skill_result", handler)

    async def _execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute each step of a structured plan sequentially."""
        steps = plan.get("steps", [])
        step_results: List[Dict[str, Any]] = []

        for step in steps:
            action = step.get("action", "")
            result = await self._execute_skill(action)
            step_results.append({
                "step": step.get("step"),
                "action": action,
                "result": result,
            })

        all_ok = all(r["result"].get("status") == "success" for r in step_results)
        return {
            "status": "success" if all_ok else "partial_failure",
            "step_results": step_results,
        }
