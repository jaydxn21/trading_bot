# config_loader.py - load strategy parameters
import json
import os
import logging

logger = logging.getLogger(__name__)

def load_config(file_path: str = "config.json") -> dict:
    """
    Load trading parameters from a JSON config file.
    """
    if not os.path.exists(file_path):
        logger.warning(f"⚠️ Config file not found: {file_path}. Using defaults.")
        return {}

    try:
        with open(file_path, "r") as f:
            config = json.load(f)
        logger.info(f"✅ Loaded config from {file_path}")
        return config
    except Exception as e:
        logger.error(f"❌ Failed to load config: {e}")
        return {}
