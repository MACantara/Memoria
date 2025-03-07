from flask import Blueprint, request, render_template, jsonify
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
    
    # AJAX request for batch loading flashcards
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        page = int(request.args.get('page', 1))
        batch_size = int(request.args.get('batch_size', 20))
        offset = (page - 1) * batch_size
        
        # Get cards based on the due_only parameter with pagination
        if due_only:
            flashcards = get_due_cards(deck_id, due_only=True, offset=offset, limit=batch_size)
        else:
            flashcards = get_due_cards(deck_id, due_only=False, offset=offset, limit=batch_size)
        
        # Serialize flashcards to JSON
        flashcard_data = []
        for card in flashcards:
            deck_info = None
            if card.flashcard_deck_id != deck_id:  # This is from a subdeck
                subdeck = FlashcardDecks.query.get(card.flashcard_deck_id)
                if subdeck:
                    deck_info = {
                        'deck_id': subdeck.flashcard_deck_id,
                        'deck_name': subdeck.name
                    }
            
            flashcard_data.append({
                'id': card.flashcard_id,
                'question': card.question,
                'correct_answer': card.correct_answer,
                'incorrect_answers': card.incorrect_answers,
                'state': card.state or 0,
                'retrievability': card.retrievability or 0,
                'subdeck': deck_info
            })
        
        return jsonify({
            'flashcards': flashcard_data,
            'page': page,
            'has_more': len(flashcards) == batch_size
        })
    
    # Normal page load - just get the count of cards for rendering the template
    if due_only:
        flashcards_count = db.session.query(db.func.count(Flashcards.flashcard_id)).filter(
            db.or_(
                Flashcards.flashcard_deck_id == deck_id,
                FlashcardDecks.query.filter(
                    FlashcardDecks.parent_deck_id == deck_id
                ).exists()
            ),
            db.or_(Flashcards.due_date <= get_current_time(), Flashcards.due_date == None),
            Flashcards.state != 2  # Exclude cards already mastered
        ).scalar()
    else:
        flashcards_count = db.session.query(db.func.count(Flashcards.flashcard_id)).filter(
            db.or_(
                Flashcards.flashcard_deck_id == deck_id,
                FlashcardDecks.query.filter(
                    FlashcardDecks.parent_deck_id == deck_id
                ).exists()
            )
        ).scalar()
    
    # Pass batch size for loading
    batch_size = 20  # Set your desired batch size
    
    return render_template(
        "flashcards.html", 
        deck=deck,
        flashcards_count=flashcards_count,
        batch_size=batch_size,
        due_only=due_only
    )

# Update the get_due_cards function to support pagination
def get_due_cards(deck_id, due_only=False, offset=0, limit=None):
    """Get cards due for review with pagination support"""
    from models import db  # Import here to avoid circular imports
    
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
    
    # Base query that includes all cards in the deck and its sub-decks
    query = db.session.query(Flashcards).filter(
        Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
    )
    
    # Add filters for due cards if needed
    if due_only:
        current_time = get_current_time()
        query = query.filter(
            db.or_(Flashcards.due_date <= current_time, Flashcards.due_date == None),
            Flashcards.state != 2  # Exclude cards already mastered
        )
    
    # Apply pagination
    if offset > 0:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
        
    return query.all()
