from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON  # Add PostgreSQL-specific JSON type
from sqlalchemy.sql import func

db = SQLAlchemy()

class FlashcardDecks(db.Model):
    __tablename__ = 'flashcard_decks'
    
    flashcard_deck_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    
    # Self-referential relationship
    parent_deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'), nullable=True)
    
    # Fix: Change FlashcardDeck to FlashcardDecks in the relationship
    parent_deck = db.relationship('FlashcardDecks', 
                                remote_side=[flashcard_deck_id],
                                backref=db.backref('child_decks', lazy=True),
                                lazy=True)
    
    # Relationship to flashcards
    flashcards = db.relationship('Flashcards', 
                               backref='deck',
                               lazy=True,
                               cascade='all, delete-orphan')
    
    def count_all_flashcards(self):
        # Recursive CTE to count all flashcards in the deck and its sub-decks
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

class Flashcards(db.Model):
    __tablename__ = 'flashcards'  # Explicitly name the table
    flashcard_id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    incorrect_answers = db.Column(JSON, nullable=False)  # Use PostgreSQL JSON type
    flashcard_deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_reviewed = db.Column(db.DateTime)
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
