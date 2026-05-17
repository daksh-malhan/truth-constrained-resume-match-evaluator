from app import database
from app.config import merge_config
from app.services.admin_config_service import reset_config, update_config


def test_admin_config_save_reset_and_merge():
    database.init_db()
    reset_config()
    saved = update_config({**merge_config().model_dump(), "threshold_score": 7.5, "chunk_size": 700})
    assert saved.threshold_score == 7.5
    merged = merge_config(saved.model_dump(), {"threshold_score": 8.5}, None)
    assert merged.threshold_score == 8.5
    assert merged.chunk_size == 700
    reset = reset_config()
    assert reset.threshold_score == 8.0

