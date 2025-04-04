from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .flashcard_deck import FlashcardDecks
from .flashcard import Flashcards, FlashcardSet, FlashcardGenerator
from .user import User
from .learning import LearningSession, LearningSection, LearningQuestion

# Import new models
from models.import_models import ImportFile, ImportChunk, ImportFlashcard

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
