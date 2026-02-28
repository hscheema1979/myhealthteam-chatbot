"""
MyHealthTeam Chatbot Application
Standalone Streamlit app for intelligent assistant
Runs on port 8502 (separate from main app on port 8501)

Incorporates patterns from Gemini-CLI-UI:
- Subprocess spawning with timeout and cleanup
- Intelligent response buffering
- Session management for conversation context
- Response filtering for debug messages
"""

import streamlit as st
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auth_module import get_auth_manager
from src.database import get_db_connection
from src.core_utils import get_user_role_ids

# Page config
st.set_page_config(
    page_title="MyHealthTeam Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for chat interface
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .bot-message {
        background-color: #f5f5f5;
        border-left: 4px solid #9e9e9e;
    }
    .system-message {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
    }
    .confirmation-message {
        background-color: #fce4ec;
        border-left: 4px solid #e91e63;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .typing-indicator {
        display: inline-block;
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    .quick-actions {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: 0.5rem;
    }
    .quick-action-btn {
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        border: 1px solid #ddd;
        background: white;
        cursor: pointer;
    }
    .quick-action-btn:hover {
        background: #f0f0f0;
    }
</style>
""", unsafe_allow_html=True)


# Session manager for conversation context
class ChatSessionManager:
    """Manages chat sessions with conversation history"""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user_id: int) -> str:
        """Create a new chat session"""
        session_id = f"chat_{user_id}_{int(datetime.now().timestamp())}"
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "context": {}
        }
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        """Add message to session history"""
        if session_id in self.sessions:
            self.sessions[session_id]["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })

    def get_context(self, session_id: str) -> str:
        """Build conversation context for Gemini"""
        if session_id not in self.sessions:
            return ""

        messages = self.sessions[session_id]["messages"]
        if not messages:
            return ""

        # Build context from last 10 messages
        recent = messages[-10:]
        context_parts = []

        for msg in recent:
            if msg["role"] == "user":
                context_parts.append(f"User: {msg['content']}")
            else:
                context_parts.append(f"Assistant: {msg['content']}")

        return "\n\n".join(context_parts)


# Global session manager
session_manager = ChatSessionManager()


def check_authentication() -> Optional[int]:
    """Check if user is authenticated via shared session"""
    # Get session from query params or cookies
    session_id = st.query_params.get("session", None)

    if not session_id:
        return None

    # Validate session against database
    conn = get_db_connection()
    session = conn.execute(
        "SELECT user_id, expires_at FROM user_sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    conn.close()

    if not session:
        return None

    # Check expiration
    if datetime.fromisoformat(session["expires_at"]) < datetime.now():
        return None

    return session["user_id"]


def initialize_session_state(user_id: int):
    """Initialize Streamlit session state"""
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = session_manager.create_session(user_id)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "pending_confirmation" not in st.session_state:
        st.session_state.pending_confirmation = None


def render_message(role: str, content: str, is_streaming: bool = False):
    """Render a chat message with appropriate styling"""
    if role == "user":
        st.markdown(f'<div class="chat-message user-message">👤 **You:** {content}</div>', unsafe_allow_html=True)
    elif role == "assistant":
        placeholder = "" if is_streaming else content
        st.markdown(f'<div class="chat-message bot-message">🤖 **Assistant:**</div>', unsafe_allow_html=True)
        st.markdown(placeholder, unsafe_allow_html=True)
    else:  # system
        st.markdown(f'<div class="chat-message system-message">⚙️ **System:** {content}</div>', unsafe_allow_html=True)


def render_quick_actions():
    """Render quick action buttons"""
    st.markdown("""
    <div class="quick-actions">
        <button class="quick-action-btn" onclick="setInput('/stats')">📊 Stats</button>
        <button class="quick-action-btn" onclick="setInput('/patients')">👥 Patients</button>
        <button class="quick-action-btn" onclick="setInput('/tasks')">📝 Tasks</button>
        <button class="quick-action-btn" onclick="setInput('/help')">❓ Help</button>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar(user_role_ids: List[int]):
    """Render sidebar with help and commands"""
    with st.sidebar:
        st.header("💡 Quick Help")

        st.markdown("**Slash Commands:**")
        st.code("""
/stats       - Your performance stats
/patients    - Your patient list
/tasks       - Your recent tasks
/workflows   - Pending workflows
/help        - Show this help
""", language="bash")

        st.markdown("**Natural Language Examples:**")
        st.markdown("""
- "How many patients do I have?"
- "Show me patients with gaps > 60 days"
- "Add 30min PCP visit for [patient]"
- "Update [patient] status to [value]"
""")

        # Show role-specific info
        if 34 in user_role_ids:  # Admin
            st.info("🔑 Admin: Full access to all features")
        elif 40 in user_role_ids:  # Coordinator Manager
            st.info("👨‍💼 Manager: Can view team stats and reassign patients")
        elif 36 in user_role_ids:  # Care Coordinator
            st.info("📋 Coordinator: Manage your assigned patients")
        elif 33 in user_role_ids:  # Care Provider
            st.info("💚 Provider: View your tasks and patient info")


def main():
    """Main chatbot application"""

    # Check authentication
    user_id = check_authentication()

    if not user_id:
        st.error("❌ Not authenticated. Please log in via the main dashboard.")
        st.info("👉 Go to [care.myhealthteam.org](http://care.myhealthteam.org) to log in")

        # Show login button
        if st.button("🔐 Go to Login", use_container_width=True):
            st.switch_page("http://care.myhealthteam.org")
        return

    # Get user info
    conn = get_db_connection()
    user = conn.execute(
        "SELECT email, first_name, last_name FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    # Get user roles
    user_role_ids = get_user_role_ids(user_id)

    # Initialize session state
    initialize_session_state(user_id)

    # Header with user info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("💬 MyHealthTeam Assistant")
    with col2:
        st.caption(f"👤 {user['first_name']} {user['last_name']}")

    # Render sidebar
    render_sidebar(user_role_ids)

    # Display chat messages
    for message in st.session_state.messages:
        render_message(message["role"], message["content"])

    # Quick actions at bottom
    render_quick_actions()

    # Chat input
    if prompt := st.chat_input("Ask me anything about your patients, tasks, or workflows..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Add to session manager
        session_manager.add_message(st.session_state.chat_session_id, "user", prompt)

        # Display user message
        render_message("user", prompt)

        # Show typing indicator
        with st.container():
            st.markdown('<div class="chat-message bot-message">🤖 <span class="typing-indicator">Thinking...</span></div>', unsafe_allow_html=True)

        # Process message (placeholder - will be replaced with actual handlers)
        response = process_message(
            prompt=prompt,
            user_id=user_id,
            user_role_ids=user_role_ids,
            session_id=st.session_state.chat_session_id
        )

        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Add to session manager
        session_manager.add_message(st.session_state.chat_session_id, "assistant", response)

        # Display assistant response
        render_message("assistant", response)

        # Rerun to show the message
        st.rerun()


def process_message(prompt: str, user_id: int, user_role_ids: List[int], session_id: str) -> str:
    """
    Process user message and generate response

    Natural Language Flow:
    1. QUERY → Execute immediately → Return results
    2. ACTION → Validate → Show confirmation → Execute on confirm
    """
    from src.chatbot.intent_parser import IntentParser, Intent
    from src.chatbot.handlers.query_handlers import QueryHandlers
    from src.chatbot.gemini_client import GeminiClient
    from src.chatbot.action_builder import ActionBuilder
    from src.chatbot.transaction_executor import TransactionExecutor

    # Get conversation history
    conversation_history = session_manager.get_context(session_id)

    # Parse intent
    gemini_client = GeminiClient()
    parse_result = gemini_client.parse_message(
        message=prompt,
        context={"user_id": user_id, "user_role_ids": user_role_ids},
        conversation_history=conversation_history
    )

    # Route to appropriate handler
    intent = parse_result.get("intent", "")
    entities = parse_result.get("entities", {})

    # Handle CONFIRMATION responses
    confirmation = entities.get("confirmation")
    cancellation = entities.get("cancellation")

    if st.session_state.get("pending_action") and (confirmation or cancellation):
        # User is responding to a confirmation prompt
        pending_action = st.session_state["pending_action"]

        if cancellation is False:
            st.session_state["pending_action"] = None
            return "❌ Action cancelled."

        if confirmation is True:
            # Execute the pending action
            executor = TransactionExecutor()
            result = executor.execute_with_confirmation(
                action=pending_action,
                user_id=user_id,
                confirmed=True
            )

            st.session_state["pending_action"] = None

            if result["success"]:
                return f"✅ {result['message']}"
            else:
                return f"❌ {result['message']}"

    # Handle QUERY intents (no confirmation needed)
    if "STATS" in intent:
        query_handlers = QueryHandlers()
        time_range = entities.get("time_range", "month")
        stats = query_handlers.get_my_stats(user_id, time_range)
        return query_handlers.format_stats_response(stats, time_range)

    elif "PATIENTS" in intent:
        query_handlers = QueryHandlers()
        status = entities.get("status")
        patients = query_handlers.get_my_patients(user_id, status)
        return query_handlers.format_patients_response(patients)

    elif "TASKS" in intent:
        query_handlers = QueryHandlers()
        tasks = query_handlers.get_pending_tasks(user_id)
        return query_handlers.format_tasks_response(tasks)

    elif "WORKFLOWS" in intent:
        query_handlers = QueryHandlers()
        workflows = query_handlers.get_pending_workflows(user_id)
        return query_handlers.format_workflows_response(workflows)

    elif "HELP" in intent:
        return """📖 **Help - MyHealthTeam Assistant**

**I can help you with:**

📊 **Queries:**
- `/stats` or "How many patients?"
- `/patients` or "Show active patients"
- `/tasks` or "What are my tasks?"

✏️ **Data Entry:**
- "Add 30min PCP visit for [patient name]"
- "Update [patient] status to [value]"

**Examples:**
- "Add 30min PCP visit for John Smith"
- "Mark Ada Lopez as discharged"
- "Change Ben Kim's status to inactive"

All changes require confirmation before saving.
"""

    # Handle ACTION intents (require confirmation)
    elif "ADD_TASK" in intent or "UPDATE_PATIENT" in intent:
        # Build the action
        builder = ActionBuilder()
        action = builder.build_action(
            natural_language=prompt,
            user_id=user_id,
            context={"user_role_ids": user_role_ids}
        )

        # Check if valid
        if not action.is_valid:
            error_msg = "❌ " + ".join(action.validation_errors)
            return error_msg

        # Store for confirmation and show summary
        st.session_state["pending_action"] = action

        response = action.get_confirmation_summary()
        response += "\n\n**Type 'yes' to confirm or 'no' to cancel.**"

        return response

    else:
        # Unknown intent
        return parse_result.get("suggested_response") or \
            f"I'm not sure how to help with \"{prompt}\". " \
            "Try asking about your stats, patients, or tasks. Type /help for more info."


if __name__ == "__main__":
    main()
