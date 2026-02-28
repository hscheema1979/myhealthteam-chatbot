"""
Intent Parser for Chatbot

Classifies user messages into intents and extracts entities.

Incorporates patterns from Gemini-CLI-UI:
- Regex-based pattern matching with confidence scoring
- Entity extraction from natural language
- Support for slash commands and conversational input
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List


class Intent(Enum):
    """Intent types for chatbot commands"""
    QUERY_STATS = "query_stats"
    QUERY_PATIENTS = "query_patients"
    QUERY_TASKS = "query_tasks"
    QUERY_WORKFLOWS = "query_workflows"
    ACTION_ADD_TASK = "action_add_task"
    ACTION_UPDATE_PATIENT = "action_update_patient"
    ACTION_CORRECT_ENTRY = "action_correct_entry"
    ACTION_ADVANCE_WORKFLOW = "action_advance_workflow"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ParseResult:
    """Result of intent parsing"""
    intent: Intent
    entities: Dict[str, Any]
    confidence: float
    raw_message: str
    suggested_response: Optional[str] = None


class IntentParser:
    """Parser for classifying user intents and extracting entities"""

    # Pattern definitions for intent classification
    # Ordered by specificity (more specific patterns first)
    PATTERNS = {
        # Query intents
        Intent.QUERY_STATS: [
            (r"^/stats$", 0.98),  # Slash command - highest confidence
            (r"how many (patients|tasks|workflows)", 0.85),
            (r"show me (my )?(stats|performance|metrics)", 0.85),
            (r"what('s| is)? my (patient|task|billing|performance)", 0.80),
            (r"(my )?(stats|metrics|performance)", 0.75),
        ],
        Intent.QUERY_PATIENTS: [
            (r"^/patients( active)?$", 0.98),
            (r"show me (my )?patients", 0.85),
            (r"list (my )?patients", 0.85),
            (r"who are (my )?patients", 0.80),
            (r"(my )?patients( list)?", 0.75),
        ],
        Intent.QUERY_TASKS: [
            (r"^/tasks( pending)?$", 0.98),
            (r"show me (my )?(pending )?tasks", 0.85),
            (r"what (tasks )?do i have (pending )?", 0.80),
            (r"(my )?(pending )?tasks", 0.75),
            (r"(my )?todo", 0.70),
        ],
        Intent.QUERY_WORKFLOWS: [
            (r"^/workflows( pending)?$", 0.98),
            (r"show me (my )?workflows", 0.85),
            (r"(my )?(pending )?workflows", 0.75),
        ],
        # Action intents
        Intent.ACTION_ADD_TASK: [
            (r"add (a )?(new )?((?:\w+\s+){0,3})?(task|visit)", 0.80),  # More flexible
            (r"log (a )?(visit|task|activity)", 0.85),
            (r"record (a )?visit", 0.85),
            (r"create (a )?(task|visit)", 0.80),
        ],
        Intent.ACTION_UPDATE_PATIENT: [
            (r"update (patient|info)", 0.85),
            (r"change (patient )?(status|info)", 0.85),
            (r"modify (patient|info)", 0.80),
            (r"(set|mark) patient (status )?to", 0.80),
        ],
        Intent.ACTION_CORRECT_ENTRY: [
            (r"change that", 0.85),
            (r"fix (that|it)", 0.85),
            (r"correct (that|the)? (last )?(entry|task)", 0.80),
            (r"update (that|the)? (last )?(entry|task)", 0.75),
        ],
        Intent.ACTION_ADVANCE_WORKFLOW: [
            (r"(complete|finish|done) (workflow|step)", 0.85),
            (r"advance (workflow|step)", 0.85),
            (r"next step", 0.80),
        ],
        # Help
        Intent.HELP: [
            (r"^/help$", 0.98),
            (r"^help$", 0.95),
            (r"how (do|can) i", 0.75),
            (r"what can (you|i)", 0.70),
        ],
    }

    # Entity extraction patterns
    ENTITY_PATTERNS = {
        # Duration: "30 min", "30 minutes", "30min"
        "duration": [
            r"(\d+)\s*(min|minute|minutes|m)",
            r"(\d+)\s*(hour|hours|h)\s*(?:and)?\s*(\d+)\s*(min|minute|minutes|m)?",
        ],
        # Service type
        "service_type": [
            r"\b(PCP|Primary Care Physician|Follow Up|Acute|TCM|Home Visit|Telehealth)\b",
        ],
        # Status
        "status": [
            r"\b(active|inactive|discharged|pending|complete)\b",
        ],
        # Time range
        "time_range": [
            r"\b(today|this week|this month|this year|yesterday|last week|last month)\b",
        ],
        # Scope - check anywhere in message
        "scope": [
            r"\b(my|me|I)\b",  # Include "I" as self-reference
            r"\b(our|team)\b",
        ],
        # Patient name (after "for", "with", "patient")
        "patient_name": [
            r"(?:for|with|patient)\s+([A-Z][a-z]+)(?:\s+[A-Z][a-z]+)?",
        ],
        # Field name for updates
        "field": [
            r"\b(status|goc|code status|facility)\b",
        ],
        # Confirmation keywords
        "confirmation": [
            r"\b(yes|yeah|yep|confirm|ok|okay|proceed|do it|go ahead)\b",
        ],
        # Cancellation keywords
        "cancellation": [
            r"\b(no|nope|cancel|stop|never mind|forget it|abort)\b",
        ],
    }

    def __init__(self):
        """Initialize the intent parser"""
        # Compile patterns for performance
        self._compiled_patterns: Dict[Intent, List[tuple]] = {}
        for intent, pattern_list in self.PATTERNS.items():
            compiled = [(re.compile(pattern, re.IGNORECASE), conf) for pattern, conf in pattern_list]
            self._compiled_patterns[intent] = compiled

        # Compile entity patterns
        self._compiled_entity_patterns: Dict[str, List[re.Pattern]] = {}
        for entity_name, pattern_list in self.ENTITY_PATTERNS.items():
            self._compiled_entity_patterns[entity_name] = [
                re.compile(pattern, re.IGNORECASE) for pattern in pattern_list
            ]

    def parse(self, message: str) -> ParseResult:
        """
        Parse user message to extract intent and entities

        Args:
            message: User's input message

        Returns:
            ParseResult with intent, entities, and confidence score
        """
        message = message.strip()

        if not message:
            return ParseResult(
                intent=Intent.UNKNOWN,
                entities={},
                confidence=0.0,
                raw_message=message,
                suggested_response="I didn't receive a message. How can I help you?"
            )

        # Check each intent pattern
        best_match = None
        best_confidence = 0.0

        for intent, patterns in self._compiled_patterns.items():
            for pattern, base_confidence in patterns:
                if pattern.search(message):
                    # Calculate confidence based on match specificity
                    confidence = self._calculate_confidence(message, intent, base_confidence)

                    if confidence > best_confidence:
                        best_match = intent
                        best_confidence = confidence

        # Extract entities
        entities = self._extract_entities(message)

        # Determine response suggestion
        suggested_response = self._get_suggested_response(best_match or Intent.UNKNOWN, entities)

        return ParseResult(
            intent=best_match or Intent.UNKNOWN,
            entities=entities,
            confidence=best_confidence,
            raw_message=message,
            suggested_response=suggested_response
        )

    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract entities from message using regex patterns"""
        entities: Dict[str, Any] = {}

        for entity_name, patterns in self._compiled_entity_patterns.items():
            for pattern in patterns:
                match = pattern.search(message)
                if match:
                    # Extract the captured value
                    if entity_name == "duration":
                        # Check if it's the "hours and minutes" pattern (has multiple groups)
                        groups = match.groups()
                        if len(groups) >= 3 and groups[1] and groups[2]:
                            # Pattern: (\d+)\s*(hour|hours|h)\s*(?:and)?\s*(\d+)\s*(min|minute|minutes|m)?
                            hours = int(groups[0])
                            minutes = int(groups[2]) if groups[2] else 0
                            entities[entity_name] = hours * 60 + minutes
                        else:
                            # Simple pattern: just the number
                            entities[entity_name] = int(groups[0])
                    elif entity_name == "confirmation":
                        entities[entity_name] = True
                    elif entity_name == "cancellation":
                        entities[entity_name] = False
                    elif entity_name == "scope":
                        matched_text = match.group(0).lower()
                        if "my" in matched_text or "me" in matched_text or "i" in matched_text:
                            entities[entity_name] = "self"
                        elif "team" in matched_text or "our" in matched_text:
                            entities[entity_name] = "team"
                        else:
                            entities[entity_name] = matched_text
                    else:
                        # Extract the last captured group
                        if match.lastindex:
                            value = match.group(match.lastindex)
                            # Normalize certain values
                            if entity_name == "status":
                                value = value.title()
                            elif entity_name == "time_range":
                                value = value.lower().replace(" ", "_")
                            entities[entity_name] = value

                    # Only store the first match for most entities
                    if entity_name not in entities:
                        entities[entity_name] = value if match.lastindex else match.group(0)

        return entities

    def _calculate_confidence(self, message: str, intent: Intent, base_confidence: float) -> float:
        """
        Calculate confidence score for intent match

        Higher confidence for:
        - Exact slash commands
        - More specific patterns
        - Complete sentences
        """
        # Slash commands get highest confidence
        if message.startswith("/"):
            return min(base_confidence + 0.05, 1.0)

        # Action intents require more specificity
        if intent.name.startswith("ACTION_"):
            # Check for complete sentence structure
            if message[0].isupper() and message[-1] in ".!?":
                return min(base_confidence + 0.05, 1.0)

        return base_confidence

    def _get_suggested_response(self, intent: Intent, entities: Dict[str, Any]) -> Optional[str]:
        """Get a suggested response for unknown intents"""
        if intent == Intent.UNKNOWN:
            return "I'm not sure what you need. Try asking about your stats, patients, or tasks. Type /help for more info."

        return None

    def get_help_text(self) -> str:
        """Get help text for using the chatbot"""
        return """
💬 **Chatbot Help**

**I can help you with:**

📊 **Stats & Metrics:**
- `/stats` - Your performance stats
- "How many patients do I have?"
- "What's my billing this month?"

👥 **Patients:**
- `/patients` - Your patient list
- `/patients active` - Active patients only
- "Show me patients with gaps > 60 days"

📝 **Tasks:**
- `/tasks` - Your recent tasks
- "What tasks do I have pending?"

🔄 **Workflows:**
- `/workflows` - Pending workflows

✏️ **Data Entry:**
- "Add 30min PCP visit for [patient name]"
- "Update [patient] status to [value]"
- All changes require confirmation before saving

❓ **Help:**
- `/help` - Show this message
"""
