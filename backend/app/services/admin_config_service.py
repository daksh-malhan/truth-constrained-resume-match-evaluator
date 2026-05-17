from __future__ import annotations

from typing import Any, Dict, Optional

from .. import database
from ..config import default_config, merge_config
from ..schemas import RunConfig


def get_active_config() -> RunConfig:
    return merge_config(database.get_admin_config())


def update_config(config_data: Dict[str, Any]) -> RunConfig:
    # Admin updates may come from the full UI form or a small API patch. Merge with
    # the active config so omitted fields keep their existing/default values.
    config = merge_config(database.get_admin_config(), config_data)
    database.save_admin_config(config.model_dump())
    return config


def reset_config() -> RunConfig:
    database.reset_admin_config()
    return default_config()
