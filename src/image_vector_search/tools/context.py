from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolContext:
    search_service: Any
    tag_service: Any
    status_service: Any
    job_runner: Any
    settings: Any
