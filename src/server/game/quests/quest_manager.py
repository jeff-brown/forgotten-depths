"""Quest management system."""

import json
import os
from typing import Dict, List, Optional, Any
from ...utils.logger import get_logger


class QuestManager:
    """Manages quests and quest progression."""

    def __init__(self, game_engine=None):
        """Initialize the quest manager."""
        self.game_engine = game_engine
        self.logger = get_logger()
        self.quests: Dict[str, Dict] = {}
        self.load_quests()

    def load_quests(self):
        """Load all quests from quests.json."""
        quests_file = os.path.join('data', 'quests.json')

        if not os.path.exists(quests_file):
            self.logger.warning(f"Quests file not found: {quests_file}")
            return

        try:
            with open(quests_file, 'r') as f:
                quests_list = json.load(f)
                for quest in quests_list:
                    self.quests[quest['id']] = quest
            self.logger.info(f"Loaded {len(self.quests)} quests")
        except Exception as e:
            self.logger.error(f"Error loading quests: {e}")

    def get_quest(self, quest_id: str) -> Optional[Dict]:
        """Get quest data by ID."""
        return self.quests.get(quest_id)

    def get_player_quests(self, character: Dict) -> Dict[str, Dict]:
        """Get all quests for a player."""
        return character.get('quests', {})

    def has_quest(self, character: Dict, quest_id: str) -> bool:
        """Check if player has a quest."""
        return quest_id in character.get('quests', {})

    def is_quest_complete(self, character: Dict, quest_id: str) -> bool:
        """Check if a quest is marked complete."""
        quests = character.get('quests', {})
        if quest_id not in quests:
            return False
        return quests[quest_id].get('completed', False)

    def can_accept_quest(self, character: Dict, quest_id: str) -> tuple[bool, str]:
        """Check if player can accept a quest."""
        quest = self.get_quest(quest_id)
        if not quest:
            return False, "Quest not found."

        # Check if already has quest
        if self.has_quest(character, quest_id):
            if self.is_quest_complete(character, quest_id):
                return False, "You have already completed this quest."
            return False, "You already have this quest."

        # Check level requirement
        if quest.get('level_requirement', 0) > character.get('level', 1):
            return False, f"You must be at least level {quest['level_requirement']} to accept this quest."

        return True, ""

    def accept_quest(self, character: Dict, quest_id: str) -> bool:
        """Accept a quest."""
        can_accept, reason = self.can_accept_quest(character, quest_id)
        if not can_accept:
            return False

        quest = self.get_quest(quest_id)
        if not quest:
            return False

        # Initialize quests dict if needed
        if 'quests' not in character:
            character['quests'] = {}

        # Add quest to character
        character['quests'][quest_id] = {
            'accepted': True,
            'completed': False,
            'objectives': {}
        }

        # Initialize objective progress
        for i, objective in enumerate(quest.get('objectives', [])):
            character['quests'][quest_id]['objectives'][i] = {
                'type': objective['type'],
                'progress': 0,
                'required': objective.get('count', 1)
            }

        self.logger.info(f"Player accepted quest: {quest_id}")
        return True

    def check_objective_completion(self, character: Dict, quest_id: str, objective_type: str, target: str, room_id: str = None) -> bool:
        """Check if an objective is completed and update progress."""
        if not self.has_quest(character, quest_id):
            return False

        if self.is_quest_complete(character, quest_id):
            return False

        quest = self.get_quest(quest_id)
        if not quest:
            return False

        quest_progress = character['quests'][quest_id]
        objectives_complete = True

        for i, objective in enumerate(quest.get('objectives', [])):
            if objective['type'] == objective_type and objective.get('target') == target:
                # Check room requirement if specified
                if objective.get('room') and objective['room'] != room_id:
                    continue

                # Update progress
                obj_progress = quest_progress['objectives'][i]
                if obj_progress['progress'] < obj_progress['required']:
                    obj_progress['progress'] += 1
                    self.logger.info(f"Quest {quest_id} objective {i} progress: {obj_progress['progress']}/{obj_progress['required']}")

            # Check if this objective is complete
            obj_progress = quest_progress['objectives'][i]
            if obj_progress['progress'] < obj_progress['required']:
                objectives_complete = False

        # Mark quest complete if all objectives done
        if objectives_complete:
            quest_progress['completed'] = True
            self.logger.info(f"Quest {quest_id} completed!")
            return True

        return False

    def give_quest_reward(self, character: Dict, quest_id: str):
        """Give quest rewards to player."""
        quest = self.get_quest(quest_id)
        if not quest:
            return

        rewards = quest.get('rewards', {})

        # Give experience
        if 'experience' in rewards:
            character['experience'] = character.get('experience', 0) + rewards['experience']
            self.logger.info(f"Gave {rewards['experience']} XP for quest {quest_id}")

        # Give gold
        if 'gold' in rewards:
            character['gold'] = character.get('gold', 0) + rewards['gold']
            self.logger.info(f"Gave {rewards['gold']} gold for quest {quest_id}")

        # Give rune
        if 'rune' in rewards:
            character['rune'] = rewards['rune']
            self.logger.info(f"Gave {rewards['rune']} rune for quest {quest_id}")

        # Mark as rewarded
        if 'quests' in character and quest_id in character['quests']:
            character['quests'][quest_id]['rewarded'] = True
