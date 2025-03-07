from datetime import datetime
from sqlalchemy.sql import func, text
from . import db

class FlashcardDecks(db.Model):
    __tablename__ = 'flashcard_decks'
    
    flashcard_deck_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    parent_deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    parent_deck = db.relationship('FlashcardDecks', 
                                remote_side=[flashcard_deck_id],
                                backref=db.backref('child_decks', 
                                                  lazy=True,
                                                  cascade='all, delete-orphan'),
                                lazy=True)
    
    flashcards = db.relationship('Flashcards', 
                               backref='deck',
                               lazy=True,
                               cascade='all, delete-orphan')
    
    def count_all_flashcards(self):
        from .flashcard import Flashcards  # Keep this local import to avoid circular imports
        
        cte = db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.flashcard_deck_id == self.flashcard_deck_id
        ).cte(name='cte', recursive=True)

        cte = cte.union_all(
            db.session.query(
                FlashcardDecks.flashcard_deck_id.label('id')
            ).filter(
                FlashcardDecks.parent_deck_id == cte.c.id
            )
        )

        count = db.session.query(func.count(Flashcards.flashcard_id)).filter(
            Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
        ).scalar()

        return count

    def count_all_sub_decks(self):
        """Count all sub-decks recursively using CTE"""
        cte = db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == self.flashcard_deck_id
        ).cte(name='sub_decks', recursive=True)

        cte = cte.union_all(
            db.session.query(
                FlashcardDecks.flashcard_deck_id.label('id')
            ).filter(
                FlashcardDecks.parent_deck_id == cte.c.id
            )
        )

        count = db.session.query(func.count(cte.c.id)).scalar()
        return count
        
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
