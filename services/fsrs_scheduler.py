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

def get_due_cards(deck_id, due_only=False):
    """
    Get cards that are due for review from a deck and its sub-decks,
    with a balanced distribution of card states.
    
    Args:
        deck_id: The ID of the deck to get cards from.
        due_only: If True, only return cards that are due for review today.
                 If False, return all cards regardless of due date.
    
    Returns:
        A list of Flashcards objects with balanced states.
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
    
    # Fetch cards for each state separately with proper ordering within each state
    new_cards = query.filter(Flashcards.state == 0).order_by(
        case((Flashcards.due_date == None, 0), else_=1),
        Flashcards.due_date.asc(),
        Flashcards.flashcard_id.asc()
    ).all()
    
    learning_cards = query.filter(Flashcards.state == 1).order_by(
        case((Flashcards.due_date == None, 0), else_=1),
        Flashcards.due_date.asc(),
        Flashcards.flashcard_id.asc()
    ).all()
    
    mastered_cards = query.filter(Flashcards.state == 2).order_by(
        case((Flashcards.due_date == None, 0), else_=1),
        Flashcards.due_date.asc(),
        Flashcards.flashcard_id.asc()
    ).all()
    
    forgotten_cards = query.filter(Flashcards.state == 3).order_by(
        case((Flashcards.due_date == None, 0), else_=1),
        Flashcards.due_date.asc(),
        Flashcards.flashcard_id.asc()
    ).all()
    
    # Log card counts by state
    print(f"Cards by state - New: {len(new_cards)}, Learning: {len(learning_cards)}, "
          f"Mastered: {len(mastered_cards)}, Forgotten: {len(forgotten_cards)}")
    
    # Create balanced segments of 25 cards with the desired ratio
    # Target: 10 new, 5 learning, 5 forgotten, 5 others per segment
    balanced_cards = []
    
    # Calculate how many segments we need
    total_available_cards = len(new_cards) + len(learning_cards) + len(forgotten_cards) + len(mastered_cards)
    segment_size = 25
    num_segments = max(1, (total_available_cards + segment_size - 1) // segment_size)
    
    # Track indices to avoid repeating cards
    new_index = 0
    learning_index = 0 
    forgotten_index = 0
    mastered_index = 0
    
    # Create segments
    for segment in range(num_segments):
        segment_cards = []
        
        # Try to add 5 forgotten cards or as many as available
        for _ in range(5):
            if forgotten_index < len(forgotten_cards):
                segment_cards.append(forgotten_cards[forgotten_index])
                forgotten_index += 1
            elif learning_index < len(learning_cards):  # Backfill with learning cards
                segment_cards.append(learning_cards[learning_index])
                learning_index += 1
            elif new_index < len(new_cards):  # Backfill with new cards
                segment_cards.append(new_cards[new_index])
                new_index += 1
            elif mastered_index < len(mastered_cards):  # Backfill with mastered cards
                segment_cards.append(mastered_cards[mastered_index])
                mastered_index += 1
        
        # Try to add 5 learning cards or as many as available
        for _ in range(5):
            if learning_index < len(learning_cards):
                segment_cards.append(learning_cards[learning_index])
                learning_index += 1
            elif new_index < len(new_cards):  # Backfill with new cards
                segment_cards.append(new_cards[new_index])
                new_index += 1
            elif forgotten_index < len(forgotten_cards):  # Backfill with forgotten cards
                segment_cards.append(forgotten_cards[forgotten_index])
                forgotten_index += 1
            elif mastered_index < len(mastered_cards):  # Backfill with mastered cards
                segment_cards.append(mastered_cards[mastered_index])
                mastered_index += 1
        
        # Try to add 10 new cards or as many as available
        for _ in range(10):
            if new_index < len(new_cards):
                segment_cards.append(new_cards[new_index])
                new_index += 1
            elif learning_index < len(learning_cards):  # Backfill with learning cards
                segment_cards.append(learning_cards[learning_index])
                learning_index += 1
            elif forgotten_index < len(forgotten_cards):  # Backfill with forgotten cards
                segment_cards.append(forgotten_cards[forgotten_index])
                forgotten_index += 1
            elif mastered_index < len(mastered_cards):  # Backfill with mastered cards
                segment_cards.append(mastered_cards[mastered_index])
                mastered_index += 1
        
        # Fill remaining slots with mastered cards or other available cards
        remaining_slots = segment_size - len(segment_cards)
        for _ in range(remaining_slots):
            if mastered_index < len(mastered_cards):
                segment_cards.append(mastered_cards[mastered_index])
                mastered_index += 1
            elif new_index < len(new_cards):
                segment_cards.append(new_cards[new_index])
                new_index += 1
            elif learning_index < len(learning_cards):
                segment_cards.append(learning_cards[learning_index])
                learning_index += 1
            elif forgotten_index < len(forgotten_cards):
                segment_cards.append(forgotten_cards[forgotten_index])
                forgotten_index += 1
        
        # If we've reached the end of all card types, break out
        if not segment_cards:
            break
            
        # Add this segment's cards to the final list
        balanced_cards.extend(segment_cards)
        
        # If we've used all cards, break
        if (new_index >= len(new_cards) and 
            learning_index >= len(learning_cards) and 
            forgotten_index >= len(forgotten_cards) and
            mastered_index >= len(mastered_cards)):
            break
    
    # Log final card distribution for debugging
    final_states = {}
    for card in balanced_cards:
        state = card.state or 0
        final_states[state] = final_states.get(state, 0) + 1
    
    print(f"Balanced card count: {len(balanced_cards)}")
    print(f"Final distribution by state: {final_states}")
    
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
