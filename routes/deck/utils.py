from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time

def is_descendant(potential_descendant_id, ancestor_id):
    """Check if a deck is a descendant of another deck"""
    if potential_descendant_id == ancestor_id:
        return True
        
    deck = FlashcardDecks.query.get(potential_descendant_id)
    if not deck:
        return False
    
    # If this deck has no parent, it can't be a descendant
    if deck.parent_deck_id is None:
        return False
        
    # Check if the parent is the ancestor we're looking for
    if deck.parent_deck_id == ancestor_id:
        return True
        
    # Recursively check the parent
    return is_descendant(deck.parent_deck_id, ancestor_id)

def count_due_flashcards(deck_id, current_time=None):
    """Count flashcards that are due for a deck and its sub-decks"""
    if current_time is None:
        current_time = get_current_time()
    
    # Create recursive CTE to find all decks including this one and its sub-decks
    cte = db.session.query(
        FlashcardDecks.flashcard_deck_id.label('id')
    ).filter(
        FlashcardDecks.flashcard_deck_id == deck_id
    ).cte(name='due_decks', recursive=True)

    cte = cte.union_all(
        db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == cte.c.id
        )
    )
    
    # Count cards that are due now, but exclude cards already in "mastered" state (2) 
    # even if they have a due date in the past
    due_count = Flashcards.query.filter(
        Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id)),
        (Flashcards.due_date <= current_time) | (Flashcards.due_date == None),
        Flashcards.state != 2  # Exclude cards already mastered
    ).count()
    
    return due_count
