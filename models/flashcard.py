from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.types import TypeDecorator
from . import db
import json
import traceback

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
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
    
    # FSRS specific fields
    fsrs_state = db.Column(JSONEncodedDict, default=dict)
    due_date = db.Column(db.DateTime)
    difficulty = db.Column(db.Float, default=0.0)
    stability = db.Column(db.Float, default=0.0)
    retrievability = db.Column(db.Float, default=0.0)
    state = db.Column(db.Integer, default=0)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    
    def init_fsrs_state(self):
        """Initialize FSRS state for new flashcard"""
        try:
            from services.fsrs_scheduler import Card, get_current_time
            
            # Let FSRS handle default values
            card = Card()
            
            # Only explicitly set the due date
            now = get_current_time()
            card.due = now
            
            # Save state
            self.fsrs_state = card.to_dict()
            self.due_date = now
            self.state = int(card.state)
            
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
    
    @staticmethod
    def fix_missing_states():
        """One-time utility to ensure all flashcards have valid states"""
        from models import db
        
        # Find cards with missing states or FSRS data
        cards_needing_init = Flashcards.query.filter(
            (Flashcards.state.is_(None)) | 
            (Flashcards.due_date.is_(None)) |
            (Flashcards.fsrs_state == {})
        ).all()
        
        print(f"Found {len(cards_needing_init)} cards needing FSRS initialization")
        
        for card in cards_needing_init:
            # Initialize with correct state
            card.init_fsrs_state()
        
        if cards_needing_init:
            db.session.commit()
            print("Fixed card states successfully")
        
        return len(cards_needing_init)
