import logging
import os

import weave

from backend.config import get_settings

logger = logging.getLogger(__name__)

_weave_client = None


def weave_project_path() -> str:
    settings = get_settings()
    if settings.wandb_entity and "/" not in settings.weave_project:
        return f"{settings.wandb_entity}/{settings.weave_project}"
    return settings.weave_project


def weave_ui_url() -> str | None:
    if _weave_client is None:
        return None
    project_id = getattr(_weave_client, "project_id", None)
    if project_id:
        return f"https://wandb.ai/{project_id}/weave"
    return f"https://wandb.ai/{weave_project_path()}/weave"


def initialize_weave() -> bool:
    global _weave_client
    settings = get_settings()
    if settings.weave_disabled:
        logger.warning("Weave tracing is disabled by WEAVE_DISABLED.")
        return False
    if settings.wandb_api_key:
        os.environ.setdefault("WANDB_API_KEY", settings.wandb_api_key)
    if settings.wandb_entity:
        os.environ.setdefault("WANDB_ENTITY", settings.wandb_entity)
    try:
        _weave_client = weave.init(weave_project_path())
        url = weave_ui_url()
        if url:
            logger.info("Weave tracing enabled: %s", url)
        return True
    except Exception as exc:
        logger.warning("Weave initialization failed; traced ops will run locally: %s", exc)
        _weave_client = None
        return False
