"""agent-system: Portable Claude agent coordination system."""
__version__ = "0.1.0"

from .akc_http_client import AKCClient
from .agent_learning_utils import build_task_result, validate_task_result
from .config import AgentConfig, load_config, ConfigValidationError

__all__ = [
    "AKCClient",
    "build_task_result",
    "validate_task_result",
    "AgentConfig",
    "load_config",
    "ConfigValidationError",
    "__version__",
]
