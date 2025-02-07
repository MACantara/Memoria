from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON  # Add PostgreSQL-specific JSON type

db = SQLAlchemy()

class Topic(db.Model):
    __tablename__ = 'topics'  # Explicitly name the table
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    flashcards = db.relationship('Flashcard', backref='topic', lazy=True)
    decks = db.relationship('Deck', backref='topic', lazy=True)

class Deck(db.Model):
    __tablename__ = 'decks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    flashcards = db.relationship('Flashcard', backref='deck', lazy=True)

class Flashcard(db.Model):
    __tablename__ = 'flashcards'  # Explicitly name the table
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    incorrect_answers = db.Column(JSON, nullable=False)  # Use PostgreSQL JSON type
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_reviewed = db.Column(db.DateTime)
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
