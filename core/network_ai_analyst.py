"""
core/network_ai_analyst.py — LLM-powered network intelligence analyst.

Uses the LLM router to generate insights about the network graph:
- Device identification and classification
- Anomaly explanation with natural language
- Threat summarisation
- Behavioural profiling
- Network health reports
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List

from core.network_topology_graph import NetworkTopologyGraph, get_network_graph

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are DEEP's Network Intelligence Analyst. You analyse network topology data and provide concise, actionable insights.

Rules:
- Be specific — name IPs, MACs, and devices when relevant.
- Use security terminology correctly but explain briefly.
- Flag anything suspicious with confidence levels.
- Keep responses under 200 words unless asked for detail.
- Format with bullet points for readability.
"""


class NetworkAIAnalyst:
    """LLM-powered analyst for the network graph."""

    def __init__(
        self,
        llm_client: Any,
        event_bus: Any,
        graph: Optional[NetworkTopologyGraph] = None,
    ) -> None:
        self._llm = llm_client
        self._event_bus = event_bus
        self._graph = graph or get_network_graph()
        self._started = False
        self._analysis_task: Optional[asyncio.Task] = None
        self._check_interval = 300  # run analysis every 5 minutes

    async def start(self) -> None:
        self._started = True
        self._analysis_task = asyncio.create_task(self._analysis_loop())
        logger.info("NetworkAIAnalyst started")

    async def stop(self) -> None:
        self._started = False
        if self._analysis_task and not self._analysis_task.done():
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass
        logger.info("NetworkAIAnalyst stopped")

    async def _analysis_loop(self) -> None:
        while self._started:
            try:
                await asyncio.wait_for(asyncio.sleep(self._check_interval), timeout=self._check_interval)
            except asyncio.TimeoutError:
                pass
            if not self._started:
                break
            try:
                await self._periodic_analysis()
            except Exception as exc:
                logger.warning(f"Periodic analysis error: {exc}")

    async def _periodic_analysis(self) -> None:
        """Run periodic auto-analysis on key nodes."""
        # Analyse unknown devices
        unknowns = self._graph.list_nodes(layer="lan")
        for node in unknowns:
            if node.metadata.get("trust") == "unknown":
                await self._analyse_device(node.id)

    # ── Public analysis methods ───────────────────────────────────────────────
    async def analyse_device(self, node_id: str) -> Dict[str, Any]:
        """Analyse a single device and return structured inference."""
        node = self._graph.get_node(node_id)
        if not node:
            return {"error": "node not found"}

        # Gather observations
        obs = self._graph.get_observations(node_id, hours=24)
        edges = self._graph.get_edges(node_id=node_id)
        connected = [e.target_id if e.source_id == node_id else e.source_id for e in edges]

        # Build prompt
        prompt = self._build_device_prompt(node, obs, connected)
        inference = await self._call_llm(prompt)

        # Store inference
        self._graph.add_inference(
            node_id=node_id,
            inference_type="device_analysis",
            confidence=inference.get("confidence", 0.7),
            explanation=inference.get("explanation", "No insight generated."),
            context={"type": node.node_type, "metadata": node.metadata, "connected_count": len(connected)},
        )

        # Publish event
        await self._event_bus.publish("network_insight", {
            "type": "device_analysis",
            "node_id": node_id,
            "inference": inference,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return inference

    async def explain_anomaly(self, node_id: str, metric: str, value: float, expected: float) -> Dict[str, Any]:
        """Explain why a metric is anomalous."""
        node = self._graph.get_node(node_id)
        if not node:
            return {"error": "node not found"}

        # Get baseline stats for context
        baseline = self._graph.get_observations(node_id, metric=metric, hours=168)  # 7 days
        baseline_values = [o["value"] for o in baseline if o["value"] is not None]

        prompt = (
            f"Device: {node.label} ({node.metadata.get('ip', 'unknown IP')})\n"
            f"Metric: {metric}\n"
            f"Current value: {value:.2f}\n"
            f"Expected value: {expected:.2f}\n"
            f"Deviation: {((value - expected) / expected * 100):.1f}%\n"
            f"Historical 7-day values: {baseline_values[-10:] if len(baseline_values) <= 10 else baseline_values[-10:]}\n\n"
            f"Explain why this is anomalous. What could cause this? Is it benign or suspicious?"
        )

        inference = await self._call_llm(prompt)
        self._graph.add_inference(
            node_id=node_id,
            inference_type="anomaly_explanation",
            confidence=inference.get("confidence", 0.6),
            explanation=inference.get("explanation", "No explanation generated."),
            context={"metric": metric, "value": value, "expected": expected},
        )

        await self._event_bus.publish("network_insight", {
            "type": "anomaly_explanation",
            "node_id": node_id,
            "inference": inference,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return inference

    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive network health report."""
        stats = self._graph.stats()
        nodes = self._graph.list_nodes(limit=50)
        threats = [n for n in nodes if n.metadata.get("threat_type")]
        rogues = [n for n in nodes if n.metadata.get("rogue")]
        unknowns = [n for n in nodes if n.metadata.get("trust") == "unknown"]

        prompt = (
            f"Network Health Report — {datetime.now(timezone.utc).isoformat()}\n"
            f"Total nodes: {sum(stats['nodes_by_layer'].values())}\n"
            f"By layer: {stats['nodes_by_layer']}\n"
            f"Active threats: {len(threats)}\n"
            f"Rogue APs: {len(rogues)}\n"
            f"Unknown devices: {len(unknowns)}\n"
            f"Recent inferences: {stats['inferences']}\n\n"
            f"Provide a concise health report with: (1) overall security posture, "
            f"(2) top 3 concerns, (3) recommended actions."
        )

        inference = await self._call_llm(prompt)
        self._graph.add_inference(
            node_id="_network",
            inference_type="health_report",
            confidence=inference.get("confidence", 0.7),
            explanation=inference.get("explanation", ""),
            context={"stats": stats},
        )

        return inference

    async def summarise_threats(self, hours: int = 24) -> Dict[str, Any]:
        """Summarise recent threats in natural language."""
        # Query events from graph (could also query threat_monitor directly)
        all_nodes = self._graph.list_nodes()
        threat_nodes = [n for n in all_nodes if n.metadata.get("threat_type")]

        if not threat_nodes:
            return {"explanation": "No threats detected in the analysed period.", "confidence": 1.0}

        prompt = "Recent security threats:\n"
        for n in threat_nodes[:10]:
            prompt += (
                f"- {n.label}: {n.metadata.get('threat_type', 'unknown')} "
                f"(confidence: {n.metadata.get('confidence', 'N/A')})\n"
            )
        prompt += "\nSummarise these threats. Are they related? What is the attacker's likely goal?"

        return await self._call_llm(prompt)

    # ── Internal helpers ──────────────────────────────────────────────────
    async def _analyse_device(self, node_id: str) -> Dict[str, Any]:
        return await self.analyse_device(node_id)

    def _build_device_prompt(self, node, obs: list, connected: list) -> str:
        meta = node.metadata
        ports = meta.get("open_ports", [])
        os_guess = meta.get("os_guess", "")
        mac = meta.get("mac", "")
        vendor = meta.get("vendor", "")

        prompt = f"Device: {node.label}\n"
        prompt += f"IP: {meta.get('ip', 'unknown')}\n"
        prompt += f"MAC: {mac}\n"
        prompt += f"Vendor: {vendor or 'unknown'}\n"
        if os_guess:
            prompt += f"OS guess: {os_guess}\n"
        if ports:
            prompt += f"Open ports: {ports}\n"
        prompt += f"Connected to: {len(connected)} other nodes\n"
        if obs:
            prompt += f"Recent metrics: {[o['metric'] for o in obs[:5]]}\n"
        prompt += "\nIdentify what kind of device this likely is. Explain your reasoning. Flag anything suspicious."
        return prompt

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call the LLM client and parse the response."""
        if not self._llm:
            return {"explanation": "LLM not available.", "confidence": 0.0}

        try:
            # The OllamaClient has .generate(system_prompt, user_prompt)
            response = await self._llm.generate(SYSTEM_PROMPT, prompt)
            text = response.text if hasattr(response, "text") else str(response)
            return {
                "explanation": text,
                "confidence": 0.75,  # LLM confidence baseline
                "raw": text,
            }
        except Exception as exc:
            logger.warning(f"LLM analysis failed: {exc}")
            return {"explanation": f"Analysis failed: {exc}", "confidence": 0.0, "error": str(exc)}
