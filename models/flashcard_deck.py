from datetime import datetime
from sqlalchemy.sql import func, text
from . import db
from sqlalchemy.orm import relationship

class FlashcardDecks(db.Model):
    __tablename__ = 'flashcard_decks'
    
    flashcard_deck_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    
    # Define relationships
    flashcards = relationship("Flashcards", backref="deck", cascade="all, delete-orphan")
    child_decks = relationship("FlashcardDecks", 
                              backref=db.backref('parent_deck', remote_side=[flashcard_deck_id]),
                              cascade="all, delete-orphan")

    def count_all_flashcards(self, visited=None):
        """Count flashcards in this deck and all sub-decks with cycle detection"""
        # Initialize visited set on first call
        if visited is None:
            visited = set()
        
        # Check for cycles
        if self.flashcard_deck_id in visited:
            # We've already seen this deck, so we have a cycle
            return 0
        
        # Add current deck to visited set
        visited.add(self.flashcard_deck_id)
        
        # Count cards in this deck
        count = len(self.flashcards)
        
        # Recursively count cards in sub-decks
        for sub_deck in self.child_decks:
            count += sub_deck.count_all_flashcards(visited)
        
        return count
    
    def count_all_sub_decks(self):
        """Count all sub-decks recursively"""
        count = len(self.child_decks)
        for sub_deck in self.child_decks:
            count += sub_deck.count_all_sub_decks()
        return count
    
    def to_dict(self):
        """Convert deck to dictionary for API responses"""
        return {
            'id': self.flashcard_deck_id,
            'name': self.name,
            'description': self.description,
            'parent_deck_id': self.parent_deck_id,
            'user_id': self.user_id,
            'card_count': len(self.flashcards) if self.flashcards else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_public': self.is_public,
        }
        
    def get_mastery_stats(self):
        """Get mastery statistics for the deck"""
        from .flashcard import Flashcards
        
        # Use recursive CTE to find all cards in this deck and sub-decks
        cte = db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.flashcard_deck_id == self.flashcard_deck_id
        ).cte(name='study_decks', recursive=True)

        cte = cte.union_all(
            db.session.query(
                FlashcardDecks.flashcard_deck_id.label('id')
            ).filter(
                FlashcardDecks.parent_deck_id == cte.c.id
            )
        )
        
        # Get cards from all decks in the hierarchy
        cards = Flashcards.query.filter(
            Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
        ).all()
        
        # Count cards by FSRS state
        total = len(cards)
        new = 0
        learning = 0
        mastered = 0
        forgotten = 0
        
        for card in cards:
            state = card.state or 0
            if state == 0:
                new += 1
            elif state == 1:
                learning += 1
            elif state == 2:
                mastered += 1
            elif state == 3:
                forgotten += 1
        
        return {
            'total': total,
            'new': new,
            'learning': learning,
            'mastered': mastered,
            'forgotten': forgotten,
            'mastery_percentage': (mastered / total * 100) if total > 0 else 0
        }
