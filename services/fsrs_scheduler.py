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
    
    print(f"DEBUG: Starting get_due_cards for deck_id={deck_id}, due_only={due_only}")
    
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
    print(f"DEBUG: Total cards in all decks: {total_cards}")
    
    # If due_only is True, filter for only cards that are due today
    if due_only:
        current_time = get_current_time()
        query = query.filter(
            (Flashcards.due_date <= current_time) | 
            (Flashcards.due_date == None)  # Include cards without due date
        )
        print(f"DEBUG: Due cards: {query.count()} (out of {total_cards})")
    
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
    
    # Debug card counts by state with detailed information
    print(f"DEBUG: Cards by state - New: {len(new_cards)}, Learning: {len(learning_cards)}, "
          f"Mastered: {len(mastered_cards)}, Forgotten: {len(forgotten_cards)}")
    
    # Print first few cards of each type to verify sorting
    if new_cards:
        print(f"DEBUG: First new card: id={new_cards[0].flashcard_id}, due={new_cards[0].due_date}")
    if learning_cards:
        print(f"DEBUG: First learning card: id={learning_cards[0].flashcard_id}, due={learning_cards[0].due_date}")
    if forgotten_cards:
        print(f"DEBUG: First forgotten card: id={forgotten_cards[0].flashcard_id}, due={forgotten_cards[0].due_date}")
    
    # Create balanced segments of 25 cards with the desired ratio
    # Target: 5 forgotten, 5 learning, 10 new, 5 mastered per segment
    balanced_cards = []
    
    # Calculate how many segments we need
    total_available_cards = len(new_cards) + len(learning_cards) + len(forgotten_cards) + len(mastered_cards)
    segment_size = 25
    num_segments = max(1, (total_available_cards + segment_size - 1) // segment_size)
    
    print(f"DEBUG: Creating {num_segments} segments of {segment_size} cards each")
    print(f"DEBUG: Total available cards: {total_available_cards}")
    
    # Track indices to avoid repeating cards
    new_index = 0
    learning_index = 0 
    forgotten_index = 0
    mastered_index = 0
    
    # Create segments
    for segment in range(num_segments):
        print(f"\nDEBUG: Building segment {segment+1}/{num_segments}")
        print(f"DEBUG: Current indices - forgotten: {forgotten_index}/{len(forgotten_cards)}, "
              f"learning: {learning_index}/{len(learning_cards)}, "
              f"new: {new_index}/{len(new_cards)}, "
              f"mastered: {mastered_index}/{len(mastered_cards)}")
              
        # Create a new segment with cards in the specified order
        segment_cards = []
        segment_debug_info = {0: 0, 1: 0, 2: 0, 3: 0}  # Count by state for debugging
        
        # First part: Add forgotten cards (target: 5)
        forgotten_to_add = min(5, len(forgotten_cards) - forgotten_index)
        print(f"DEBUG: Adding {forgotten_to_add} forgotten cards (target: 5)")
        for i in range(forgotten_index, forgotten_index + forgotten_to_add):
            segment_cards.append(forgotten_cards[i])
            segment_debug_info[3] += 1
        forgotten_index += forgotten_to_add
        
        # If we don't have enough forgotten cards, backfill with other types
        remaining_forgotten = 5 - forgotten_to_add
        
        if remaining_forgotten > 0:
            print(f"DEBUG: Backfilling {remaining_forgotten} forgotten slots")
            
            # Backfill priority: learning -> new -> mastered
            # Try learning cards first
            learning_backfill = min(remaining_forgotten, len(learning_cards) - learning_index)
            print(f"DEBUG: Backfilling with {learning_backfill} learning cards")
            for i in range(learning_index, learning_index + learning_backfill):
                segment_cards.append(learning_cards[i])
                segment_debug_info[1] += 1
            learning_index += learning_backfill
            remaining_forgotten -= learning_backfill
            
            # Then try new cards
            new_backfill = min(remaining_forgotten, len(new_cards) - new_index)
            print(f"DEBUG: Backfilling with {new_backfill} new cards")
            for i in range(new_index, new_index + new_backfill):
                segment_cards.append(new_cards[i])
                segment_debug_info[0] += 1
            new_index += new_backfill
            remaining_forgotten -= new_backfill
            
            # Finally mastered cards
            mastered_backfill = min(remaining_forgotten, len(mastered_cards) - mastered_index)
            print(f"DEBUG: Backfilling with {mastered_backfill} mastered cards")
            for i in range(mastered_index, mastered_index + mastered_backfill):
                segment_cards.append(mastered_cards[i])
                segment_debug_info[2] += 1
            mastered_index += mastered_backfill
        
        # Second part: Add learning cards (target: 5)
        learning_to_add = min(5, len(learning_cards) - learning_index)
        print(f"DEBUG: Adding {learning_to_add} learning cards (target: 5)")
        for i in range(learning_index, learning_index + learning_to_add):
            segment_cards.append(learning_cards[i])
            segment_debug_info[1] += 1
        learning_index += learning_to_add
        
        # Backfill if needed
        remaining_learning = 5 - learning_to_add
        
        if remaining_learning > 0:
            print(f"DEBUG: Backfilling {remaining_learning} learning slots")
            
            # Backfill priority: new -> forgotten -> mastered
            # Try new cards first
            new_backfill = min(remaining_learning, len(new_cards) - new_index)
            print(f"DEBUG: Backfilling with {new_backfill} new cards")
            for i in range(new_index, new_index + new_backfill):
                segment_cards.append(new_cards[i])
                segment_debug_info[0] += 1
            new_index += new_backfill
            remaining_learning -= new_backfill
            
            # Then try forgotten cards
            forgotten_backfill = min(remaining_learning, len(forgotten_cards) - forgotten_index)
            print(f"DEBUG: Backfilling with {forgotten_backfill} forgotten cards")
            for i in range(forgotten_index, forgotten_index + forgotten_backfill):
                segment_cards.append(forgotten_cards[i])
                segment_debug_info[3] += 1
            forgotten_index += forgotten_backfill
            remaining_learning -= forgotten_backfill
            
            # Finally mastered cards
            mastered_backfill = min(remaining_learning, len(mastered_cards) - mastered_index)
            print(f"DEBUG: Backfilling with {mastered_backfill} mastered cards")
            for i in range(mastered_index, mastered_index + mastered_backfill):
                segment_cards.append(mastered_cards[i])
                segment_debug_info[2] += 1
            mastered_index += mastered_backfill
        
        # Third part: Add new cards (target: 10)
        new_to_add = min(10, len(new_cards) - new_index)
        print(f"DEBUG: Adding {new_to_add} new cards (target: 10)")
        for i in range(new_index, new_index + new_to_add):
            segment_cards.append(new_cards[i])
            segment_debug_info[0] += 1
        new_index += new_to_add
        
        # Backfill if needed
        remaining_new = 10 - new_to_add
        
        if remaining_new > 0:
            print(f"DEBUG: Backfilling {remaining_new} new slots")
            
            # Backfill priority: learning -> forgotten -> mastered
            # Try learning cards first
            learning_backfill = min(remaining_new, len(learning_cards) - learning_index)
            print(f"DEBUG: Backfilling with {learning_backfill} learning cards")
            for i in range(learning_index, learning_index + learning_backfill):
                segment_cards.append(learning_cards[i])
                segment_debug_info[1] += 1
            learning_index += learning_backfill
            remaining_new -= learning_backfill
            
            # Then try forgotten cards
            forgotten_backfill = min(remaining_new, len(forgotten_cards) - forgotten_index)
            print(f"DEBUG: Backfilling with {forgotten_backfill} forgotten cards")
            for i in range(forgotten_index, forgotten_index + forgotten_backfill):
                segment_cards.append(forgotten_cards[i])
                segment_debug_info[3] += 1
            forgotten_index += forgotten_backfill
            remaining_new -= forgotten_backfill
            
            # Finally mastered cards
            mastered_backfill = min(remaining_new, len(mastered_cards) - mastered_index)
            print(f"DEBUG: Backfilling with {mastered_backfill} mastered cards")
            for i in range(mastered_index, mastered_index + mastered_backfill):
                segment_cards.append(mastered_cards[i])
                segment_debug_info[2] += 1
            mastered_index += mastered_backfill
        
        # Fourth part: Add remaining cards to fill segment (target: 5, usually mastered)
        remaining_slots = segment_size - len(segment_cards)
        
        # Fill with mastered cards first
        mastered_to_add = min(remaining_slots, len(mastered_cards) - mastered_index)
        print(f"DEBUG: Adding {mastered_to_add} mastered cards (target: 5)")
        for i in range(mastered_index, mastered_index + mastered_to_add):
            segment_cards.append(mastered_cards[i])
            segment_debug_info[2] += 1
        mastered_index += mastered_to_add
        remaining_slots -= mastered_to_add
        
        # If we still need cards, use any remaining cards from any state
        if remaining_slots > 0:
            print(f"DEBUG: Filling {remaining_slots} remaining slots with any available cards")
            
            # Try new cards
            new_fill = min(remaining_slots, len(new_cards) - new_index)
            print(f"DEBUG: Filling with {new_fill} new cards")
            for i in range(new_index, new_index + new_fill):
                segment_cards.append(new_cards[i])
                segment_debug_info[0] += 1
            new_index += new_fill
            remaining_slots -= new_fill
            
            # Try learning cards
            learning_fill = min(remaining_slots, len(learning_cards) - learning_index)
            print(f"DEBUG: Filling with {learning_fill} learning cards")
            for i in range(learning_index, learning_index + learning_fill):
                segment_cards.append(learning_cards[i])
                segment_debug_info[1] += 1
            learning_index += learning_fill
            remaining_slots -= learning_fill
            
            # Try forgotten cards
            forgotten_fill = min(remaining_slots, len(forgotten_cards) - forgotten_index)
            print(f"DEBUG: Filling with {forgotten_fill} forgotten cards")
            for i in range(forgotten_index, forgotten_index + forgotten_fill):
                segment_cards.append(forgotten_cards[i])
                segment_debug_info[3] += 1
            forgotten_index += forgotten_fill
        
        # If we have no cards in this segment, we're done
        if not segment_cards:
            print("DEBUG: No cards for this segment, breaking")
            break
            
        # Print the segment summary
        print(f"DEBUG: Segment {segment+1} composition:")
        print(f"DEBUG: - New cards (state 0): {segment_debug_info[0]}")
        print(f"DEBUG: - Learning cards (state 1): {segment_debug_info[1]}")
        print(f"DEBUG: - Mastered cards (state 2): {segment_debug_info[2]}")
        print(f"DEBUG: - Forgotten cards (state 3): {segment_debug_info[3]}")
        print(f"DEBUG: - Total cards in segment: {len(segment_cards)}")
        
        # Debug the first few cards in this segment
        if segment_cards:
            print("DEBUG: First 5 cards in this segment (id, state):")
            for i, card in enumerate(segment_cards[:5]):
                print(f"DEBUG:   {i+1}. id={card.flashcard_id}, state={card.state}")
            
        # Add this segment's cards to the final list
        balanced_cards.extend(segment_cards)
        
        # If we've used all cards, break
        if (new_index >= len(new_cards) and 
            learning_index >= len(learning_cards) and 
            forgotten_index >= len(forgotten_cards) and
            mastered_index >= len(mastered_cards)):
            print("DEBUG: All cards used, breaking")
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
