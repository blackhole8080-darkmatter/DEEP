"""
core/interactive_response.py

Interactive Response System — Claude-style options, alternatives, and clarification questions.

Enables DEEP to:
- Present multiple options/alternatives to the user
- Ask clarifying questions before proceeding
- Provide structured choices with pros/cons
- Handle user selection and continue workflow
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Enums & Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class InteractionType(Enum):
    """Type of interactive response"""
    OPTIONS = "options"              # Multiple choice options
    ALTERNATIVES = "alternatives"    # Alternative approaches
    CLARIFICATION = "clarification"  # Questions needing answers
    CONFIRMATION = "confirmation"    # Yes/no confirmation
    TRADEOFFS = "tradeoffs"         # Pros/cons comparison


@dataclass
class Option:
    """A single option in an interactive response"""
    id: str
    label: str
    description: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    recommended: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "pros": self.pros,
            "cons": self.cons,
            "recommended": self.recommended,
            "metadata": self.metadata,
        }


@dataclass
class ClarificationQuestion:
    """A question that needs user input"""
    id: str
    question: str
    context: str = ""
    required: bool = True
    default_value: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "question": self.question,
            "context": self.context,
            "required": self.required,
            "default_value": self.default_value,
            "suggestions": self.suggestions,
        }


@dataclass
class InteractiveResponse:
    """
    An interactive response that requires user input before proceeding.
    
    Similar to Claude's interactive responses with options and alternatives.
    """
    id: str
    type: InteractionType
    message: str
    options: List[Option] = field(default_factory=list)
    questions: List[ClarificationQuestion] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "message": self.message,
            "options": [opt.to_dict() for opt in self.options],
            "questions": [q.to_dict() for q in self.questions],
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Response Builder
# ═══════════════════════════════════════════════════════════════════════════════

class InteractiveResponseBuilder:
    """
    Builder for creating interactive responses.
    
    Usage:
        builder = InteractiveResponseBuilder()
        response = builder.create_options(
            message="How would you like to implement authentication?",
            options=[
                {"label": "JWT", "description": "Stateless tokens", "pros": [...], "cons": [...]},
                {"label": "Sessions", "description": "Server-side state", "pros": [...], "cons": [...]}
            ]
        )
    """

    def __init__(self):
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"interactive_{self._counter}_{int(datetime.utcnow().timestamp())}"

    def create_options(
        self,
        message: str,
        options: List[Dict[str, Any]],
        context: Optional[Dict] = None,
    ) -> InteractiveResponse:
        """
        Create an options-based interactive response.
        
        Args:
            message: Main message/question
            options: List of option dicts with label, description, pros, cons
            context: Additional context for processing user selection
        """
        option_objects = []
        for i, opt in enumerate(options):
            option_objects.append(
                Option(
                    id=f"opt_{i+1}",
                    label=opt.get("label", f"Option {i+1}"),
                    description=opt.get("description", ""),
                    pros=opt.get("pros", []),
                    cons=opt.get("cons", []),
                    recommended=opt.get("recommended", False),
                    metadata=opt.get("metadata", {}),
                )
            )

        return InteractiveResponse(
            id=self._next_id(),
            type=InteractionType.OPTIONS,
            message=message,
            options=option_objects,
            context=context or {},
        )

    def create_alternatives(
        self,
        message: str,
        alternatives: List[Dict[str, Any]],
        context: Optional[Dict] = None,
    ) -> InteractiveResponse:
        """
        Create an alternatives-based response (different approaches to same goal).
        """
        return self.create_options(message, alternatives, context)

    def create_clarification(
        self,
        message: str,
        questions: List[Dict[str, Any]],
        context: Optional[Dict] = None,
    ) -> InteractiveResponse:
        """
        Create a clarification request with specific questions.
        
        Args:
            message: Context message
            questions: List of question dicts with question, context, required, suggestions
            context: Additional context
        """
        question_objects = []
        for i, q in enumerate(questions):
            question_objects.append(
                ClarificationQuestion(
                    id=f"q_{i+1}",
                    question=q.get("question", ""),
                    context=q.get("context", ""),
                    required=q.get("required", True),
                    default_value=q.get("default_value"),
                    suggestions=q.get("suggestions", []),
                )
            )

        return InteractiveResponse(
            id=self._next_id(),
            type=InteractionType.CLARIFICATION,
            message=message,
            questions=question_objects,
            context=context or {},
        )

    def create_confirmation(
        self,
        message: str,
        action: str,
        context: Optional[Dict] = None,
    ) -> InteractiveResponse:
        """
        Create a yes/no confirmation request.
        """
        return InteractiveResponse(
            id=self._next_id(),
            type=InteractionType.CONFIRMATION,
            message=message,
            options=[
                Option(id="yes", label="Yes", description=f"Proceed with {action}"),
                Option(id="no", label="No", description="Cancel this action"),
            ],
            context=context or {"action": action},
        )

    def create_tradeoffs(
        self,
        message: str,
        options: List[Dict[str, Any]],
        context: Optional[Dict] = None,
    ) -> InteractiveResponse:
        """
        Create a tradeoffs comparison (pros/cons emphasis).
        """
        response = self.create_options(message, options, context)
        response.type = InteractionType.TRADEOFFS
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Response Manager
# ═══════════════════════════════════════════════════════════════════════════════

class InteractiveResponseManager:
    """
    Manages pending interactive responses and user selections.
    
    Tracks active interactive responses and processes user selections.
    """

    def __init__(self):
        self._pending: Dict[str, InteractiveResponse] = {}
        self._builder = InteractiveResponseBuilder()
        logger.info("[InteractiveResponseManager] Initialized")

    def create_and_store(
        self,
        response_type: str,
        message: str,
        data: List[Dict],
        context: Optional[Dict] = None,
    ) -> InteractiveResponse:
        """
        Create an interactive response and store it as pending.
        
        Args:
            response_type: "options", "alternatives", "clarification", "confirmation", "tradeoffs"
            message: Main message
            data: Options or questions data
            context: Additional context
        """
        if response_type == "options":
            response = self._builder.create_options(message, data, context)
        elif response_type == "alternatives":
            response = self._builder.create_alternatives(message, data, context)
        elif response_type == "clarification":
            response = self._builder.create_clarification(message, data, context)
        elif response_type == "confirmation":
            # data should have "action" key
            action = data[0].get("action", "this action") if data else "this action"
            response = self._builder.create_confirmation(message, action, context)
        elif response_type == "tradeoffs":
            response = self._builder.create_tradeoffs(message, data, context)
        else:
            raise ValueError(f"Unknown response type: {response_type}")

        self._pending[response.id] = response
        logger.info(f"[InteractiveResponseManager] Created {response_type} response: {response.id}")
        return response

    def get_pending(self, response_id: str) -> Optional[InteractiveResponse]:
        """Get a pending interactive response by ID."""
        return self._pending.get(response_id)

    def process_selection(
        self,
        response_id: str,
        selection: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process user selection for an interactive response.
        
        Args:
            response_id: ID of the interactive response
            selection: User's selection (e.g., {"option_id": "opt_1"} or {"answers": {...}})
        
        Returns:
            Dict with processed selection and context
        """
        response = self._pending.get(response_id)
        if not response:
            return {"error": f"No pending response with ID: {response_id}"}

        result = {
            "response_id": response_id,
            "type": response.type.value,
            "selection": selection,
            "context": response.context,
        }

        # Process based on type
        if response.type in [InteractionType.OPTIONS, InteractionType.ALTERNATIVES, InteractionType.TRADEOFFS]:
            option_id = selection.get("option_id")
            selected_option = next((opt for opt in response.options if opt.id == option_id), None)
            if selected_option:
                result["selected_option"] = selected_option.to_dict()
            else:
                result["error"] = f"Invalid option ID: {option_id}"

        elif response.type == InteractionType.CLARIFICATION:
            answers = selection.get("answers", {})
            result["answers"] = answers
            # Validate required questions
            missing = [q.id for q in response.questions if q.required and q.id not in answers]
            if missing:
                result["error"] = f"Missing required answers: {missing}"

        elif response.type == InteractionType.CONFIRMATION:
            confirmed = selection.get("confirmed", False)
            result["confirmed"] = confirmed

        # Remove from pending
        self._pending.pop(response_id, None)
        logger.info(f"[InteractiveResponseManager] Processed selection for: {response_id}")

        return result

    def list_pending(self) -> List[Dict]:
        """List all pending interactive responses."""
        return [r.to_dict() for r in self._pending.values()]

    def clear_expired(self):
        """Remove expired interactive responses."""
        now = datetime.utcnow()
        expired = [
            rid for rid, resp in self._pending.items()
            if resp.expires_at and resp.expires_at < now
        ]
        for rid in expired:
            self._pending.pop(rid, None)
            logger.info(f"[InteractiveResponseManager] Cleared expired response: {rid}")


# ═══════════════════════════════════════════════════════════════════════════════
# Global instance
# ═══════════════════════════════════════════════════════════════════════════════

interactive_manager = InteractiveResponseManager()
