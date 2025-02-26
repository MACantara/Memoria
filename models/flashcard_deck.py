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

    @staticmethod
    def update_flashcard_progress(flashcard_id, is_correct):
        """
        Atomically update flashcard progress counts using SQL UPDATE
        """
        try:
            if is_correct:
                db.session.execute(
                    text("""
                        UPDATE flashcards 
                        SET correct_count = correct_count + 1,
                            last_reviewed = CURRENT_TIMESTAMP 
                        WHERE flashcard_id = :flashcard_id
                    """),
                    {"flashcard_id": flashcard_id}
                )
            else:
                db.session.execute(
                    text("""
                        UPDATE flashcards 
                        SET incorrect_count = incorrect_count + 1,
                            last_reviewed = CURRENT_TIMESTAMP 
                        WHERE flashcard_id = :flashcard_id
                    """),
                    {"flashcard_id": flashcard_id}
                )
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error updating flashcard progress: {e}")
            return False
