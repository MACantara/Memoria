from datetime import datetime, timedelta, timezone
from fsrs import Scheduler, Card, Rating, ReviewLog, State
import traceback
from models import db  # Add this import at the top

# We MUST use UTC timezone for FSRS
def get_current_time():
    """Get current time with UTC timezone (required by FSRS)"""
    return datetime.now(timezone.utc)

# Create a custom state constant for our "New" state
NEW_STATE = 0  # Custom state to represent unreviewed cards

# Initialize scheduler with optimized parameters
scheduler = Scheduler(
    parameters=(
        0.40255, 1.18385, 3.173, 15.69105, 7.1949, 0.5345, 1.4604, 0.0046, 
        1.54575, 0.1192, 1.01925, 1.9395, 0.11, 0.29605, 2.2698, 
        0.2315, 2.9898, 0.51655, 0.6621,
    ),
    desired_retention=0.9,
    learning_steps=(timedelta(minutes=1), timedelta(minutes=10)),
    relearning_steps=(timedelta(minutes=10),),
    maximum_interval=365,
    enable_fuzzing=True
)

def get_scheduler():
    """Get FSRS scheduler instance"""
    return scheduler

def convert_rating(is_correct):
    """Convert binary correct/incorrect to FSRS ratings"""
    return Rating.Good if is_correct else Rating.Again

def process_review(flashcard, is_correct):
    """Process a review for a flashcard"""
    # Note: No need to import db here since it's now imported at the module level
    
    try:
        # Get current card state
        fsrs_card = flashcard.get_fsrs_card()
        now = get_current_time()
        
        # If this is a first review of a card in our custom "New" state,
        # change to state 1 (Learning) to work with FSRS algorithm
        if flashcard.state == NEW_STATE:
            print(f"Converting card from New state (0) to Learning state (1)")
            fsrs_card.state = State(1)  # Convert to Learning state
        
        # Determine rating based on correctness
        rating = Rating.Good if is_correct else Rating.Again
        
        print(f"FSRS: Processing review with rating {rating}, current state: {fsrs_card.state}")
        
        # Process with FSRS
        next_card, review_log = scheduler.review_card(fsrs_card, rating, now)
        
        # Update flashcard with new state
        flashcard.fsrs_state = next_card.to_dict()
        flashcard.due_date = next_card.due
        flashcard.state = int(next_card.state)
        flashcard.stability = next_card.stability
        flashcard.difficulty = next_card.difficulty
        flashcard.retrievability = next_card.get_retrievability() or 0.0
        
        flashcard.last_reviewed = now
        
        # Save to database
        db.session.add(flashcard)
        db.session.commit()
        
        return flashcard.due_date, flashcard.retrievability
        
    except Exception as e:
        print(f"Error in process_review: {e}")
        print(traceback.format_exc())
        
        # Simple fallback if FSRS fails
        now = get_current_time()
        flashcard.last_reviewed = now
            
        db.session.add(flashcard)
        db.session.commit()
        
        return flashcard.due_date, 0.0

def get_due_cards(deck_id, due_only=False):
    """
    Get cards that are due for review from a deck and its sub-decks.
    
    Args:
        deck_id: The ID of the deck to get cards from.
        due_only: If True, only return cards that are due for review today.
                 If False, return all cards regardless of due date.
    
    Returns:
        A list of Flashcards objects that are due for review.
    """
    from models import FlashcardDecks, Flashcards
    from sqlalchemy import case
    
    # Create recursive CTE to find all decks including this one and its sub-decks
    cte = db.session.query(
        FlashcardDecks.flashcard_deck_id.label('id')
    ).filter(
        FlashcardDecks.flashcard_deck_id == deck_id
    ).cte(name='study_decks', recursive=True)

    cte = cte.union_all(
        db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == cte.c.id
        )
    )
    
    # Debug to check the CTE query
    deck_ids = [row[0] for row in db.session.query(cte.c.id).all()]
    print(f"Found {len(deck_ids)} decks in tree including deck {deck_id}")
    
    # Start with a query for all cards in these decks
    query = Flashcards.query.filter(
        Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
    )
    
    # Debug
    total_cards = query.count()
    print(f"Total cards in all decks: {total_cards}")
    
    # If due_only is True, filter for only cards that are due today
    if due_only:
        current_time = get_current_time()
        query = query.filter(
            (Flashcards.due_date <= current_time) | 
            (Flashcards.due_date == None)  # Include cards without due date
        )
        print(f"Due cards: {query.count()} (out of {total_cards})")
    
    # Order by due date (earliest first), with None values at the beginning
    # Updated to use SQLAlchemy's newer case syntax
    flashcards = query.order_by(
        # Put cards without due date first - FIXED CASE EXPRESSION
        case((Flashcards.due_date == None, 0), else_=1),
        # Then order by due date (earliest first)
        Flashcards.due_date.asc(),
        # Finally by ID to ensure stable ordering
        Flashcards.flashcard_id.asc()
    ).all()
    
    return flashcards

def get_stats(deck_id=None):
    """
    Get FSRS stats for a deck or all decks
    
    Args:
        deck_id: Optional deck ID to filter by
        
    Returns:
        Dictionary of stats
    """
    from models import FlashcardDecks, Flashcards
    from sqlalchemy import func
    
    query = Flashcards.query
    
    if deck_id:
        # Use recursive CTE to find all nested sub-decks
        cte = db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.flashcard_deck_id == deck_id
        ).cte(name='study_decks', recursive=True)

        cte = cte.union_all(
            db.session.query(
                FlashcardDecks.flashcard_deck_id.label('id')
            ).filter(
                FlashcardDecks.parent_deck_id == cte.c.id
            )
        )
        
        query = query.filter(Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id)))
    
    # Count cards by state - be more explicit with filtering conditions
    state_counts = {
        'new': query.filter(Flashcards.state == 0).count(),
        'learning': query.filter(Flashcards.state == 1).count(),
        'mastered': query.filter(Flashcards.state == 2).count(),
        'forgotten': query.filter(Flashcards.state == 3).count()
    }
    
    # Add a check for cards with uninitialized state
    uninitialized_count = query.filter(Flashcards.state.is_(None)).count()
    if uninitialized_count > 0:
        print(f"Warning: Found {uninitialized_count} cards with NULL state")
        # Add these to new cards
        state_counts['new'] += uninitialized_count
    
    # Verify the totals add up correctly
    total = sum(state_counts.values())
    total_cards = query.count()
    if total != total_cards:
        print(f"Warning: State counts ({total}) don't match total cards ({total_cards})")
    
    # Count due cards - use timezone-aware datetime
    now = get_current_time()
    due_count = query.filter(Flashcards.due_date <= now).count()
    
    # Calculate average retrievability only for cards that have been reviewed
    reviewed_cards = query.filter(
        Flashcards.retrievability > 0,
        Flashcards.last_reviewed.isnot(None)  # Only include cards that have been reviewed
    )
    
    reviewed_count = reviewed_cards.count()
    
    # Calculate percentage of cards reviewed
    review_coverage = (reviewed_count / total_cards * 100) if total_cards > 0 else 0
    
    # Only calculate average retention if there are actually reviewed cards
    # and at least 10% of cards have been reviewed
    if reviewed_count > 0:
        avg_retrievability = db.session.query(
            func.avg(Flashcards.retrievability)
        ).filter(
            Flashcards.retrievability > 0,
            Flashcards.last_reviewed.isnot(None)
        ).scalar() or 0
    else:
        # No review history available
        avg_retrievability = None
    
    # Get upcoming reviews - include already due cards too
    upcoming = {}
    
    # First add today's due cards
    today = now.date()
    today_count = query.filter(
        Flashcards.due_date <= now
    ).count()
    
    if today_count > 0:
        upcoming[today] = today_count
    
    # Then add upcoming cards for the next week
    next_week = now + timedelta(days=7)
    future_reviews = query.filter(
        Flashcards.due_date > now,
        Flashcards.due_date <= next_week
    ).all()
    
    for card in future_reviews:
        # Extract just the date part
        due_date = card.due_date.date()
        upcoming[due_date] = upcoming.get(due_date, 0) + 1
    
    # Format for JSON response
    formatted_upcoming = [
        {'date': date.isoformat(), 'count': count}
        for date, count in sorted(upcoming.items())
    ]
    
    print(f"Upcoming reviews: {formatted_upcoming}")  # Debug info
    
    return {
        'total_cards': total_cards,
        'due_count': due_count,
        'reviewed_count': reviewed_count,
        'review_coverage': round(review_coverage, 1),  # Percentage of cards reviewed
        'average_retention': float(avg_retrievability) if avg_retrievability is not None else None,
        'has_retention_data': reviewed_count > 0,
        'has_significant_retention_data': reviewed_count >= 20 or (total_cards > 0 and review_coverage >= 10),
        'state_counts': state_counts,
        'upcoming_reviews': formatted_upcoming
    }
