# Package initialization

# Import all utility functions from utils.py for proper package exports
from utils.utils import (
    # Existing imports
    chunk_text,
    allowed_file,
    clean_flashcard_text,
    is_descendant,
    count_due_flashcards,
    batch_count_due_cards,
    create_pagination_metadata,
    
    # New optimized utility functions
    get_descendant_deck_ids,
    is_descendant_optimized,
    invalidate_deck_caches
)

from typing import List, Optional, Dict
from io import StringIO
import PyPDF2
import math
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time
from flask import current_app
import time
import sqlalchemy
from sqlalchemy import text

# Override the count_due_flashcards function with an optimized version
def count_due_flashcards(deck_id, current_time=None):
    """Count flashcards that are due for a deck and its sub-decks with timeout protection"""
    if current_time is None:
        current_time = get_current_time()
    
    try:
        # First try direct count without recursion - much faster
        direct_count = count_due_flashcards_simple(deck_id, current_time)
        
        # If successful, return the count
        return direct_count
    except Exception as e:
        # If direct count fails, log the error
        current_app.logger.warning(f"Simple due count failed for deck {deck_id}: {str(e)}")
        
        try:
            # Try with recursive CTE but set a timeout
            with db.engine.connect() as conn:
                # Set statement timeout to 2 seconds
                conn.execute(text("SET LOCAL statement_timeout = 2000"))
                
                # Create recursive CTE query
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
                due_count = db.session.query(db.func.count(Flashcards.flashcard_id)).filter(
                    Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id)),
                    (Flashcards.due_date <= current_time) | (Flashcards.due_date == None),
                    Flashcards.state != 2  # Exclude cards already mastered
                ).scalar()
                
                return due_count
        except Exception as e:
            current_app.logger.error(f"Recursive due count failed for deck {deck_id}: {str(e)}")
            # Fall back to a minimal count that at least includes this deck's direct cards
            return count_due_flashcards_fallback(deck_id, current_time)

def count_due_flashcards_simple(deck_id, current_time):
    """Optimized version that avoids recursion for performance but counts accurately"""
    # Get all direct sub-deck IDs using a non-recursive query
    sub_deck_ids = []
    to_process = [deck_id]
    processed = set()
    
    # Simple breadth-first traversal with a limit on iterations
    max_iterations = 100
    iteration = 0
    
    while to_process and iteration < max_iterations:
        iteration += 1
        current_id = to_process.pop(0)
        if current_id in processed:
            continue
            
        processed.add(current_id)
        sub_deck_ids.append(current_id)
        
        # Get immediate children
        children = db.session.query(FlashcardDecks.flashcard_deck_id).filter(
            FlashcardDecks.parent_deck_id == current_id
        ).all()
        
        to_process.extend([child[0] for child in children])
    
    # Now count due cards in these decks
    due_count = Flashcards.query.filter(
        Flashcards.flashcard_deck_id.in_(sub_deck_ids),
        (Flashcards.due_date <= current_time) | (Flashcards.due_date == None),
        Flashcards.state != 2  # Exclude cards already mastered
    ).count()
    
    return due_count

def count_due_flashcards_fallback(deck_id, current_time):
    """Last resort fallback that only counts cards directly in this deck"""
    try:
        due_count = Flashcards.query.filter(
            Flashcards.flashcard_deck_id == deck_id,
            (Flashcards.due_date <= current_time) | (Flashcards.due_date == None),
            Flashcards.state != 2
        ).count()
        return due_count
    except Exception as e:
        current_app.logger.error(f"Fallback due count failed for deck {deck_id}: {str(e)}")
        return 0

# Override batch_count_due_cards with the optimized version
def batch_count_due_cards(deck_ids, user_id):
    """
    Efficiently count due cards for multiple decks at once.
    Returns a dictionary mapping deck_id -> due_count.
    """
    # Create a cache key for the user's counts
    cache_key = f"due_counts_{user_id}"
    
    # Try to get from cache first if caching is enabled
    if hasattr(current_app, 'cache') and current_app.config.get('ENABLE_CACHING', False):
        cached_counts = current_app.cache.get(cache_key)
        if cached_counts:
            # Filter to just the requested deck IDs
            result = {deck_id: cached_counts.get(deck_id, 0) for deck_id in deck_ids}
            return result
    
    # If not cached or no cache available, count for each deck
    result = {}
    for deck_id in deck_ids:
        try:
            result[deck_id] = count_due_flashcards(deck_id)
        except Exception as e:
            current_app.logger.error(f"Error counting due cards for deck {deck_id}: {str(e)}")
            result[deck_id] = 0
    
    # Cache for future use if caching is enabled
    if hasattr(current_app, 'cache') and current_app.config.get('ENABLE_CACHING', False):
        current_app.cache.set(cache_key, result, timeout=300)  # 5 minute cache
    
    return result

# Add exports to __all__ to make these functions accessible when importing from utils
__all__ = [
    'chunk_text',
    'allowed_file',
    'clean_flashcard_text',
    'is_descendant',
    'count_due_flashcards',
    'batch_count_due_cards',
    'create_pagination_metadata',
    'get_descendant_deck_ids',
    'is_descendant_optimized',
    'invalidate_deck_caches',
    'count_due_flashcards_simple',
    'count_due_flashcards_fallback'
]
