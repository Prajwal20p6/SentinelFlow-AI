from enum import Enum
from typing import Dict, Optional

class GuardRailType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    COMMAND_INJECTION = "command_injection"
    SENSITIVE_DATA = "sensitive_data"

class GuardRailRequest:
    def __init__(self, content: str, guard_rail_type: GuardRailType, context: Optional[Dict] = None):
        self.content = content
        self.guard_rail_type = guard_rail_type
        self.context = context or {}
