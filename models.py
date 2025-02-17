from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON  # Add PostgreSQL-specific JSON type

db = SQLAlchemy()

class FlashcardDecks(db.Model):
    __tablename__ = 'flashcard_decks'
    
    flashcard_deck_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    
    # Self-referential foreign key
    parent_deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'), nullable=True)
    
    # Relationship to parent deck
    parent_deck = db.relationship('FlashcardDeck', remote_side=[flashcard_deck_id], backref='child_decks', lazy=True)
    
    flashcards = db.relationship('Flashcard', backref='flashcard_deck', lazy=True)

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
