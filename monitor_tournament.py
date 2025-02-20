import os
import sys
import json
import time
import argparse
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from dotenv import load_dotenv

from matchplay_games_extractor import MatchPlayGamesExtractor
from slack_notifier import SlackNotifier, setup_slack_notifications, notify_tournament_start
from slack_notifier import notify_player_assignments, send_standings_notification, notify_completed_games

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path('logs/matchplay_monitor.log').absolute(), mode='a')
    ]
)
logger = logging.getLogger('matchplay_monitor')

# Global tracking variables
last_standings_update = datetime.now() - timedelta(hours=1)
processed_rounds = set()
processed_games = set()
tournament_status = None


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json file"""
    config_path = Path('config.json').absolute()
    try:
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load config file: {e}")
        # Return default configuration
        return {
            "api": {
                "poll_interval_seconds": 300,
            },
            "notifications": {
                "standings_update_interval_minutes": 30
            }
        }


def extract_tournament_id(tournament_url: str) -> Optional[int]:
    """Extract tournament ID from URL"""
    try:
        match = re.search(r'/tournaments/(\d+)', tournament_url)
        if match:
            return int(match.group(1))
        return None
    except (AttributeError, ValueError, TypeError):
        return None
