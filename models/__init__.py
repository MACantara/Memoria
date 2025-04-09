from flask_sqlalchemy import SQLAlchemy
import os

# Configure SQLAlchemy for both PostgreSQL and SQLite compatibility
db = SQLAlchemy()

# Import models after db initialization
from .flashcard_deck import FlashcardDecks
from .flashcard import Flashcards, FlashcardSet, FlashcardGenerator
from .user import User
from .learning import LearningSession, LearningSection, LearningQuestion

# Import new models
from models.import_models import ImportFile, ImportChunk, ImportFlashcard, ImportTask

# Setup for database compatibility
def setup_db_compatibility():
    """Configure database engine options based on database type"""
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()
    
    # Set SQLite-specific configurations if needed
    if db_type == 'sqlite':
        # Enable SQLite foreign key constraints
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        from sqlite3 import Connection as SQLite3Connection
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, SQLite3Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

# Call the setup function
setup_db_compatibility()

__all__ = ['db', 'FlashcardDecks', 'Flashcards']

# Add to FlashcardDecks class
def to_dict(self):
    """Convert deck to dictionary for API responses"""
    return {
        'id': self.flashcard_deck_id,
        'name': self.name,
        'description': self.description,
        'parent_deck_id': self.parent_deck_id,
        'card_count': len(self.flashcards) if self.flashcards else 0,
        'created_at': self.created_at.isoformat() if self.created_at else None,
    }

# Add to Flashcards class
def to_search_dict(self):
    """Convert flashcard to dictionary for search results"""
    deck_info = {
        'id': self.deck.flashcard_deck_id,
        'name': self.deck.name
    } if hasattr(self, 'deck') else None
    
    return {
        'id': self.flashcard_id,
        'question': self.question,
        'correct_answer': self.correct_answer,
        'deck': deck_info,
        'state': self.state or 0,
        'state_name': self.get_state_name(),
    }
