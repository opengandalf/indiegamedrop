"""Configuration constants for the IndieGameDrop dashboard."""

import os

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DB_PATH: str = os.path.join(BASE_DIR, '..', 'data', 'indiegamedrop.db')
LOGS_DIR: str = os.path.join(BASE_DIR, '..', 'logs')
CRON_STATUS_FILE: str = os.path.join(BASE_DIR, 'cron_status.json')
CRON_STATE_SCRIPT: str = os.path.join(BASE_DIR, 'cron_state.py')
PORT: int = 8790
AUTO_REFRESH_SECONDS: int = 60
PER_PAGE: int = 50
