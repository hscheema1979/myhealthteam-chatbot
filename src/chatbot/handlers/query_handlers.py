"""
Query Handlers for Chatbot

Handles read-only queries for stats, patients, tasks, and workflows.
Connects to the existing MyHealthTeam database schema.
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional

from src import database


class QueryHandlers:
    """Handlers for read-only queries"""

    def get_my_stats(self, user_id: int, time_range: str = "month") -> Dict[str, Any]:
        """
        Get personal performance statistics

        Args:
            user_id: User's ID
            time_range: "today", "week", "month", or "year"

        Returns:
            Dict with patient_count, task_count, total_minutes
        """
        conn = database.get_db_connection()

        # Calculate date range
        end_date = datetime.now()
        start_date = self._calculate_start_date(time_range)

        # Get current year/month for table name
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Query coordinator tasks table
        table_name = f"coordinator_tasks_{current_year}_{current_month:02d}"

        # Check if table exists
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()

        stats = {
            "patient_count": 0,
            "task_count": 0,
            "total_minutes": 0,
            "time_range": time_range
        }

        if table_exists:
            # Query stats
            query = f"""
                SELECT
                    COUNT(DISTINCT patient_id) as patient_count,
                    COUNT(*) as task_count,
                    COALESCE(SUM(duration_minutes), 0) as total_minutes
                FROM {table_name}
                WHERE coordinator_id = ?
                    AND datetime(created_at) >= datetime(?)
            """

            result = conn.execute(query, (user_id, start_date.isoformat())).fetchone()

            if result:
                stats = {
                    "patient_count": result["patient_count"] or 0,
                    "task_count": result["task_count"] or 0,
                    "total_minutes": result["total_minutes"] or 0,
                    "time_range": time_range
                }

        conn.close()
        return stats

    def format_stats_response(self, stats: Dict[str, Any], time_range: str = "month") -> str:
        """
        Format stats response for chat display

        Args:
            stats: Stats dictionary from get_my_stats
            time_range: Time range for context in response

        Returns:
            Formatted string response
        """
        time_label = {
            "today": "today",
            "week": "this week",
            "month": "this month",
            "year": "this year",
        }.get(time_range, time_range)

        return f"""📊 **Your Stats {time_label.title()}:**

• **Patients:** {stats['patient_count']}
• **Tasks:** {stats['task_count']}
• **Total Minutes:** {stats['total_minutes']}
"""

    def get_my_patients(
        self,
        user_id: int,
        status: Optional[str] = None,
        gap_days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get patient list for user

        Args:
            user_id: User's ID
            status: Filter by status (active, inactive, discharged)
            gap_days: Filter by gap in days (>60 for gap patients)

        Returns:
            List of patient dictionaries
        """
        conn = database.get_db_connection()

        # Base query for user's assigned patients
        query = """
            SELECT
                p.patient_id,
                p.first_name,
                p.last_name,
                p.status,
                p.facility,
                p.last_visit_date,
                p.goc_status,
                p.code_status
            FROM patients p
            WHERE p.assigned_coordinator_id = ?
        """

        params = [user_id]

        # Add filters
        if status:
            query += " AND p.status = ?"
            params.append(status.title())

        if gap_days:
            days_ago = (datetime.now() - timedelta(days=gap_days)).date()
            query += " AND (p.last_visit_date < ? OR p.last_visit_date IS NULL)"
            params.append(days_ago.isoformat())

        query += " ORDER BY p.last_name, p.first_name"

        try:
            results = conn.execute(query, params).fetchall()
        except Exception as e:
            # Table structure might be different
            print(f"Error querying patients: {e}")
            results = []

        conn.close()

        return [dict(row) for row in results]

    def format_patients_response(self, patients: List[Dict[str, Any]]) -> str:
        """Format patient list for chat display"""
        if not patients:
            return "📋 No patients found."

        response = f"📋 **{len(patients)} Patient(s):**\n\n"

        for p in patients[:10]:  # Limit to 10 for chat
            gap = ""
            if p.get("last_visit_date"):
                try:
                    last_visit = datetime.fromisoformat(p["last_visit_date"]).date()
                    days_since = (datetime.now().date() - last_visit).days
                    if days_since > 60:
                        gap = f" ⚠️ Gap: {days_since}d"
                except:
                    pass
            else:
                gap = " ⚠️ No visits"

            response += f"• **{p['first_name']} {p['last_name']}** ({p.get('status', 'Unknown')})"
            response += f" - {p.get('facility', 'N/A')}{gap}\n"

        if len(patients) > 10:
            response += f"\n_... and {len(patients) - 10} more_"

        return response

    def get_pending_tasks(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent tasks for user

        Args:
            user_id: User's ID
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries
        """
        conn = database.get_db_connection()

        # For now, return tasks from current month's table
        current_year = datetime.now().year
        current_month = datetime.now().month
        table_name = f"coordinator_tasks_{current_year}_{current_month:02d}"

        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()

        if not table_exists:
            conn.close()
            return []

        try:
            query = f"""
                SELECT
                    task_id,
                    patient_id,
                    task_description,
                    service_type,
                    duration_minutes,
                    created_at
                FROM {table_name}
                WHERE coordinator_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """

            results = conn.execute(query, (user_id, limit)).fetchall()
        except Exception as e:
            print(f"Error querying tasks: {e}")
            results = []

        conn.close()

        return [dict(row) for row in results]

    def format_tasks_response(self, tasks: List[Dict[str, Any]]) -> str:
        """Format task list for chat display"""
        if not tasks:
            return "✅ No recent tasks found."

        response = f"📝 **{len(tasks)} Recent Task(s):**\n\n"

        for t in tasks[:10]:
            response += f"• **{t.get('task_description', 'Task')}** ({t.get('service_type', 'N/A')})"
            response += f" - {t.get('duration_minutes', 0)} min\n"

        if len(tasks) > 10:
            response += f"\n_... and {len(tasks) - 10} more_"

        return response

    def get_pending_workflows(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get pending workflows for user

        Args:
            user_id: User's ID

        Returns:
            List of pending workflow dictionaries
        """
        conn = database.get_db_connection()

        # Check if workflow_instances table exists
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_instances'"
        ).fetchone()

        if not table_exists:
            conn.close()
            return []

        try:
            query = """
                SELECT
                    wi.instance_id,
                    wi.patient_id,
                    wi.patient_name,
                    wi.template_id,
                    wi.current_step,
                    wi.workflow_status,
                    wi.created_at
                FROM workflow_instances wi
                WHERE wi.assigned_coordinator_id = ?
                    AND wi.workflow_status = 'Active'
                ORDER BY wi.created_at DESC
                LIMIT 10
            """

            results = conn.execute(query, (user_id,)).fetchall()
        except Exception as e:
            print(f"Error querying workflows: {e}")
            results = []

        conn.close()

        return [dict(row) for row in results]

    def format_workflows_response(self, workflows: List[Dict[str, Any]]) -> str:
        """Format workflow list for chat display"""
        if not workflows:
            return "✅ No pending workflows."

        response = f"🔄 **{len(workflows)} Pending Workflow(s):**\n\n"

        for w in workflows:
            response += f"• Workflow for **{w['patient_name']}**\n"
            response += f"  Step: {w.get('current_step', 'N/A')} | Status: {w.get('workflow_status', 'Active')}\n"

        return response

    def _calculate_start_date(self, time_range: str) -> datetime:
        """Calculate start date for time range query"""
        now = datetime.now()

        if time_range == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "week":
            return now - timedelta(days=now.weekday())
        elif time_range == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "year":
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return now - timedelta(days=30)  # Default to 30 days

    def resolve_patient_id(self, patient_name: str, user_id: int) -> Optional[int]:
        """
        Resolve patient name to patient ID

        Args:
            patient_name: Patient's name (first last)
            user_id: User's ID (to scope to their patients)

        Returns:
            Patient ID or None if not found
        """
        conn = database.get_db_connection()

        # Split name
        parts = patient_name.split()
        if len(parts) < 2:
            conn.close()
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

            conn.close()
            return result["patient_id"] if result else None
        except Exception as e:
            print(f"Error resolving patient: {e}")
            conn.close()
            return None
