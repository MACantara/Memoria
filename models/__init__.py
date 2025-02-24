from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .flashcard_deck import FlashcardDecks
from .flashcard import Flashcards

__all__ = ['db', 'FlashcardDecks', 'Flashcards']
