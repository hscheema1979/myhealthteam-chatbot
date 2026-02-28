"""
Gemini CLI Client for Chatbot

Interface to Gemini CLI for natural language processing.

Incorporates patterns from Gemini-CLI-UI:
- Subprocess spawning with timeout and cleanup
- Intelligent response buffering
- Process tracking for abort capability
- Session management for conversation context
- Response filtering for debug messages
"""

import subprocess
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import os


class GeminiResponseBuffer:
    """
    Intelligent response buffer - avoids sending fragmented messages.

    Based on Gemini-CLI-UI's GeminiResponseHandler:
    - Buffers output until complete logical units
    - Detects code blocks to avoid splitting mid-block
    - Configurable delay thresholds
    """

    def __init__(self, partial_delay: int = 300, max_wait_time: int = 1500, min_buffer_size: int = 30):
        self.buffer: str = ""
        self.last_sent_time = datetime.now()
        self.partial_delay = partial_delay
        self.max_wait_time = max_wait_time
        self.min_buffer_size = min_buffer_size
        self.in_code_block = False
        self.code_block_count = 0

        # Patterns that indicate message completion
        self.completion_patterns = [
            re.compile(r'\.\s*$'),        # Ends with period
            re.compile(r'\?\s*$'),        # Ends with question mark
            re.compile(r'!\s*$'),         # Ends with exclamation
            re.compile(r'```\s*$'),       # Ends with code block
            re.compile(r':\s*$'),          # Ends with colon
            re.compile(r'\n\n$'),          # Double line break
        ]

    def add_data(self, data: str) -> List[str]:
        """
        Add incoming data and return any ready-to-send chunks

        Args:
            data: Raw data from Gemini CLI stdout

        Returns:
            List of complete message chunks ready to send
        """
        self.buffer += data
        self._update_code_block_state()

        chunks = []

        if self.in_code_block:
            # Wait for code block to complete
            if self._is_code_block_complete():
                chunks.append(self._flush())
        else:
            # Normal processing
            if self._should_send_now():
                chunks.append(self._flush())

        return chunks

    def flush(self) -> str:
        """Force flush any remaining buffered content"""
        if self.buffer:
            content = self.buffer.strip()
            self.buffer = ""
            return self._fix_formatting(content)
        return ""

    def _update_code_block_state(self):
        """Track whether we're inside a code block"""
        code_blocks = self.buffer.count('```')
        self.code_block_count = code_blocks
        self.in_code_block = (code_blocks % 2) != 0

    def _is_code_block_complete(self):
        """Check if current code block is complete"""
        return self.code_block_count > 0 and self.code_block_count % 2 == 0

    def _should_send_now(self) -> bool:
        """Determine if buffered content is ready to send"""
        if len(self.buffer) < self.min_buffer_size:
            return False

        if self.in_code_block:
            return False

        # Check completion patterns
        for pattern in self.completion_patterns:
            if pattern.search(self.buffer.strip()):
                return True

        # Check time-based threshold
        time_since_last = (datetime.now() - self.last_sent_time).total_seconds()
        if time_since_last > (self.max_wait_time / 1000.0):
            return True

        return False

    def _flush(self) -> str:
        """Flush and reset buffer"""
        if not self.buffer:
            return ""

        content = self.buffer.strip()
        self.buffer = ""
        self.last_sent_time = datetime.now()

        return self._fix_formatting(content)

    def _fix_formatting(self, content: str) -> str:
        """Fix common formatting issues"""
        # Remove excessive newlines (but not in code blocks)
        if '```' not in content:
            content = re.sub(r'\n{4,}', '\n\n\n', content)
        else:
            # Preserve code block structure, clean up edges
            lines = content.split('\n')
            # Find code block boundaries
            in_code = False
            cleaned = []
            for i, line in enumerate(lines):
                if '```' in line:
                    in_code = not in_code
                    cleaned.append(line)
                elif in_code:
                    cleaned.append(line)
                else:
                    # Outside code blocks, limit consecutive newlines
                    if line.strip() or (cleaned and cleaned[-1].strip()):
                        cleaned.append(line)
            content = '\n'.join(cleaned)

        return content.strip()

    def reset(self):
        """Reset buffer state"""
        self.buffer = ""
        self.in_code_block = False
        self.code_block_count = 0


class GeminiClient:
    """
    Client for interacting with Gemini CLI

    Incorporates patterns from Gemini-CLI-UI:
    - Subprocess spawning with proper environment
    - Timeout handling
    - Process cleanup and abort capability
    - Stdout/stderr filtering
    - Session context management
    """

    def __init__(self, cli_command: str = "gemini", timeout_ms: int = 30000):
        """
        Initialize Gemini client

        Args:
            cli_command: Command to run Gemini CLI (default: "gemini")
            timeout_ms: Timeout for subprocess in milliseconds
        """
        self.cli_command = cli_command
        self.timeout_ms = timeout_ms
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.response_buffer = GeminiResponseBuffer()  # For buffering responses

    def parse_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse user message using Gemini CLI

        Args:
            message: User's input message
            context: Additional context (user_id, roles, etc.)
            conversation_history: Previous conversation for context

        Returns:
            Dict with intent, entities, and confidence
        """
        # Build prompt for Gemini with system instructions
        prompt = self._build_parse_prompt(message, context, conversation_history)

        try:
            # Spawn Gemini process
            full_response = ""
            response_buffer = GeminiResponseBuffer()

            process = subprocess.Popen(
                [self.cli_command, '--prompt', prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                env={**os.environ, 'LANG': 'en_US.UTF-8'},
                text=True
            )

            # Close stdin - we're using --prompt flag
            process.stdin.close()

            # Read output with timeout
            import select
            import time

            start_time = time.time()
            has_output = False

            while True:
                # Check if process has output
                if select.select([process.stdout], [], [], 0.1)[0]:
                    has_output = True
                    try:
                        line = process.stdout.readline()
                        if line:
                            # Filter debug messages
                            filtered = self._filter_debug_messages(line)
                            if filtered:
                                chunks = response_buffer.add_data(filtered)
                                full_response += filtered
                    except:
                        break

                # Check if process is done
                if process.poll() is not None:
                    break

                # Timeout check
                if (time.time() - start_time) * 1000 > self.timeout_ms:
                    if not has_output:
                        raise TimeoutError(f"Gemini CLI timeout after {self.timeout_ms}ms")
                    break

            # Flush any remaining content
            remaining = response_buffer.flush()
            if remaining:
                full_response += remaining

            # Check for errors
            if process.returncode not in [0, None]:
                stderr_output = process.stderr.read() if process.stderr else ""
                if stderr_output and not self._is_harmless_error(stderr_output):
                    print(f"Gemini CLI stderr: {stderr_output}")

            # Parse Gemini response
            return self._parse_gemini_response(full_response)

        except (subprocess.TimeoutExpired, TimeoutError, FileNotFoundError, Exception) as e:
            # Fall back to pattern matching on any error
            print(f"Gemini CLI error: {e}, falling back to pattern matching")
            return self._fallback_parse(message, context)

    def _filter_debug_messages(self, output: str) -> str:
        """
        Filter out debug and system messages from Gemini CLI output

        Based on Gemini-CLI-UI filtering patterns
        """
        # Skip debug messages
        skip_patterns = [
            '[DEBUG]',
            'Flushing log events',
            'Clearcut response',
            '[MemoryDiscovery]',
            '[BfsFileSearch]',
            'Loaded cached credentials',
            'DeprecationWarning',
            '--trace-deprecation',
        ]

        for pattern in skip_patterns:
            if pattern in output:
                return ""

        return output.strip()

    def _is_harmless_error(self, stderr: str) -> bool:
        """Check if stderr error is harmless (warnings, etc.)"""
        harmless_patterns = [
            'DeprecationWarning',
            'Loaded cached credentials',
            'future warnings',
        ]
        return any(pattern in stderr for pattern in harmless_patterns)

    def _build_parse_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
        conversation_history: Optional[str]
    ) -> str:
        """Build prompt for Gemini CLI for intent classification"""
        history_part = f"\nPrevious conversation:\n{conversation_history}\n" if conversation_history else ""

        return f"""You are a healthcare assistant intent classifier. Analyze this message and respond with JSON.

{history_part}

User message: "{message}"

Classify into one of these intents:
- QUERY_STATS: User wants statistics/metrics
- QUERY_PATIENTS: User wants patient information
- QUERY_TASKS: User wants task information
- QUERY_WORKFLOWS: User wants workflow information
- ACTION_ADD_TASK: User wants to log/add a task
- ACTION_UPDATE_PATIENT: User wants to update patient info
- ACTION_CORRECT_ENTRY: User wants to fix a previous entry
- ACTION_ADVANCE_WORKFLOW: User wants to complete a workflow step
- HELP: User needs help
- UNKNOWN: Cannot determine intent

Extract these entities if present:
- duration: number of minutes
- service_type: type of service (PCP, Follow Up, Acute, TCM, Home Visit, Telehealth)
- patient_name: patient's name
- status: active, inactive, discharged, pending
- time_range: today, this week, this month, this year
- scope: self (my stats) or team

Respond with JSON only, no markdown:
{{
    "intent": "QUERY_STATS",
    "entities": {{"scope": "self", "time_range": "week"}},
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this intent was chosen"
}}
"""

    def _parse_gemini_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from Gemini"""
        try:
            # Extract JSON from response (might have markdown code blocks)
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                # Try to find JSON object in response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response.strip()

            return json.loads(json_str)

        except (json.JSONDecodeError, Exception) as e:
            # If parsing fails, return unknown intent
            return {
                "intent": "UNKNOWN",
                "entities": {},
                "confidence": 0.0,
                "error": str(e)
            }

    def _fallback_parse(self, message: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback to pattern-based parsing when Gemini is unavailable"""
        from src.chatbot.intent_parser import IntentParser

        parser = IntentParser()
        result = parser.parse(message)

        return {
            "intent": result.intent.value,
            "entities": result.entities,
            "confidence": result.confidence,
            "fallback": True
        }

    def abort_session(self, session_id: str) -> bool:
        """Abort an active Gemini process by session ID"""
        if session_id in self.active_processes:
            try:
                process = self.active_processes[session_id]
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                del self.active_processes[session_id]
                return True
            except Exception as e:
                print(f"Error aborting session {session_id}: {e}")
                return False
        return False
