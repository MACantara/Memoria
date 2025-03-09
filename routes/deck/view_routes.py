from flask import Blueprint, request, render_template, jsonify, g, abort
from models import FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_due_cards, get_current_time
from routes.deck.utils import count_due_flashcards
from flask_login import login_required, current_user

deck_view_bp = Blueprint('deck_view', __name__)

@deck_view_bp.before_request
def load_all_decks():
    """Load all decks for the current user for use in templates"""
    if current_user.is_authenticated:
        g.all_decks = FlashcardDecks.query.filter_by(user_id=current_user.id).all()
    else:
        g.all_decks = []

@deck_view_bp.route("/<int:deck_id>")
@login_required
def get_deck_flashcards(deck_id):
    """View all flashcards in a deck"""
    # Get the deck with its sub-decks
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check ownership
    if deck.user_id != current_user.id:
        abort(403)  # Unauthorized
    
    # Get parent decks for breadcrumb trail
    parent_decks = []
    current_parent = deck.parent
    while current_parent is not None:
        parent_decks.insert(0, current_parent)
        current_parent = current_parent.parent
    
    # Get child decks
    child_decks = FlashcardDecks.query.filter_by(parent_deck_id=deck_id).all()
    
    # Get flashcards
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id).all()
    
    # Import due counts function
    from routes.deck.utils import count_due_flashcards
    due_count = count_due_flashcards(deck_id)
    
    return render_template(
        'deck.html',
        deck=deck,
        parent_decks=parent_decks,
        child_decks=child_decks,
        flashcards=flashcards,
        due_count=due_count
    )

@deck_view_bp.route("/study/<int:deck_id>")
@login_required
def study_deck(deck_id):
    """Study a specific deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check ownership
    if deck.user_id != current_user.id:
        abort(403)  # Unauthorized
        
    # Check if studying due cards only
    due_only = request.args.get('due_only') == 'true'
    
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
