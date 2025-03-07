from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.types import TypeDecorator
from . import db
import json
import traceback
from dataclasses import dataclass
import json
from typing import List, Set

class FlashcardSet:
    """Manage unique flashcards with deduplication"""
    def __init__(self):
        self._cards: set = set()
        self._count: int = 0
    
    def add(self, card: str) -> bool:
        """Add card if unique, return True if added"""
        card_normalized = self._normalize_card(card)
        if card_normalized not in self._cards:
            self._cards.add(card_normalized)
            self._count += 1
            return True
        return False
    
    @staticmethod
    def _normalize_card(card: str) -> str:
        """Normalize card text for comparison"""
        q, a = card.split('|')
        return f"{' '.join(q.split()).lower()}|{' '.join(a.split()).lower()}"
    
    def __len__(self) -> int:
        return self._count

class FlashcardGenerator:
    """Generate and process flashcards"""
    def __init__(self, client):
        self.client = client
        self.unique_cards = FlashcardSet()

class JSONEncodedDict(TypeDecorator):
    """Represents a JSON-encoded dictionary as a text column."""
    impl = db.Text
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

class Flashcards(db.Model):
    __tablename__ = 'flashcards'
    
    flashcard_id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    incorrect_answers = db.Column(JSON, nullable=False)
    flashcard_deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_reviewed = db.Column(db.DateTime)
    
    # FSRS specific fields
    fsrs_state = db.Column(JSONEncodedDict, default=dict)
    due_date = db.Column(db.DateTime)
    difficulty = db.Column(db.Float, default=0.0)
    stability = db.Column(db.Float, default=0.0)
    retrievability = db.Column(db.Float, default=0.0)
    state = db.Column(db.Integer, default=0)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    
    def init_fsrs_state(self):
        """Initialize FSRS state for new flashcard with custom 'New' state (0)"""
        try:
            from services.fsrs_scheduler import Card, get_current_time
            
            # Create a new card (will be in state 1 by default)
            card = Card()
            
            # Override the state with our custom 'New' state (0)
            # We'll manually track this state and change to FSRS states during review
            card_dict = card.to_dict()
            card_dict['state'] = 0  # Our custom state for "New" cards
            
            # Set due date to now (immediately available)
            now = get_current_time()
            card.due = now
            
            # Save modified state to database
            self.fsrs_state = card_dict
            self.due_date = now
            self.state = 0  # Explicitly use 0 for "New" state
            
            return self
        except Exception as e:
            print(f"Error initializing FSRS state: {e}")
            print(traceback.format_exc())
            
            # Minimal fallback
            self.fsrs_state = {}
            self.due_date = datetime.now(timezone.utc)
            self.state = 0
            
            return self
        
    def get_fsrs_card(self):
        """Convert to FSRS Card object"""
        try:
            from services.fsrs_scheduler import Card
            
            if not self.fsrs_state:
                print("No FSRS state, creating a new card")
                card = Card()
                self.fsrs_state = card.to_dict()
            else:
                print(f"Loading card from state: {self.fsrs_state}")
                card = Card.from_dict(self.fsrs_state)
                
            return card
        except Exception as e:
            print(f"Error getting FSRS card: {e}")
            print(traceback.format_exc())
            
            # Simple fallback
            from services.fsrs_scheduler import Card
            return Card()
        
    def get_state_name(self):
        """Get user-friendly state name"""
        state_names = {
            0: "new",
            1: "learning",
            2: "mastered",  # Review/Graduated
            3: "forgotten"   # Relearning/Lapsed
        }
        return state_names.get(self.state, "new")
