import requests
import json
import os
from typing import Dict, List, Optional, Union
import logging

class SlackNotifier:
    """
    Handles Slack notifications for MatchPlay tournament events
    """
    def __init__(self, webhook_url: str, channel: Optional[str] = None):
        """
        Initialize the Slack notifier
        
        Args:
            webhook_url: Slack webhook URL for posting messages
            channel: Optional channel override (if not using webhook default)
        """
        self.webhook_url = webhook_url
        self.channel = channel
        self.logger = logging.getLogger('SlackNotifier')
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for Slack notifications"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def send_message(self, 
                    text: str, 
                    blocks: Optional[List[Dict]] = None,
                    attachments: Optional[List[Dict]] = None) -> bool:
        """
        Send a message to Slack
        
        Args:
            text: The message text (fallback for notifications)
            blocks: Optional Block Kit blocks for rich formatting
            attachments: Optional legacy attachments
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        payload = {
            "text": text
        }
        
        if self.channel:
            payload["channel"] = self.channel
        
        if blocks:
            payload["blocks"] = blocks
            
        if attachments:
            payload["attachments"] = attachments
        
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            self.logger.info(f"Message sent successfully to Slack: {text[:50]}...")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False
    
    def notify_round_start(self, 
                          round_name: str, 
                          player_assignments: List[Dict],
                          tournament_name: str) -> bool:
        """
        Notify players about a new round starting
        
        Args:
            round_name: The name/number of the round
            player_assignments: List of player game assignments
            tournament_name: Name of the tournament
            
        Returns:
            bool: True if notification sent successfully
        """
        # Build a rich Block Kit message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 New Round Starting: {round_name}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tournament:* {tournament_name}\n*Round:* {round_name}\n\nPlease check your game assignments below:"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Group assignments by machine for cleaner display
        machine_groups = {}
        for assignment in player_assignments:
            machine = assignment.get('machine_name', 'Unknown Machine')
            if machine not in machine_groups:
                machine_groups[machine] = []
            machine_groups[machine].append(assignment)
        
        # Add each machine assignment as a section
        for machine, assignments in machine_groups.items():
            player_text = ""
            for idx, assignment in enumerate(assignments):
                player_name = assignment.get('player_name', 'Unknown Player')
                player_text += f"• Player {idx+1}: *{player_name}*\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🎮 {machine}*\n{player_text}"
                }
            })
            
            # If we have pintips for this machine, include them
            if 'pintips' in assignment and assignment['pintips']:
                tip_text = "💡 *Tips:*\n"
                for i, tip in enumerate(assignment['pintips'][:3]):  # Limit to top 3 tips
                    tip_text += f"• {tip}\n"
                    
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": tip_text
                    }
                })
                
            blocks.append({
                "type": "divider"
            })
        
        # Add footer with instructions
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Remember to enter your scores in MatchPlay when finished. Good luck!"
                }
            ]
        })
        
        return self.send_message(
            text=f"New Round Starting: {round_name} - {tournament_name}",
            blocks=blocks
        )
    
    def notify_game_results(self,
                           game_results: Dict,
                           tournament_name: str) -> bool:
        """
        Send notification about completed game results
        
        Args:
            game_results: Dictionary containing game results data
            tournament_name: Name of the tournament
            
        Returns

        Continuing with the rest of slack_notifier.py:

```python
            bool: True if notification sent successfully
        """
        machine_name = game_results.get('machine_name', 'Unknown Machine')
        round_name = game_results.get('round_name', 'Unknown Round')
        players = game_results.get('players', [])
        
        # Sort players by position
        players.sort(key=lambda x: x.get('position', 999))
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🏆 Game Results",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tournament:* {tournament_name}\n*Round:* {round_name}\n*Machine:* {machine_name}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Add player results
        results_text = ""
        for player in players:
            position = player.get('position', '?')
            name = player.get('player_name', 'Unknown Player')
            score = player.get('score', 0)
            
            # Format position with emoji
            position_emoji = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else "🎮"
            
            results_text += f"{position_emoji} *{name}*: {score:,} points\n"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": results_text
            }
        })
        
        return self.send_message(
            text=f"Game Results - {machine_name} - {tournament_name}",
            blocks=blocks
        )
    
    def notify_tournament_standings(self,
                                  standings: List[Dict],
                                  tournament_name: str,
                                  top_n: int = 10) -> bool:
        """
        Send current tournament standings
        
        Args:
            standings: List of player standings
            tournament_name: Name of the tournament
            top_n: Number of top players to include (default 10)
            
        Returns:
            bool: True if notification sent successfully
        """
        # Sort standings by position and limit to top N
        standings.sort(key=lambda x: x.get('position', 999))
        top_standings = standings[:top_n]
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text", 
                    "text": f"📊 Current Tournament Standings",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tournament:* {tournament_name}\n\nHere are the current top {len(top_standings)} players:"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Create standings table
        table_text = ""
        for player in top_standings:
            position = player.get('position', '?')
            name = player.get('name', 'Unknown Player')
            points = player.get('points', 0)
            games_played = player.get('gamesPlayed', 0)
            
            # Format position with emoji for top 3
            position_marker = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else f"{position}."
            
            table_text += f"{position_marker} *{name}* - {points} pts ({games_played} games)\n"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": table_text
            }
        })
        
        # Add note about full standings
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "View complete standings in the MatchPlay Events app or website."
                }
            ]
        })
        
        return self.send_message(
            text=f"Current Tournament Standings - {tournament_name}",
            blocks=blocks
        )
    
    def notify_player_up_next(self,
                            player_name: str,
                            game_details: Dict,
                            tournament_name: str) -> bool:
        """
        Send a direct notification to a player that they're up next
        
        Args:
            player_name: Name of the player to notify
            game_details: Details about the upcoming game
            tournament_name: Name of the tournament
            
        Returns:
            bool: True if notification sent successfully
        """
        machine_name = game_details.get('machine_name', 'Unknown Machine')
        machine_location = game_details.get('machine_location', '')
        round_name = game_details.get('round_name', 'Unknown Round')
        opponents = game_details.get('opponents', [])
        pintips = game_details.get('pintips', [])
        
        location_text = f" ({machine_location})" if machine_location else ""
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔔 You're Up Next!",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Hey *{player_name}*, you're up for your next game!\n\n*Tournament:* {tournament_name}\n*Round:* {round_name}\n*Machine:* {machine_name}{location_text}"
                }
            }
        ]
        
        # Add opponents if available
        if opponents:
            opponents_text = "*Opponents:*\n"
            for opp in opponents:
                opponents_text += f"• {opp}\n"
                
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": opponents_text
                }
            })
        
        # Add machine tips if available (limit to top 3)
        if pintips:
            tips_text = "💡 *Machine Tips:*\n"
            for i, tip in enumerate(pintips[:3]):
                tips_text += f"{i+1}. {tip}\n"
                
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": tips_text
                }
            })
        
        return self.send_message(
            text=f"You're up next on {machine_name} - {tournament_name}",
            blocks=blocks
        )
```
