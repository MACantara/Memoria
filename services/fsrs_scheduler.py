from datetime import datetime, timedelta, timezone
from fsrs import Scheduler, Card, Rating, ReviewLog, State
import traceback
from models import db  # Add this import at the top
import logging

# Get logger
logger = logging.getLogger(__name__)

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
    try:
        # Get current card state
        fsrs_card = flashcard.get_fsrs_card()
        now = get_current_time()
        
        # Debug the card state before any modifications
        print(f"Processing card {flashcard.flashcard_id} with initial state: step={fsrs_card.step}, state={fsrs_card.state}")
        
        # COMPREHENSIVE INITIALIZATION: Ensure all required fields are properly initialized
        # START WITH STATE-SPECIFIC INITIALIZATION
        
        # For forgotten cards (state 3), step MUST be initialized based on relearning steps
        # This is critical to prevent the '>=' not supported between instances of 'NoneType' and 'int' error
        if int(fsrs_card.state) == 3 and fsrs_card.step is None:
            print(f"Card {flashcard.flashcard_id} is in forgotten state with step=None, initializing to 0")
            fsrs_card.step = 0  # For relearning cards, always start at step 0
        
        # For learning cards (state 1), step is also required
        elif int(fsrs_card.state) == 1 and fsrs_card.step is None:
            print(f"Card {flashcard.flashcard_id} is in learning state with step=None, initializing to 0")
            fsrs_card.step = 0
        
        # General initialization for any other cards with None step
        elif fsrs_card.step is None:
            print(f"Card {flashcard.flashcard_id} has step=None (state={fsrs_card.state}), initializing to 0")
            fsrs_card.step = 0
        
        if fsrs_card.difficulty is None:
            print(f"Card {flashcard.flashcard_id} has difficulty=None, initializing to 0.3 (default)")
            fsrs_card.difficulty = 0.3  # Default difficulty in FSRS
        
        # CRITICAL FIX: stability cannot be zero since FSRS raises it to negative powers
        # Initialize with small positive value to avoid division by zero errors
        if fsrs_card.stability is None or fsrs_card.stability <= 0.0:
            print(f"Card {flashcard.flashcard_id} has stability={fsrs_card.stability}, initializing to 0.1")
            fsrs_card.stability = 0.1  # Small positive value to avoid math errors
        
        # Remember if this was a new card before processing
        was_new_card = (flashcard.state == NEW_STATE)
        
        # If this is a first review of a card in our custom "New" state,
        # change to state 1 (Learning) to work with FSRS algorithm
        if flashcard.state == NEW_STATE:
            print(f"Converting card from New state (0) to Learning state (1)")
            fsrs_card.state = State(1)  # Convert to Learning state
        
        # Final verification of card parameters before processing
        if fsrs_card.step is None:
            print(f"CRITICAL ERROR: Card {flashcard.flashcard_id} still has step=None after initialization!")
            fsrs_card.step = 0  # Force it again as a safeguard
        
        # Determine rating based on correctness
        rating = Rating.Good if is_correct else Rating.Again
        
        # Log the finalized parameters before FSRS processing
        print(f"FSRS: Processing review with rating {rating}, current state: {fsrs_card.state}")
        print(f"Card parameters: step={fsrs_card.step}, difficulty={fsrs_card.difficulty}, stability={fsrs_card.stability}")
        
        # Process with FSRS
        next_card, review_log = scheduler.review_card(fsrs_card, rating, now)
        
        # Update flashcard with new state
        flashcard.fsrs_state = next_card.to_dict()
        flashcard.due_date = next_card.due
        flashcard.state = int(next_card.state)
        flashcard.stability = next_card.stability
        
        # Fix for new cards: If the card was new and answered incorrectly,
        # ensure it goes to Learning (state 1) instead of Forgotten (state 3)
        if flashcard.state == 3 and was_new_card and not is_correct:
            print(f"Fixing state: Card {flashcard.flashcard_id} was new and answered incorrectly, setting to Learning (1) instead of Forgotten (3)")
            flashcard.state = 1
            # Update the fsrs_state to be consistent with the state override
            flashcard.fsrs_state['state'] = 1
            
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

def get_due_cards(deck_id, due_only=False, excluded_ids=None, page=1, per_page=None):
    """
    Get cards that are due for review from a deck and its sub-decks
    
    Args:
        deck_id: The deck ID to fetch cards from
        due_only: Whether to only include cards that are due
        excluded_ids: DEPRECATED - No longer used, kept for backwards compatibility
        page: The page number for pagination (1-based)
        per_page: Number of cards per page, if None returns all cards
    """
    from models import FlashcardDecks, Flashcards
    from sqlalchemy import case
    from sqlalchemy.orm import load_only
    
    # Only log at debug level, not in production
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Starting get_due_cards for deck_id={deck_id}, due_only={due_only}")
    
    # Optimize queries by selecting only needed columns
    query = Flashcards.query.options(
        load_only(
            Flashcards.flashcard_id, 
            Flashcards.question,
            Flashcards.correct_answer,
            Flashcards.incorrect_answers,
            Flashcards.state,
            Flashcards.due_date,
            Flashcards.flashcard_deck_id,
            Flashcards.retrievability
        )
    )
    
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
    
    # Start with a query for all cards in these decks
    query = query.filter(
        Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
    )
    
    # If due_only is True, filter for only cards that are due today
    if due_only:
        current_time = get_current_time()
        query = query.filter(
            (Flashcards.due_date <= current_time) | 
            (Flashcards.due_date == None)  # Include cards without due date
        )
    
    # Removed: Excluded IDs filtering code
    
    # Target counts for each state - we want 15 of each primary state
    target_forgotten = 15
    target_learning = 15
    target_new = 15
    
    # Calculate the total target count (missing variable)
    total_target = target_forgotten + target_learning + target_new
    
    # If we're paginating, adjust targets based on page number
    if per_page is not None:
        # For page 1, use default targets
        # For subsequent pages, adjust proportion of each state
        if page > 1:
            # For later pages, we can change the distribution if needed
            # Here we're keeping it the same
            pass
    
    # Apply pagination at the SQL level if per_page is specified
    if per_page is not None:
        # Calculate offset based on page number (1-based indexing)
        offset = (page - 1) * per_page
        
        # Apply LIMIT and OFFSET to the queries to get paginated results
        forgotten_cards = query.filter(Flashcards.state == 3).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).offset(offset).limit(per_page // 3 + 5).all()  # Add a few extra in case we need them
        
        learning_cards = query.filter(Flashcards.state == 1).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).offset(offset).limit(per_page // 3 + 5).all()
        
        new_cards = query.filter(Flashcards.state == 0).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).offset(offset).limit(per_page // 3 + 5).all()
        
        # For mastered cards, we're less concerned about pagination
        # since they're only used to fill in when there aren't enough other cards
        mastered_cards = query.filter(Flashcards.state == 2).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).limit(per_page // 3).all()
    else:
        # Use existing code for non-paginated queries
        forgotten_cards = query.filter(Flashcards.state == 3).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).all()
        
        learning_cards = query.filter(Flashcards.state == 1).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).all()
        
        new_cards = query.filter(Flashcards.state == 0).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).all()
        
        mastered_cards = query.filter(Flashcards.state == 2).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc(),
            Flashcards.flashcard_id.asc()
        ).all()
    
    # Track available cards for each state
    available_forgotten = len(forgotten_cards)
    available_learning = len(learning_cards)
    available_new = len(new_cards)
    available_mastered = len(mastered_cards)
    
    logger.debug(f"Available cards - Forgotten: {available_forgotten}, Learning: {available_learning}, " +
                f"New: {available_new}, Mastered: {available_mastered}")
    
    # Initialize lists for final selection
    selected_forgotten = []
    selected_learning = []
    selected_new = []
    
    # 1. First, allocate the primary target for each state if available
    selected_forgotten = forgotten_cards[:target_forgotten]
    selected_learning = learning_cards[:target_learning]
    selected_new = new_cards[:target_new]
    
    # Calculate shortfalls
    shortage_forgotten = target_forgotten - len(selected_forgotten)
    shortage_learning = target_learning - len(selected_learning)
    shortage_new = target_new - len(selected_new)
    
    # 2. If there's a shortage in forgotten cards, fill with other types in priority order
    if shortage_forgotten > 0:
        logger.debug(f"Shortage of {shortage_forgotten} forgotten cards, filling with other types")
        
        # First try to fill with learning cards
        learning_for_forgotten = min(shortage_forgotten, max(0, available_learning - len(selected_learning)))
        if learning_for_forgotten > 0:
            additional_learning = learning_cards[len(selected_learning):len(selected_learning) + learning_for_forgotten]
            selected_forgotten.extend(additional_learning)
            shortage_forgotten -= learning_for_forgotten
        
        # Then try to fill with new cards
        if shortage_forgotten > 0:
            new_for_forgotten = min(shortage_forgotten, max(0, available_new - len(selected_new)))
            if new_for_forgotten > 0:
                additional_new = new_cards[len(selected_new):len(selected_new) + new_for_forgotten]
                selected_forgotten.extend(additional_new)
                shortage_forgotten -= new_for_forgotten
        
        # Finally try with mastered cards
        if shortage_forgotten > 0:
            mastered_for_forgotten = min(shortage_forgotten, available_mastered)
            if mastered_for_forgotten > 0:
                selected_forgotten.extend(mastered_cards[:mastered_for_forgotten])
                mastered_cards = mastered_cards[mastered_for_forgotten:]  # Update remaining mastered cards
    
    # 3. If there's a shortage in learning cards, fill with other types in priority order
    if shortage_learning > 0:
        logger.debug(f"Shortage of {shortage_learning} learning cards, filling with other types")
        
        # First try to fill with forgotten cards beyond what we've already used
        forgotten_for_learning = min(shortage_learning, max(0, available_forgotten - len(selected_forgotten)))
        if forgotten_for_learning > 0:
            additional_forgotten = forgotten_cards[len(selected_forgotten):len(selected_forgotten) + forgotten_for_learning]
            selected_learning.extend(additional_forgotten)
            shortage_learning -= forgotten_for_learning
        
        # Then try to fill with new cards
        if shortage_learning > 0:
            new_for_learning = min(shortage_learning, max(0, available_new - len(selected_new)))
            if new_for_learning > 0:
                additional_new = new_cards[len(selected_new):len(selected_new) + new_for_learning]
                selected_learning.extend(additional_new)
                shortage_learning -= new_for_learning
        
        # Finally try with mastered cards
        if shortage_learning > 0:
            mastered_for_learning = min(shortage_learning, len(mastered_cards))
            if mastered_for_learning > 0:
                selected_learning.extend(mastered_cards[:mastered_for_learning])
                mastered_cards = mastered_cards[mastered_for_learning:]  # Update remaining mastered cards
    
    # 4. If there's a shortage in new cards, fill with other types in priority order
    if shortage_new > 0:
        logger.debug(f"Shortage of {shortage_new} new cards, filling with other types")
        
        # First try to fill with forgotten cards beyond what we've already used
        forgotten_for_new = min(shortage_new, max(0, available_forgotten - len(selected_forgotten)))
        if forgotten_for_new > 0:
            additional_forgotten = forgotten_cards[len(selected_forgotten):len(selected_forgotten) + forgotten_for_new]
            selected_new.extend(additional_forgotten)
            shortage_new -= forgotten_for_new
        
        # Then try to fill with learning cards
        if shortage_new > 0:
            learning_for_new = min(shortage_new, max(0, available_learning - len(selected_learning)))
            if learning_for_new > 0:
                additional_learning = learning_cards[len(selected_learning):len(selected_learning) + learning_for_new]
                selected_new.extend(additional_learning)
                shortage_new -= learning_for_new
        
        # Finally try with mastered cards
        if shortage_new > 0:
            mastered_for_new = min(shortage_new, len(mastered_cards))
            if mastered_for_new > 0:
                selected_new.extend(mastered_cards[:mastered_for_new])
                mastered_cards = mastered_cards[mastered_for_new:]  # Update remaining mastered cards
    
    # Combine all cards with a balanced distribution
    balanced_cards = []
    
    # Create an interleaved pattern to mix states
    # We'll alternate between forgotten, learning and new
    max_cards = max(len(selected_forgotten), len(selected_learning), len(selected_new))
    
    for i in range(max_cards):
        if i < len(selected_forgotten):
            balanced_cards.append(selected_forgotten[i])
        if i < len(selected_learning):
            balanced_cards.append(selected_learning[i])
        if i < len(selected_new):
            balanced_cards.append(selected_new[i])
    
    # If we still don't have enough cards to reach our target, add any remaining mastered cards
    if len(balanced_cards) < total_target and len(mastered_cards) > 0:
        balanced_cards.extend(mastered_cards[:total_target - len(balanced_cards)])
    
    # Make sure we don't return more than per_page cards if pagination is enabled
    if per_page is not None and len(balanced_cards) > per_page:
        balanced_cards = balanced_cards[:per_page]
    
    logger.debug(f"get_due_cards returning {len(balanced_cards)} cards for page {page}, per_page {per_page}")
    
    return balanced_cards

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
        # Add these to new cards
        state_counts['new'] += uninitialized_count
    
    # Verify the totals add up correctly
    total = sum(state_counts.values())
    total_cards = query.count()
    
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
