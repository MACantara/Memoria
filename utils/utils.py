from typing import List, Optional, Dict
from io import StringIO
import PyPDF2
from config import Config
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time
from flask import current_app
import math

def chunk_text(text: str, size: int = Config.CHUNK_SIZE) -> List[str]:
    """Split text into chunks of approximately given size"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        word_size = len(word) + 1
        if current_size + word_size > size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def allowed_file(filename):
    """Check if uploaded file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def clean_flashcard_text(text: str) -> Optional[str]:
    """Clean and format a single flashcard text"""
    if not text or '|' not in text:
        return None
    parts = text.strip().split('|')
    if len(parts) != 2:
        return None
        
    q_part = parts[0].strip()
    a_part = parts[1].strip()
    
    if not q_part.startswith('Q:') or not a_part.startswith('A:'):
        return None
        
    question = q_part[2:].strip()
    answer = a_part[2:].strip()
    
    if not question or not answer:
        return None
        
    return f"Q: {question} | A: {answer}"

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
        result[deck_id] = count_due_flashcards(deck_id)
    
    # Cache for future use if caching is enabled
    if hasattr(current_app, 'cache') and current_app.config.get('ENABLE_CACHING', False):
        current_app.cache.set(cache_key, result, timeout=300)  # 5 minute cache
    
    return result

# Pagination helper - moved from utils/pagination.py for consolidated utility functions
def create_pagination_metadata(page, per_page, total_items, endpoint_args=None):
    """Helper function to create consistent pagination metadata"""
    # Calculate number of pages
    pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    
    # Ensure page is within valid range
    page = max(1, min(page, pages))
    
    # Calculate start and end indexes for display
    start_idx = (page - 1) * per_page + 1 if total_items > 0 else 0
    end_idx = min(start_idx + per_page - 1, total_items)
    
    # Calculate page range (show 5 pages around current page)
    page_range_radius = 2
    page_range_start = max(1, page - page_range_radius)
    page_range_end = min(pages, page + page_range_radius)
    
    # Ensure we always show at least 5 pages when possible
    if page_range_end - page_range_start + 1 < min(5, pages):
        if page_range_start == 1:
            page_range_end = min(5, pages)
        elif page_range_end == pages:
            page_range_start = max(1, pages - 4)
    
    # Other args to preserve in pagination links
    other_args = endpoint_args or {}
    if 'page' in other_args:
        other_args.pop('page')
        
    return {
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'total': total_items,
        'has_prev': page > 1,
        'has_next': page < pages,
        'start_idx': start_idx,
        'end_idx': end_idx,
        'page_range_start': page_range_start,
        'page_range_end': page_range_end,
        'other_args': other_args
    }
