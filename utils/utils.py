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
    Efficiently count due cards for multiple decks at once with optimized query.
    Returns a dictionary mapping deck_id -> due_count.
    """
    # Create a cache key for the user's counts
    cache_key = f"due_counts_{user_id}"
    
    # Try to get from cache first if caching is enabled
    if hasattr(current_app, 'cache') and current_app.cache:
        cached_counts = current_app.cache.get(cache_key)
        if cached_counts:
            # Filter to just the requested deck IDs
            result = {deck_id: cached_counts.get(str(deck_id), 0) for deck_id in deck_ids}
            return result
    
    # If not cached or no cache available, use a single optimized query
    result = {deck_id: 0 for deck_id in deck_ids}  # Initialize all with 0
    current_time = get_current_time()  # Get current time once for all decks
    
    # Use a single query to get all due counts
    due_counts_query = """
    WITH RECURSIVE subdeck(id, parent_id, root_id) AS (
        SELECT d.flashcard_deck_id, d.parent_deck_id, d.flashcard_deck_id
        FROM flashcard_decks d
        WHERE d.flashcard_deck_id = ANY(:deck_ids)
        UNION ALL
        SELECT d.flashcard_deck_id, d.parent_deck_id, s.root_id
        FROM flashcard_decks d
        JOIN subdeck s ON d.parent_deck_id = s.id
    )
    SELECT s.root_id, COUNT(f.flashcard_id)
    FROM subdeck s
    JOIN flashcards f ON f.flashcard_deck_id = s.id
    WHERE (f.due_date <= :current_time OR f.due_date IS NULL)
      AND f.state != 2
    GROUP BY s.root_id
    """
    
    # Execute the query with parameters
    try:
        counts = db.session.execute(
            due_counts_query, 
            {"deck_ids": deck_ids, "current_time": current_time}
        ).fetchall()
        
        # Update with actual counts
        for root_id, count in counts:
            result[root_id] = count
            
    except Exception as e:
        current_app.logger.error(f"Error in batch_count_due_cards: {str(e)}")
        # Fall back to individual counts if the optimized query fails
        for deck_id in deck_ids:
            result[deck_id] = count_due_flashcards(deck_id, current_time)
    
    # Cache for future use if caching is enabled
    if hasattr(current_app, 'cache') and current_app.cache:
        current_app.cache.set(cache_key, result, timeout=300)  # 5 minute cache
    
    return result

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

# Add descendant deck ID retrieval with caching
def get_descendant_deck_ids(deck_id):
    """Get all descendant deck IDs with caching"""
    cache_key = f"deck_descendants:{deck_id}"
    
    # Try to get from cache
    if hasattr(current_app, 'cache') and current_app.cache:
        cached_ids = current_app.cache.get(cache_key)
        if cached_ids:
            return cached_ids
    
    # Not in cache, fetch from database
    # Create recursive CTE to find all sub-decks
    cte = db.session.query(
        FlashcardDecks.flashcard_deck_id.label('id')
    ).filter(
        FlashcardDecks.flashcard_deck_id == deck_id
    ).cte(name='sub_decks', recursive=True)

    cte = cte.union_all(
        db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == cte.c.id
        )
    )

    # Get all deck IDs including the parent
    all_deck_ids = [deck_id]  # Include the parent deck ID
    all_deck_ids.extend([row[0] for row in db.session.query(cte.c.id).all()])
    
    # Cache the result for future use
    if hasattr(current_app, 'cache') and current_app.cache:
        current_app.cache.set(cache_key, all_deck_ids, timeout=3600)  # Cache for 1 hour
    
    return all_deck_ids

# Add optimized descendant check for hierarchy operations
def is_descendant_optimized(potential_descendant_id, ancestor_id):
    """More efficient check if a deck is a descendant of another deck"""
    if potential_descendant_id == ancestor_id:
        return True
    
    # Get all descendants of the ancestor
    descendant_ids = get_descendant_deck_ids(ancestor_id)
    
    # Check if potential descendant is in the list
    return potential_descendant_id in descendant_ids

# Add function to invalidate deck caches when structure changes
def invalidate_deck_caches(deck_id):
    """Invalidate cached data for a deck and its descendants"""
    if not hasattr(current_app, 'cache') or not current_app.cache:
        return
    
    # Get all descendants
    descendant_ids = get_descendant_deck_ids(deck_id)
    
    # Invalidate caches for all affected decks
    for d_id in descendant_ids:
        current_app.cache.delete(f"deck_descendants:{d_id}")
        current_app.cache.delete(f"deck_stats:{d_id}")
        current_app.cache.delete(f"deck_retention:{d_id}")
        current_app.cache.delete(f"deck_flashcards:{d_id}")
        
        # Also invalidate upcoming reviews cache with various page sizes
        for page in range(1, 6):  # First 5 pages of each size
            for per_page in [20, 50, 100]:
                current_app.cache.delete(f"upcoming_reviews:{d_id}:{page}:{per_page}")
