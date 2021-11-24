import os
import sys
from typing import Any, Callable, Dict

from feedcloud import constants

DATABASE_URL = ""
BROKER_URL = "amqp://guest:guest@127.0.0.1:5672"
TASK_SCHEDULER_INTERVAL_SECONDS = 60
FEED_MAX_FAILURE_COUNT = 3

IS_TESTING = False


def update_settings_from_env_vars() -> None:
    """
    Update settings using values provided via environment variables.

    Each environment variable name must start with the prefix specified
    by `constants.SETTINGS_ENV_PREFIX`.
    """
    prefix = constants.SETTINGS_ENV_PREFIX
    prefix_len = len(prefix)

    values = dict()

    for env_name, env_value in os.environ.items():
        if not env_name.startswith(prefix):
            continue

        env_name = env_name[prefix_len:]
        values[env_name] = env_value

    update_settings_from_dict(values)


def update_settings_from_dict(new_values: Dict[str, Any]) -> None:
    thismodule = sys.modules[__name__]
    for key, value in new_values.items():
        if key not in dir(thismodule):
            continue

        # Ignore private and non-setting items
        if key.startswith("_") or not key.isupper():
            continue

        current_type = type(getattr(thismodule, key))
        value = _sanitize_value(value, current_type)

        setattr(thismodule, key, value)


def _sanitize_value(value: Any, current_type: Callable) -> Any:
    if not isinstance(value, str):
        return value

    if current_type == bool:
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False

    return current_type(value)
