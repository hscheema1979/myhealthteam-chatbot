"""
pytest configuration for MyHealthTeam Chatbot tests
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ.setdefault("DATABASE_PATH", str(project_root / "production_backup_for_testing.db"))
