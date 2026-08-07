"""
core/knowledge_graph.py

DEEP Local Knowledge Graph — Entity-relationship memory with inference.

Replaces flat vector memory with interconnected knowledge:
    "Aryan" → likes → "Python"
    "Python" → used_in → "Project X"
    "Project X" → created_by → "Aryan"

Enables inference: "You usually code in Python, shall I open your IDE?"

Features:
- Lightweight entity extraction from text (no API key)
- Relationship inference from sentence patterns
- Graph traversal and path queries
- Confidence scoring for facts
- Conversation-linked provenance
- All local, persistent storage

Usage:
    from DEEP.core.knowledge_graph import KnowledgeGraph
    
    kg = KnowledgeGraph()
    kg.ingest("Aryan likes Python and uses VS Code for coding")
    
    # Query neighbors
    kg.get_neighbors("Aryan")
    
    # Find paths
    kg.find_paths("Aryan", "Python")
    
    # Query by relationship
    kg.query_relationship("Aryan", "likes")
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    from core.event_bus import EventBus
except ImportError:
    from event_bus import EventBus

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class EntityType(Enum):
    PERSON = "person"
    TECHNOLOGY = "technology"
    TOPIC = "topic"
    PROJECT = "project"
    PLACE = "place"
    ORGANIZATION = "organization"
    PREFERENCE = "preference"
    ACTION = "action"
    CONCEPT = "concept"
    UNKNOWN = "unknown"
    VULNERABILITY   = "vulnerability"   # CVE-XXXX-XXXXX
    EXPLOIT         = "exploit"         # PoC, technique name
    PROTOCOL        = "protocol"        # TCP, MQTT, CAN, GATT, etc.
    RF_FREQUENCY    = "rf_frequency"    # 2.4GHz ISM, 433MHz, etc.
    HARDWARE_DEVICE = "hardware_device" # chip, board, sensor
    PHYSICS_CONCEPT = "physics_concept" # Hamiltonian, dispersion relation
    THREAT_ACTOR    = "threat_actor"    # APT group
    IOC             = "ioc"            # IP, domain, hash
    NETWORK_DEVICE  = "network_device"  # IP + MAC


class RelationType(Enum):
    LIKES = "likes"
    USES = "uses"
    KNOWS = "knows"
    CREATED = "created"
    WORKS_ON = "works_on"
    LOCATED_IN = "located_in"
    RELATED_TO = "related_to"
    MENTIONED_IN = "mentioned_in"
    PREFERS = "prefers"
    LEARNS = "learns"
    BUILDS = "builds"
    STUDIES = "studies"
    HAS = "has"
    IS_A = "is_a"
    EXPLOITS        = "exploits"        # Exploit → Vulnerability
    PATCHES         = "patches"         # Fix → Vulnerability
    AFFECTS         = "affects"         # Vulnerability → HardwareDevice/Protocol
    TRANSMITS_ON    = "transmits_on"    # Protocol → RF_Frequency
    IMPLEMENTS      = "implements"      # HardwareDevice → Protocol
    DERIVED_FROM    = "derived_from"    # Physics concept chain
    ATTRIBUTED_TO   = "attributed_to"  # Exploit → ThreatActor
    COMMUNICATES_WITH = "communicates_with" # NetworkDevice → NetworkDevice
    RESOLVES_TO     = "resolves_to"    # IOC domain → IOC IP


@dataclass
class Entity:
    """A node in the knowledge graph."""
    id: str
    name: str
    type: EntityType
    aliases: List[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    mention_count: int = 1
    source_ids: List[str] = field(default_factory=list)  # conversation IDs
    description: str = ""   # concise LLM-extracted fact about this entity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "aliases": self.aliases,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "mention_count": self.mention_count,
            "description": self.description,
        }


@dataclass
class Relationship:
    """An edge in the knowledge graph."""
    id: str
    source: str  # entity ID
    target: str  # entity ID
    relation: RelationType
    confidence: float = 1.0
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    evidence: List[str] = field(default_factory=list)  # Text snippets
    source_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation.value,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence[:3],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Entity Extraction Patterns
# ═══════════════════════════════════════════════════════════════════════════════

# Technology keywords
_TECH_KEYWORDS = {
    "python", "javascript", "java", "rust", "cpp", "c++", "go", "typescript",
    "react", "vue", "angular", "django", "flask", "fastapi", "docker", "kubernetes",
    "aws", "azure", "gcp", "linux", "windows", "macos", "ubuntu", "debian",
    "vscode", "vs code", "visual studio", "pycharm", "intellij", "vim", "neovim",
    "git", "github", "gitlab", "ollama", "chromadb", "postgres", "mongodb",
    "redis", "sqlite", "mysql", "nginx", "apache", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "jupyter", "colab", "three.js", "threejs",
}

# Common person indicators
_PERSON_INDICATORS = {
    "aryan", "i", "me", "my", "mine", "myself",
}

# Project indicators
_PROJECT_PATTERNS = {
    "project", "app", "application", "system", "platform", "tool",
    "website", "dashboard", "bot", "agent", "model", "framework",
    "deep", "jarvis", "ui", "api", "backend", "frontend",
}

# Topic/concept indicators
_TOPIC_PATTERNS = {
    "ai", "machine learning", "deep learning", "neural network",
    "blockchain", "cybersecurity", "devops", "cloud", "data science",
    "web development", "mobile", "automation", "robotics", "iot",
    "algorithm", "database", "api", "microservices", "architecture",
}

# Expert domain keywords
_FREQ_KEYWORDS = {
    "2.4ghz", "5ghz", "433mhz", "868mhz", "915mhz", "ism band", "lora", "zigbee", "zwave", "bluetooth"
}

_CHIP_KEYWORDS = {
    "esp32", "stm32", "atmega", "raspberry pi", "arduino", "nrf52", "cc2650", "bcm2835", "cortex-m4"
}

_PHYSICS_TERMS = {
    "hamiltonian", "lagrangian", "maxwell", "schrödinger", "schrodinger", "navier-stokes", "boltzmann", "eigenvalue", "fourier", "plasma"
}

_PROTOCOL_NAMES = {
    "mqtt", "modbus", "dnp3", "profibus", "canbus", "can fd", "gatt", "ble", "coap", "tcp", "udp", "http"
}

_RELATION_PATTERNS: List[Tuple[RelationType, List[str]]] = [
    (RelationType.LIKES, ["like", "love", "enjoy", "prefer", "favorite", "fan of", "into", "keen on"]),
    (RelationType.USES, ["use", "using", "run", "running", "built with", "developed with", "work with", "code in"]),
    (RelationType.KNOWS, ["know", "understand", "familiar with", "expert in", "skilled at", "good at"]),
    (RelationType.CREATED, ["create", "made", "built", "developed", "wrote", "designed", "authored"]),
    (RelationType.WORKS_ON, ["work on", "working on", "project is", "building", "developing", "maintaining"]),
    (RelationType.LEARNS, ["learn", "learning", "study", "studying", "read about", "researching"]),
    (RelationType.HAS, ["have", "has", "own", "possess", "contain", "include"]),
    (RelationType.LOCATED_IN, ["live in", "from", "based in", "located in", "in", "at"]),
    (RelationType.RELATED_TO, ["related to", "connected to", "associated with", "part of", "involves"]),
    (RelationType.EXPLOITS, ["exploit", "exploited by", "attacks"]),
    (RelationType.PATCHES, ["patch", "fix", "mitigate", "remediate"]),
    (RelationType.AFFECTS, ["affect", "vulnerable", "exposed"]),
    (RelationType.TRANSMITS_ON, ["transmit on", "broadcast on", "send on"]),
    (RelationType.IMPLEMENTS, ["implement", "run", "hardware supports"]),
    (RelationType.DERIVED_FROM, ["derived from", "proven from"]),
    (RelationType.ATTRIBUTED_TO, ["attributed to", "threat actor"]),
    (RelationType.COMMUNICATES_WITH, ["communicate with", "connect to", "talk to"]),
    (RelationType.RESOLVES_TO, ["resolve to", "points to"]),
]

# ═══════════════════════════════════════════════════════════════════════════════
# Knowledge Graph
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """
    Local entity-relationship graph for DEEP memory.
    """

    def __init__(self, data_dir: Optional[Path] = None, event_bus: EventBus = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data" / "knowledge_graph"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Graph storage
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self._entity_name_map: Dict[str, str] = {}  # lowercase name -> entity ID
        
        # Adjacency: entity_id -> list of (target_id, relation, edge_id)
        self._adj: Dict[str, List[Tuple[str, RelationType, str]]] = defaultdict(list)
        
        self.event_bus = event_bus
        self.extractor = None   # optional LLM extractor (set_extractor); regex is the fallback
        self._ingest_lock = asyncio.Lock()   # serialize concurrent background LLM ingests
        
        # Load state
        self._load_state()

    async def start(self) -> None:
        """Activate the knowledge graph."""
        logger.info("[KnowledgeGraph] Started")

    async def stop(self) -> None:
        """Deactivate the knowledge graph."""
        logger.info("[KnowledgeGraph] Stopped")

    def status(self) -> Dict[str, Any]:
        """Return operational status."""
        return {
            "entities": len(self.entities),
            "relationships": len(self.relationships),
        }

    def _publish(self, event_type: str, payload: Dict):
        """Fire-and-forget event publish on the bus from any context."""
        if self.event_bus:
            try:
                asyncio.create_task(self.event_bus.publish(event_type, payload))
            except RuntimeError:
                pass

    # ─── Persistence (SQLite, with one-time JSON migration + JSON backup) ─────
    #
    # Storage moved from a whole-file graph.json (re-parsed/rewritten in full on
    # every ingest) to SQLite: row-based upserts in a transaction, durable, and
    # queryable. The legacy graph.json is migrated once (and kept as a backup);
    # a JSON snapshot is still written alongside each save as a belt-and-braces
    # backup. Crucially, last_seen / first_seen / source_ids are now persisted in
    # full — the old Relationship.to_dict() dropped last_seen, which silently
    # reset every fact's age to "now" on each restart and defeated decay.

    def _state_file(self) -> Path:
        return self.data_dir / "graph.json"

    def _db_file(self) -> Path:
        return self.data_dir / "graph.db"

    def _connect(self):
        import sqlite3
        conn = sqlite3.connect(self._db_file())
        conn.execute("""CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY, name TEXT, type TEXT, aliases TEXT,
            first_seen TEXT, last_seen TEXT, mention_count INTEGER,
            source_ids TEXT, description TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY, source TEXT, target TEXT, relation TEXT,
            confidence REAL, first_seen TEXT, last_seen TEXT,
            evidence TEXT, source_ids TEXT)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source)")
        return conn

    def _index_entity(self, entity: "Entity"):
        self.entities[entity.id] = entity
        self._entity_name_map[entity.name.lower()] = entity.id
        for alias in entity.aliases:
            self._entity_name_map[alias.lower()] = entity.id

    def _load_state(self):
        # Prefer SQLite; if the DB is empty/absent but a legacy graph.json exists,
        # migrate it once.
        try:
            if self._db_file().exists():
                self._load_from_db()
                if self.entities:
                    return
            if self._state_file().exists():
                self._load_from_json()
                if self.entities:
                    logger.info("[KnowledgeGraph] Migrating legacy graph.json → SQLite")
                    self._save_state()  # writes the DB
        except Exception as e:
            logger.warning(f"[KnowledgeGraph] Failed to load state: {e}")

    def _load_from_db(self):
        conn = self._connect()
        try:
            for row in conn.execute("SELECT id,name,type,aliases,first_seen,last_seen,"
                                    "mention_count,source_ids,description FROM entities"):
                self._index_entity(Entity(
                    id=row[0], name=row[1], type=EntityType(row[2] or "unknown"),
                    aliases=json.loads(row[3] or "[]"),
                    first_seen=datetime.fromisoformat(row[4]),
                    last_seen=datetime.fromisoformat(row[5]),
                    mention_count=row[6] or 1,
                    source_ids=json.loads(row[7] or "[]"),
                    description=row[8] or "",
                ))
            for row in conn.execute("SELECT id,source,target,relation,confidence,"
                                    "first_seen,last_seen,evidence,source_ids FROM relationships"):
                rel = Relationship(
                    id=row[0], source=row[1], target=row[2],
                    relation=RelationType(row[3] or "related_to"),
                    confidence=row[4] if row[4] is not None else 1.0,
                    first_seen=datetime.fromisoformat(row[5]) if row[5] else datetime.utcnow(),
                    last_seen=datetime.fromisoformat(row[6]) if row[6] else datetime.utcnow(),
                    evidence=json.loads(row[7] or "[]"),
                    source_ids=json.loads(row[8] or "[]"),
                )
                self.relationships[rel.id] = rel
                self._adj[rel.source].append((rel.target, rel.relation, rel.id))
            logger.info(f"[KnowledgeGraph] Loaded {len(self.entities)} entities, "
                        f"{len(self.relationships)} relationships from SQLite")
        finally:
            conn.close()

    def _load_from_json(self):
        data = json.loads(self._state_file().read_text(encoding="utf-8"))
        for e in data.get("entities", []):
            self._index_entity(Entity(
                id=e["id"], name=e["name"], type=EntityType(e.get("type", "unknown")),
                aliases=e.get("aliases", []),
                first_seen=datetime.fromisoformat(e["first_seen"]),
                last_seen=datetime.fromisoformat(e["last_seen"]),
                mention_count=e.get("mention_count", 1),
                source_ids=e.get("source_ids", []),
                description=e.get("description", ""),
            ))
        for r in data.get("relationships", []):
            rel = Relationship(
                id=r["id"], source=r["source"], target=r["target"],
                relation=RelationType(r.get("relation", "related_to")),
                confidence=r.get("confidence", 1.0),
                first_seen=datetime.fromisoformat(r["first_seen"]) if r.get("first_seen") else datetime.utcnow(),
                last_seen=datetime.fromisoformat(r["last_seen"]) if r.get("last_seen") else datetime.utcnow(),
                evidence=r.get("evidence", []),
                source_ids=r.get("source_ids", []),
            )
            self.relationships[rel.id] = rel
            self._adj[rel.source].append((rel.target, rel.relation, rel.id))

    def _save_state(self):
        # Write SQLite (source of truth) + a JSON backup snapshot.
        try:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM entities")
                conn.execute("DELETE FROM relationships")
                conn.executemany(
                    "INSERT OR REPLACE INTO entities VALUES (?,?,?,?,?,?,?,?,?)",
                    [(e.id, e.name, e.type.value, json.dumps(e.aliases),
                      e.first_seen.isoformat(), e.last_seen.isoformat(),
                      e.mention_count, json.dumps(e.source_ids), e.description)
                     for e in self.entities.values()])
                conn.executemany(
                    "INSERT OR REPLACE INTO relationships VALUES (?,?,?,?,?,?,?,?,?)",
                    [(r.id, r.source, r.target, r.relation.value, r.confidence,
                      r.first_seen.isoformat(), r.last_seen.isoformat(),
                      json.dumps(r.evidence), json.dumps(r.source_ids))
                     for r in self.relationships.values()])
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"[KnowledgeGraph] Failed to save SQLite state: {e}")

        # JSON backup (includes the full timestamps the legacy to_dict() omitted).
        try:
            data = {
                "saved_at": datetime.utcnow().isoformat(),
                "entities": [{**e.to_dict(), "source_ids": e.source_ids}
                             for e in self.entities.values()],
                "relationships": [{**r.to_dict(),
                                   "first_seen": r.first_seen.isoformat(),
                                   "last_seen": r.last_seen.isoformat(),
                                   "source_ids": r.source_ids}
                                  for r in self.relationships.values()],
            }
            self._state_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[KnowledgeGraph] Failed to write JSON backup: {e}")

    # ─── Event System ────────────────────────────────────────────────────────


    # ─── Entity Extraction ───────────────────────────────────────────────────

    def ingest(self, text: str, source_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract entities and relationships from text, add to graph."""
        extracted = self._extract_entities(text)
        relationships = self._extract_relationships(text, extracted)
        
        added_entities = []
        added_rels = []
        
        for ent_data in extracted:
            entity = self._add_or_update_entity(ent_data, source_id)
            added_entities.append(entity.to_dict())
        
        for rel_data in relationships:
            rel = self._add_or_update_relationship(rel_data, source_id)
            if rel:
                added_rels.append(rel.to_dict())
        
        if added_entities or added_rels:
            self._save_state()
            self._publish("knowledge_added", {
                "entities_added": len(added_entities),
                "relationships_added": len(added_rels),
            })
        
        return {
            "entities": added_entities,
            "relationships": added_rels,
        }

    def set_extractor(self, extractor) -> None:
        """Inject an LLM extractor (core.entity_extractor.LLMEntityExtractor).
        When set, `ingest_llm` uses it; the regex `ingest` stays as the fallback."""
        self.extractor = extractor

    _NAME_VARIANTS = {
        "i": "Aryan", "me": "Aryan", "my": "Aryan", "mine": "Aryan",
        "myself": "Aryan", "aryan": "Aryan", "hey aryan": "Aryan",
    }

    def _canonical_name(self, name: str) -> str:
        """Light canonicalisation safety-net (the LLM already canonicalises)."""
        n = " ".join(str(name or "").split()).strip()
        return self._NAME_VARIANTS.get(n.lower(), n)

    async def ingest_llm(self, text: str, source_id: Optional[str] = None) -> Dict[str, Any]:
        """LLM-based ingest: clean, typed, canonical entities + a one-line fact each.
        Falls back to the regex `ingest` if no extractor is set or extraction fails."""
        if not self.extractor:
            return self.ingest(text, source_id)
        try:
            result = await self.extractor.extract(text)
        except Exception as e:
            logger.warning(f"[KnowledgeGraph] LLM extract failed, falling back: {e}")
            return self.ingest(text, source_id)

        ents = result.get("entities", [])
        rels = result.get("relationships", [])
        if not ents:
            return self.ingest(text, source_id)   # nothing found → try the heuristic path

        # Contradiction handling: if the user is retracting ("I no longer use X"),
        # weaken the matching beliefs instead of asserting new ones.
        if self.looks_like_retraction(text) and rels:
            retracted = []
            async with self._ingest_lock:
                for r in rels:
                    res = self.retract(self._canonical_name(r.get("source_name", "")),
                                       self._canonical_name(r.get("target_name", "")),
                                       relation=None)
                    if res.get("updated") or res.get("removed"):
                        retracted.append(res)
            if retracted:
                return {"entities": [], "relationships": [], "method": "llm",
                        "retracted": retracted}
            # nothing matched to retract → fall through and ingest normally

        added_entities, added_rels = [], []
        async with self._ingest_lock:   # serialize graph mutation + state save
            for e in ents:
                try:
                    etype = EntityType(e.get("type", "concept"))
                except Exception:
                    etype = EntityType.CONCEPT
                entity = self._add_or_update_entity({
                    "name": self._canonical_name(e.get("name", "")),
                    "type": etype,
                    "aliases": e.get("aliases", []),
                    "description": e.get("description", ""),
                }, source_id)
                added_entities.append(entity.to_dict())

            for r in rels:
                try:
                    rtype = RelationType(r.get("relation", "related_to"))
                except Exception:
                    rtype = RelationType.RELATED_TO
                rel = self._add_or_update_relationship({
                    "source_name": self._canonical_name(r.get("source_name", "")),
                    "target_name": self._canonical_name(r.get("target_name", "")),
                    "relation": rtype,
                    "evidence": r.get("evidence", ""),
                }, source_id)
                if rel:
                    added_rels.append(rel.to_dict())

            if added_entities or added_rels:
                self._save_state()
                self._publish("knowledge_added", {
                    "entities_added": len(added_entities),
                    "relationships_added": len(added_rels),
                })
        return {"entities": added_entities, "relationships": added_rels, "method": "llm"}

    # Junk the legacy capitalized-word regex produced: sentence-openers,
    # pronouns, conjunctions, fillers. Pruned regardless of links.
    _NOISE_NAMES = {
        "also", "right", "well", "okay", "ok", "yes", "no", "yeah", "nope",
        "the", "this", "that", "these", "those", "there", "here", "then",
        "also", "but", "and", "or", "so", "because", "however", "thus",
        "hey", "hi", "hello", "oh", "ah", "um", "uh", "let", "lets", "let's",
        "what", "when", "where", "why", "who", "which", "how", "whose",
        "i", "me", "my", "you", "your", "we", "us", "our", "they", "them",
        "he", "she", "it", "his", "her", "its", "thing", "things", "stuff",
        "next", "steps", "step", "first", "second", "third", "last", "go",
        "get", "got", "make", "made", "do", "does", "did", "now", "just",
        "really", "very", "much", "more", "most", "some", "any", "all",
        "unknown", "none", "etc", "thanks", "thank", "please", "sure",
    }

    def prune_noise(self) -> Dict[str, Any]:
        """Remove obvious non-entities the legacy regex left behind. Conservative:
        drops curated stop-names and sub-3-char fragments. Returns what was cut."""
        # Entities that have at least one relationship are structurally meaningful —
        # protect them from the length/char heuristics (acronym hubs like "AI"),
        # but still drop them if they're an outright stop-name.
        linked = set()
        for r in self.relationships.values():
            linked.add(r.source); linked.add(r.target)

        victims = []
        for eid, e in list(self.entities.items()):
            low = (e.name or "").strip().lower()
            if not low:
                victims.append(e.name)
                continue
            if low in self._NOISE_NAMES:
                victims.append(e.name)
            elif eid not in linked and (len(low) < 3 or not any(c.isalpha() for c in low)):
                victims.append(e.name)
        for name in victims:
            try:
                self.forget(name)
            except Exception:
                pass
        return {"pruned": len(victims), "names": victims[:60],
                "remaining": len(self.entities)}

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text using keyword matching."""
        text_lower = text.lower()
        found = []
        seen = set()
        
        # Check technology keywords
        for tech in _TECH_KEYWORDS:
            if tech in text_lower and tech not in seen:
                seen.add(tech)
                found.append({
                    "name": tech.title() if tech != "cpp" else "C++",
                    "type": EntityType.TECHNOLOGY,
                    "aliases": [tech],
                })
        
        # Check topic keywords
        for topic in _TOPIC_PATTERNS:
            if topic in text_lower and topic not in seen:
                seen.add(topic)
                found.append({
                    "name": topic.title(),
                    "type": EntityType.TOPIC,
                    "aliases": [topic],
                })
        
        # Check person indicators
        for indicator in _PERSON_INDICATORS:
            if indicator in text_lower.split() and indicator not in seen:
                seen.add(indicator)
                found.append({
                    "name": "Aryan" if indicator in ("aryan", "i", "me", "my", "mine", "myself") else indicator.title(),
                    "type": EntityType.PERSON,
                    "aliases": [indicator],
                })

        # Check CVEs
        cve_matches = re.findall(r'CVE-\d{4}-\d{4,7}', text, re.IGNORECASE)
        for cve in cve_matches:
            cve_upper = cve.upper()
            if cve_upper.lower() not in seen:
                seen.add(cve_upper.lower())
                found.append({
                    "name": cve_upper,
                    "type": EntityType.VULNERABILITY,
                    "aliases": [cve_upper.lower()],
                })

        # Check frequencies
        for freq in _FREQ_KEYWORDS:
            if freq in text_lower and freq not in seen:
                seen.add(freq)
                found.append({
                    "name": freq.upper() if "hz" in freq else freq.title(),
                    "type": EntityType.RF_FREQUENCY,
                    "aliases": [freq],
                })

        # Check chips/hardware devices
        for chip in _CHIP_KEYWORDS:
            if chip in text_lower and chip not in seen:
                seen.add(chip)
                found.append({
                    "name": chip.title() if "pi" in chip or "cortex" in chip else chip.upper(),
                    "type": EntityType.HARDWARE_DEVICE,
                    "aliases": [chip],
                })

        # Check physics concepts
        for term in _PHYSICS_TERMS:
            if term in text_lower and term not in seen:
                seen.add(term)
                found.append({
                    "name": term.title(),
                    "type": EntityType.PHYSICS_CONCEPT,
                    "aliases": [term],
                })

        # Check protocol names
        for proto in _PROTOCOL_NAMES:
            if proto in text_lower and proto not in seen:
                seen.add(proto)
                found.append({
                    "name": proto.upper(),
                    "type": EntityType.PROTOCOL,
                    "aliases": [proto],
                })
        
        # Simple noun phrase extraction (capitalized sequences)
        # Match capitalized words that are likely proper nouns
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        for noun in proper_nouns:
            noun_lower = noun.lower()
            if noun_lower not in seen and len(noun) > 2:
                # Skip common words
                if noun_lower in ("the", "this", "that", "what", "when", "where", "how", "why", "who", "which", "would", "could", "should", "will", "shall", "may", "might", "can", "do", "does", "did", "have", "has", "had", "was", "were", "is", "am", "are", "been", "being", "be", "it", "its", "itself", "he", "him", "his", "himself", "she", "her", "hers", "herself", "they", "them", "their", "theirs", "themselves", "we", "us", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves"):
                    continue
                seen.add(noun_lower)
                found.append({
                    "name": noun,
                    "type": EntityType.CONCEPT,
                    "aliases": [noun_lower],
                })
        
        return found

    def _extract_relationships(self, text: str, entities: List[Dict]) -> List[Dict]:
        """Extract relationships between entities using pattern matching."""
        if len(entities) < 2:
            return []
        
        text_lower = text.lower()
        relationships = []
        entity_names = [e["name"].lower() for e in entities]
        
        for relation_type, patterns in _RELATION_PATTERNS:
            for pattern in patterns:
                if pattern in text_lower:
                    # Find which entities are connected by this pattern
                    idx = text_lower.find(pattern)
                    before = text_lower[max(0, idx-80):idx]
                    after = text_lower[idx+len(pattern):idx+80]
                    
                    # Try to match entities before and after
                    source = self._find_entity_in_text(before, entities)
                    target = self._find_entity_in_text(after, entities)
                    
                    if source and target and source != target:
                        relationships.append({
                            "source_name": source,
                            "target_name": target,
                            "relation": relation_type,
                            "evidence": text[idx:idx+len(pattern)+40],
                        })
        
        return relationships

    def _find_entity_in_text(self, text: str, entities: List[Dict]) -> Optional[str]:
        """Find the most prominent entity in a text snippet."""
        text_lower = text.lower()
        best_match = None
        best_len = 0
        
        for ent in entities:
            name = ent["name"].lower()
            if name in text_lower and len(name) > best_len:
                best_match = ent["name"]
                best_len = len(name)
        
        return best_match

    def _add_or_update_entity(self, ent_data: Dict, source_id: Optional[str]) -> Entity:
        """Add new entity or update existing one."""
        name = ent_data["name"]
        name_lower = name.lower()
        
        desc = (ent_data.get("description") or "").strip()

        # Check if entity exists
        if name_lower in self._entity_name_map:
            entity_id = self._entity_name_map[name_lower]
            entity = self.entities[entity_id]
            entity.last_seen = datetime.utcnow()
            entity.mention_count += 1
            if source_id and source_id not in entity.source_ids:
                entity.source_ids.append(source_id)
            # Prefer a non-empty / richer description; merge any new aliases.
            if desc and (not entity.description or len(desc) > len(entity.description)):
                entity.description = desc
            for alias in ent_data.get("aliases", []):
                al = str(alias).strip()
                if al and al.lower() not in self._entity_name_map:
                    entity.aliases.append(al)
                    self._entity_name_map[al.lower()] = entity_id
            return entity

        # Create new entity
        # Name-scoped, so this is already near-unique; the old
        # `int(time.time()*1000) % 10000` suffix wrapped every 10 seconds and
        # bought nothing the name didn't already provide.
        entity_id = f"ent_{name_lower.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        entity = Entity(
            id=entity_id,
            name=name,
            type=ent_data.get("type", EntityType.UNKNOWN),
            aliases=ent_data.get("aliases", []),
            description=desc,
        )
        if source_id:
            entity.source_ids.append(source_id)
        
        self.entities[entity_id] = entity
        self._entity_name_map[name_lower] = entity_id
        for alias in entity.aliases:
            self._entity_name_map[alias.lower()] = entity_id
        
        return entity

    def _add_or_update_relationship(self, rel_data: Dict, source_id: Optional[str]) -> Optional[Relationship]:
        """Add new relationship or strengthen existing one."""
        source_name = rel_data["source_name"]
        target_name = rel_data["target_name"]
        relation = rel_data["relation"]
        
        source_id_e = self._entity_name_map.get(source_name.lower())
        target_id_e = self._entity_name_map.get(target_name.lower())
        
        if not source_id_e or not target_id_e:
            return None
        
        # Check if relationship already exists
        for existing_target, existing_rel, existing_id in self._adj[source_id_e]:
            if existing_target == target_id_e and existing_rel == relation:
                rel = self.relationships[existing_id]
                rel.confidence = min(1.0, rel.confidence + 0.1)
                rel.last_seen = datetime.utcnow()
                if rel_data.get("evidence"):
                    rel.evidence.append(rel_data["evidence"][:100])
                    if len(rel.evidence) > 5:
                        rel.evidence = rel.evidence[-5:]
                return rel
        
        # Create new relationship.
        #
        # This used to be f"rel_{int(time.time()*1000)}". Extraction produces
        # several relationships per ingest() call, well within one millisecond,
        # so they all received the same id and each overwrote the last in
        # self.relationships — one ingest of five relationships persisted one.
        # uuid4 removes the collision entirely and stays stable across the
        # SQLite round-trip.
        rel_id = f"rel_{uuid.uuid4().hex[:16]}"
        rel = Relationship(
            id=rel_id,
            source=source_id_e,
            target=target_id_e,
            relation=relation,
            confidence=0.5,
            evidence=[rel_data.get("evidence", "")[:100]] if rel_data.get("evidence") else [],
        )
        if source_id:
            rel.source_ids.append(source_id)
        
        self.relationships[rel_id] = rel
        self._adj[source_id_e].append((target_id_e, relation, rel_id))
        
        return rel

    # ─── Decay & contradictions ──────────────────────────────────────────────

    # A fact's stored confidence is its strength at last reinforcement; its
    # CURRENT belief decays toward 0 as it goes unmentioned. Half-life = how many
    # days until an un-reinforced fact is worth half as much.
    DECAY_HALF_LIFE_DAYS = 45.0

    def effective_confidence(self, rel: "Relationship",
                             now: Optional[datetime] = None) -> float:
        """Recency-weighted belief: stored confidence × 2^(-age / half_life).

        Lets old, never-repeated facts fade while frequently-reinforced ones
        (whose last_seen keeps refreshing) stay strong — without mutating state.
        """
        now = now or datetime.utcnow()
        age_days = max(0.0, (now - rel.last_seen).total_seconds() / 86400.0)
        factor = 0.5 ** (age_days / self.DECAY_HALF_LIFE_DAYS)
        return round(rel.confidence * factor, 4)

    def decay_sweep(self, prune_below: float = 0.08) -> Dict[str, Any]:
        """Drop relationships whose *effective* (time-decayed) belief has fallen
        below `prune_below` — the graph forgetting what it stopped hearing about.
        Returns what was pruned. Entities are left intact (they may still be hubs)."""
        now = datetime.utcnow()
        dead = [rid for rid, r in self.relationships.items()
                if self.effective_confidence(r, now) < prune_below]
        for rid in dead:
            r = self.relationships.pop(rid, None)
            if r and r.source in self._adj:
                self._adj[r.source] = [e for e in self._adj[r.source] if e[2] != rid]
        if dead:
            self._save_state()
            self._publish("knowledge_decayed", {"relationships_pruned": len(dead)})
        return {"pruned": len(dead), "remaining": len(self.relationships)}

    # Patterns that signal the user is RETRACTING a fact, not asserting one.
    _NEGATION_CUES = (
        "no longer", "don't use", "dont use", "do not use", "stopped using",
        "not using", "quit", "gave up", "moved off", "switched away from",
        "no more", "don't like", "dont like", "not into", "hate", "abandoned",
    )

    def looks_like_retraction(self, text: str) -> bool:
        t = (text or "").lower()
        return any(cue in t for cue in self._NEGATION_CUES)

    def retract(self, source_name: str, target_name: str,
                relation: Optional[str] = None, amount: float = 0.5) -> Dict[str, Any]:
        """Weaken (or, if it collapses, remove) a contradicted belief.

        `amount` is how much confidence to subtract. A fact knocked to/below 0 is
        deleted outright. Optionally scope to a single `relation` value.
        """
        src_id = self._entity_name_map.get(source_name.lower())
        tgt_id = self._entity_name_map.get(target_name.lower())
        if not src_id or not tgt_id:
            return {"updated": 0, "removed": 0, "reason": "entity not found"}

        updated = removed = 0
        for target_id, rel_type, rel_id in list(self._adj.get(src_id, [])):
            if target_id != tgt_id:
                continue
            if relation and rel_type.value != relation:
                continue
            rel = self.relationships.get(rel_id)
            if not rel:
                continue
            rel.confidence -= amount
            rel.last_seen = datetime.utcnow()
            if rel.confidence <= 0.0:
                self.relationships.pop(rel_id, None)
                self._adj[src_id] = [e for e in self._adj[src_id] if e[2] != rel_id]
                removed += 1
            else:
                updated += 1
        if updated or removed:
            self._save_state()
            self._publish("knowledge_retracted",
                          {"source": source_name, "target": target_name,
                           "updated": updated, "removed": removed})
        return {"updated": updated, "removed": removed}

    # ─── Semantic retrieval ───────────────────────────────────────────────────

    def semantic_search(self, query: str, k: int = 8,
                        min_score: float = 0.30) -> List[Dict[str, Any]]:
        """Embedding-based entity lookup: find entities whose meaning matches the
        query, not just a substring. Reuses graph_enrich's MiniLM embedder + vector
        cache. Falls back to substring `search()` if embeddings are unavailable.

        Each hit carries a `score` (cosine sim). This is what the brain should call
        to pull a *relevant* slice of memory into context for a turn.
        """
        ents = self.get_all_entities()
        if not ents or not query.strip():
            return []
        try:
            import numpy as np
            from core import graph_enrich as ge

            ge._load_cache()
            docs, vecs, missing, missing_idx = [], [], [], []
            for i, e in enumerate(ents):
                doc = ge._doc_for(e, (e.get("context") or [""])[0])
                docs.append(doc)
                v = ge._VEC_CACHE.get(ge._hash(doc))
                vecs.append(v)
                if v is None:
                    missing.append(doc)
                    missing_idx.append(i)
            if missing:
                emb = ge._get_model().encode(missing, normalize_embeddings=True)
                for j, i in enumerate(missing_idx):
                    vecs[i] = np.asarray(emb[j], dtype="float32")
            qv = np.asarray(
                ge._get_model().encode([query], normalize_embeddings=True)[0],
                dtype="float32")
            mat = np.vstack(vecs)
            sims = mat @ qv
            order = np.argsort(-sims)[:k]
            out = []
            for i in order:
                score = float(sims[int(i)])
                if score < min_score:
                    continue
                hit = dict(ents[int(i)])
                hit["score"] = round(score, 3)
                out.append(hit)
            return out
        except Exception as e:  # noqa: BLE001 — fall back, never break retrieval
            logger.warning(f"[KnowledgeGraph] semantic_search fell back to substring: {e}")
            return self.search(query)

    # ─── Queries ───────────────────────────────────────────────────────────────

    def get_entity(self, name: str) -> Optional[Dict]:
        """Get entity by name."""
        entity_id = self._entity_name_map.get(name.lower())
        if entity_id:
            return self.entities[entity_id].to_dict()
        return None

    def get_neighbors(self, name: str) -> List[Dict]:
        """Get all entities directly connected to the given entity."""
        entity_id = self._entity_name_map.get(name.lower())
        if not entity_id:
            return []
        
        results = []
        for target_id, relation, rel_id in self._adj[entity_id]:
            target = self.entities.get(target_id)
            rel = self.relationships.get(rel_id)
            if target and rel:
                results.append({
                    "entity": target.to_dict(),
                    "relation": relation.value,
                    "confidence": rel.confidence,
                })
        return results

    def find_paths(self, source_name: str, target_name: str, max_depth: int = 3,
                   max_paths: int = 25) -> List[List[Dict]]:
        """Find all simple paths between two entities, up to `max_depth` hops.

        Uses per-path visited bookkeeping (not a single global set) so genuinely
        distinct routes are all discovered — the old shared-visited BFS marked
        nodes on enqueue and so returned at most one path per node.
        """
        source_id = self._entity_name_map.get(source_name.lower())
        target_id = self._entity_name_map.get(target_name.lower())

        if not source_id or not target_id or source_id == target_id:
            return []

        paths: List[List[Dict]] = []
        # (current, path_so_far, set_of_nodes_on_this_path)
        queue = deque([(source_id, [source_id], {source_id})])

        while queue and len(paths) < max_paths:
            current, path, on_path = queue.popleft()
            if len(path) > max_depth + 1:
                continue

            if current == target_id and len(path) > 1:
                readable = []
                for i in range(len(path) - 1):
                    src, tgt = path[i], path[i + 1]
                    relation_str = "related_to"
                    for t, rel, _ in self._adj[src]:
                        if t == tgt:
                            relation_str = rel.value
                            break
                    readable.append({
                        "from": self.entities[src].name,
                        "to": self.entities[tgt].name,
                        "relation": relation_str,
                    })
                paths.append(readable)
                continue

            for next_id, _, _ in self._adj[current]:
                if next_id not in on_path:   # no cycles within a single path
                    queue.append((next_id, path + [next_id], on_path | {next_id}))

        return paths

    def query_relationship(self, name: str, relation: Optional[str] = None) -> List[Dict]:
        """Query all relationships for an entity, optionally filtered by type."""
        entity_id = self._entity_name_map.get(name.lower())
        if not entity_id:
            return []
        
        results = []
        for target_id, rel_type, rel_id in self._adj[entity_id]:
            if relation and rel_type.value != relation:
                continue
            target = self.entities.get(target_id)
            rel = self.relationships.get(rel_id)
            if target and rel:
                results.append({
                    "target": target.to_dict(),
                    "relation": rel_type.value,
                    "confidence": rel.confidence,
                })
        return results

    def search(self, query: str) -> List[Dict]:
        """Search entities by name or alias."""
        query_lower = query.lower()
        results = []
        
        for entity in self.entities.values():
            if (query_lower in entity.name.lower() or
                any(query_lower in alias.lower() for alias in entity.aliases)):
                results.append(entity.to_dict())
        
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Graph statistics."""
        type_counts = Counter(e.type.value for e in self.entities.values())
        rel_counts = Counter(r.relation.value for r in self.relationships.values())
        
        return {
            "entities": len(self.entities),
            "relationships": len(self.relationships),
            "entity_types": dict(type_counts),
            "relation_types": dict(rel_counts),
            "most_connected": self._get_most_connected(5),
        }

    def _get_most_connected(self, n: int) -> List[Dict]:
        """Get most connected entities."""
        connections = [(eid, len(self._adj[eid])) for eid in self._adj]
        connections.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for eid, count in connections[:n]:
            entity = self.entities.get(eid)
            if entity:
                results.append({"name": entity.name, "connections": count})
        return results

    def get_recent_entities(self, limit: int = 10) -> List[Dict]:
        """Get recently seen entities."""
        sorted_entities = sorted(
            self.entities.values(),
            key=lambda e: e.last_seen,
            reverse=True
        )
        return [e.to_dict() for e in sorted_entities[:limit]]

    def get_all_entities(self) -> List[Dict]:
        """Get all entities."""
        return [e.to_dict() for e in self.entities.values()]

    def forget(self, name: str) -> bool:
        """Delete an entity by name along with every relationship touching it.

        Powers the user-facing Memory Vault: lets Aryan remove anything the
        system has learned. Returns True if something was deleted.
        """
        entity_id = self._entity_name_map.get(name.lower())
        if not entity_id:
            return False
        entity = self.entities.pop(entity_id, None)

        # Drop name + alias lookups pointing at this entity
        for key in [k for k, v in self._entity_name_map.items() if v == entity_id]:
            self._entity_name_map.pop(key, None)

        # Remove every relationship that references the entity (either end)
        dead_rels = [
            rid for rid, r in self.relationships.items()
            if r.source == entity_id or r.target == entity_id
        ]
        for rid in dead_rels:
            self.relationships.pop(rid, None)

        # Rebuild adjacency for any node that linked to/from the removed entity
        if hasattr(self, "_adj"):
            self._adj.pop(entity_id, None)
            for src, edges in self._adj.items():
                self._adj[src] = [e for e in edges if e[0] != entity_id]

        self._save_state()
        self._publish("entity_forgotten", {"name": name, "relationships_removed": len(dead_rels)})
        return entity is not None

    def get_all_relationships(self, limit: int = 50) -> List[Dict]:
        """Get all relationships."""
        return [r.to_dict() for r in list(self.relationships.values())[:limit]]
