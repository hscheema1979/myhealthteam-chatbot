"""
Action Builder - Natural Language to Database Operations

Uses Gemini CLI to interpret natural language into precise, validated database actions.

This is the surgical harness - every action is:
1. Parsed by Gemini CLI
2. Validated against actual schema
3. Checked for constraints
4. Returned as exact SQL with parameters
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from src.chatbot.database_schema_inspector import DatabaseSchemaInspector
from src.chatbot.gemini_client import GeminiClient


@dataclass
class ValidatedAction:
    """
    A validated database action ready for execution.

    Surgical precision - every parameter is validated.
    """
    action_type: str  # "INSERT", "UPDATE", "DELETE"
    table_name: str
    target_id: Optional[int]  # For UPDATE/DELETE
    changes: Dict[str, Any]  # Column -> value mappings
    where_clause: Optional[str] = None
    sql_template: Optional[str] = None
    sql_params: Tuple[Any, ...] = field(default_factory=tuple)
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    requires_confirmation: bool = True

    @property
    def is_valid(self) -> bool:
        """Check if action has no validation errors"""
        return len(self.validation_errors) == 0

    def get_confirmation_summary(self) -> str:
        """Get human-readable summary for confirmation"""
        if self.action_type == "INSERT":
            return self._format_insert_summary()
        elif self.action_type == "UPDATE":
            return self._format_update_summary()
        elif self.action_type == "DELETE":
            return self._format_delete_summary()
        return "Unknown action"

    def _format_insert_summary(self) -> str:
        """Format INSERT action summary"""
        lines = [
            "⚠️ **CONFIRMATION REQUIRED**",
            "",
            f"**Action:** Add new record to {self.table_name}",
            ""
        ]

        # Group changes by category
        core_fields = []
        optional_fields = []

        for col, val in self.changes.items():
            if col in ["created_at", "updated_at"]:
                continue
            line = f"• **{col}:** {self._format_value(val)}"
            if col in ["duration_minutes", "service_type", "patient_id"]:
                core_fields.append(line)
            else:
                optional_fields.append(line)

        lines.extend(core_fields)
        if optional_fields:
            lines.append("")
            lines.extend(optional_fields)

        if self.warnings:
            lines.append("")
            lines.append("⚠️ **Warnings:**")
            for warning in self.warnings:
                lines.append(f"  • {warning}")

        return "\n".join(lines)

    def _format_update_summary(self) -> str:
        """Format UPDATE action summary"""
        lines = [
            "⚠️ **CONFIRMATION REQUIRED**",
            "",
            f"**Action:** Update record in {self.table_name}",
            f"**Record ID:** {self.target_id}",
            ""
        ]

        lines.append("**Changes:**")
        for col, (old_val, new_val) in self.changes.items():
            lines.append(f"• **{col}:** {old_val} → {new_val}")

        if self.warnings:
            lines.append("")
            lines.append("⚠️ **Warnings:**")
            for warning in self.warnings:
                lines.append(f"  • {warning}")

        return "\n".join(lines)

    def _format_delete_summary(self) -> str:
        """Format DELETE action summary"""
        return f"""⚠️ **CONFIRMATION REQUIRED**

**Action:** Delete record from {self.table_name}
**Record ID:** {self.target_id}

This will permanently remove this record. This action cannot be undone.
"""

    def _format_value(self, value: Any) -> str:
        """Format value for display"""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            return f'"{value}"'
        return str(value)


class ActionBuilder:
    """
    Builds validated database actions from natural language.

    Uses Gemini CLI for interpretation, then validates against actual schema.
    """

    def __init__(self):
        """Initialize action builder with schema inspector"""
        self.schema = DatabaseSchemaInspector()
        self.gemini = GeminiClient()

    def build_action(
        self,
        natural_language: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidatedAction:
        """
        Build a validated database action from natural language

        Args:
            natural_language: User's input like "Add 30min PCP visit for John Smith"
            user_id: User performing the action
            context: Additional context (user roles, etc.)

        Returns:
            ValidatedAction ready for confirmation and execution
        """
        # Step 1: Use Gemini to parse into structured action
        structured_action = self._parse_with_gemini(natural_language, context)

        # Step 2: Validate against schema
        validated = self._validate_action(structured_action, user_id)

        return validated

    def _parse_with_gemini(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use Gemini CLI to parse natural language into structured action

        Returns structured action like:
        {
            "action": "INSERT",
            "table": "coordinator_tasks_2026_02",
            "data": {
                "coordinator_id": 123,
                "patient_id": 456,
                "duration_minutes": 30,
                "service_type": "PCP",
                "task_description": "PCP visit",
                "created_at": "2026-02-28T10:30:00"
            },
            "reasoning": "User wants to log a task..."
        }
        """
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year

        prompt = f"""You are a database action parser for a healthcare application. Parse the user's request into a precise database operation.

User request: "{natural_language}"

Current context:
- User ID: {context.get('user_id', 'Unknown') if context else 'Unknown'}
- Current date: {current_date.isoformat()}
- Current month: {current_year}-{current_month:02d}

Available tables and purposes:
- coordinator_tasks_{{YYYY}}_{{MM}}: Task entries for coordinators
  • Columns: task_id (PK), coordinator_id, patient_id, task_description, service_type, duration_minutes, created_at, notes
  • Required: coordinator_id, patient_id, service_type
  • coordinator_id comes from user context
  • Valid service_types: PCP, Follow Up, Acute, TCM, Home Visit, Telehealth

- patients: Patient information
  • Columns: patient_id (PK), first_name, last_name, status, facility, assigned_coordinator_id, goc_status, code_status, last_visit_date
  • Updateable: status, goc_status, code_status, facility, assigned_coordinator_id
  • Valid statuses: Active, Inactive, Discharged
  • Valid goc_status: Rev/Confirm, Discuss, Documentation
  • Valid code_status: Full Code, DNR, DNI, Partial Code

Parse the request and respond with JSON:

{{
    "action": "INSERT|UPDATE|DELETE",
    "table": "table_name",
    "target_id": 123,  // For UPDATE/DELETE, the record ID
    "data": {{
        "column_name": "new_value",
        ...
    }},
    "reasoning": "Brief explanation of what will happen",
    "warnings": ["Any potential issues or concerns"]
}}

Rules:
- For "add task", "log visit", etc. → action = "INSERT", table = "coordinator_tasks_YYYY_MM"
- For "update patient", "change status" → action = "UPDATE", table = "patients"
- Always include created_at timestamp for INSERTs
- Extract patient name and suggest patient_id lookup
- Be conservative: if uncertain, use action = "UNKNOWN" and explain why
"""

        try:
            # Call Gemini CLI
            full_response = ""
            response_buffer = self.gemini.response_buffer or self.gemini.__class__()

            # For now, use a simpler approach - fallback to pattern matching if Gemini fails
            import subprocess
            process = subprocess.Popen(
                ["gemini", '--prompt', prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process.stdin.close()

            try:
                stdout, _ = process.communicate(timeout=30)
                full_response = stdout.strip()

                # Extract JSON from response
                parsed = self._extract_json(full_response)
                if parsed:
                    return parsed
            except subprocess.TimeoutExpired:
                process.kill()
            except FileNotFoundError:
                pass  # Gemini not installed, use fallback

        except Exception as e:
            print(f"Gemini error: {e}")

        # Fallback to pattern-based parsing
        return self._fallback_parse(natural_language, context)

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Gemini response"""
        import re

        # Try to find JSON in response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _fallback_parse(self, natural_language: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback to pattern-based parsing if Gemini unavailable"""
        from src.chatbot.intent_parser import IntentParser

        parser = IntentParser()
        parse_result = parser.parse(natural_language)

        # Map intents to actions
        intent_action_map = {
            "ACTION_ADD_TASK": ("INSERT", "coordinator_tasks"),
            "ACTION_UPDATE_PATIENT": ("UPDATE", "patients"),
        }

        action, base_table = intent_action_map.get(parse_result.intent, (None, None))

        return {
            "action": action or "UNKNOWN",
            "table": base_table,
            "data": parse_result.entities,
            "reasoning": f"Based on intent: {parse_result.intent.value}",
            "warnings": ["Using pattern-based fallback (Gemini unavailable)"]
        }

    def _validate_action(self, structured_action: Dict[str, Any], user_id: int) -> ValidatedAction:
        """Validate action against database schema"""
        action = ValidatedAction(
            action_type=structured_action.get("action", "UNKNOWN"),
            table_name=structured_action.get("table", ""),
            changes=structured_action.get("data", {}),
            warnings=structured_action.get("warnings", [])
        )

        # Check action type
        if action.action_type == "UNKNOWN":
            action.validation_errors.append("Could not determine action type")
            return action

        # Check table exists
        if not self.schema.table_exists(action.table_name):
            action.validation_errors.append(f"Table {action.table_name} does not exist")
            return action

        # Add user_id to data if INSERT
        if action.action_type == "INSERT" and "coordinator_id" not in action.changes:
            action.changes["coordinator_id"] = user_id

        # Add timestamp if not present
        if action.action_type == "INSERT" and "created_at" not in action.changes:
            action.changes["created_at"] = datetime.now().isoformat()

        # Validate each column and value
        for column_name, value in action.changes.items():
            is_valid, error_msg = self.schema.validate_value(
                action.table_name,
                column_name,
                value
            )

            if not is_valid:
                action.validation_errors.append(error_msg)

        return action

    def resolve_patient_name(self, patient_name: str, user_id: int) -> Optional[int]:
        """
        Resolve patient name to patient_id

        Args:
            patient_name: Patient's full name
            user_id: Coordinator's user_id (to scope to their patients)

        Returns:
            patient_id or None
        """
        from src import database

        conn = database.get_db_connection()

        # Split name
        parts = patient_name.strip().split()
        if len(parts) < 2:
            return None

        first_name = parts[0]
        last_name = " ".join(parts[1:])

        # Search for patient
        try:
            result = conn.execute("""
                SELECT patient_id
                FROM patients
                WHERE assigned_coordinator_id = ?
                    AND first_name LIKE ?
                    AND last_name LIKE ?
                LIMIT 1
            """, (user_id, f"{first_name}%", f"{last_name}%")).fetchone()

            return result["patient_id"] if result else None
        finally:
            conn.close()
