from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .flashcard_deck import FlashcardDecks
from .flashcard import Flashcards, FlashcardSet, FlashcardGenerator

__all__ = ['db', 'FlashcardDecks', 'Flashcards']
