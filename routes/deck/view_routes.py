from flask import Blueprint, request, render_template
from models import FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_due_cards, get_current_time
from routes.deck.utils import count_due_flashcards

deck_view_bp = Blueprint('deck_view', __name__)

@deck_view_bp.route("/<int:deck_id>")
def get_deck_flashcards(deck_id):
    """View deck structure and its contents"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id).all()
    
    # Count due flashcards for this deck (including sub-decks)
    current_time = get_current_time()
    due_count = count_due_flashcards(deck_id, current_time)
    
    return render_template("deck.html", deck=deck, flashcards=flashcards, due_count=due_count)

@deck_view_bp.route("/<int:deck_id>/study")
def study_deck(deck_id):
    """Study flashcards in this deck and all nested sub-decks using FSRS scheduling"""
    from models import db  # Import here to avoid circular imports
    
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if we should only get due cards
    due_only = request.args.get('due_only', 'false').lower() == 'true'
    
    # Debug log
    print(f"Study request for deck {deck_id}: due_only={due_only}")
    
    # Get cards based on the due_only parameter
    if due_only:
        flashcards = get_due_cards(deck_id, due_only=True)
        print(f"Retrieved {len(flashcards)} due cards for study")
    else:
        flashcards = get_due_cards(deck_id, due_only=False)
        print(f"Retrieved {len(flashcards)} total cards for study")
    
    # Initialize FSRS state and due dates for any cards that need it
    if flashcards:
        current_time = get_current_time()
        for card in flashcards:
            # If card doesn't have FSRS state or state is None, initialize it
            if not card.fsrs_state or card.state is None:
                print(f"Initializing FSRS state for card {card.flashcard_id}")
                card.init_fsrs_state()
            
            # If card doesn't have a due date, make it due now
            if card.due_date is None:
                card.due_date = current_time
        
        db.session.commit()
    
    # Get parent deck information for each card to display subdeck names
    deck_info = {}
    for card in flashcards:
        if card.flashcard_deck_id != deck_id:  # This card is from a subdeck
            subdeck = FlashcardDecks.query.get(card.flashcard_deck_id)
            if subdeck:
                deck_info[card.flashcard_id] = {
                    'deck_id': subdeck.flashcard_deck_id,
                    'deck_name': subdeck.name
                }
    
    return render_template(
        "flashcards.html", 
        deck=deck, 
        flashcards=flashcards, 
        due_only=due_only,
        deck_info=deck_info
    )
