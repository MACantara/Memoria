from flask import Blueprint, request, render_template, jsonify, g, abort, current_app, redirect, url_for
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time, get_due_cards
from utils import count_due_flashcards, create_pagination_metadata, batch_count_due_cards
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload, contains_eager, defer, load_only
from sqlalchemy import func, desc, asc, case

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
    """View all flashcards in a deck with pagination"""
    # Get the deck with its sub-decks using eager loading
    deck = FlashcardDecks.query.options(
        joinedload(FlashcardDecks.parent_deck),
        joinedload(FlashcardDecks.child_decks)
    ).get_or_404(deck_id)
    
    # Check ownership
    if deck.user_id != current_user.id:
        abort(403)  # Unauthorized
    
    # Get parent decks for breadcrumb trail
    parent_decks = []
    current_parent = deck.parent_deck
    while current_parent is not None:
        parent_decks.insert(0, current_parent)
        current_parent = current_parent.parent_deck
    
    # Get sort parameter for child decks
    sort_by = request.args.get('sort', 'name')
    
    # Get child decks and apply sorting
    if deck.child_decks:
        # Apply sorting to child_decks
        if sort_by == 'name':
            deck.child_decks.sort(key=lambda d: d.name)
        elif sort_by == 'created_desc':
            deck.child_decks.sort(key=lambda d: d.created_at, reverse=True)
        elif sort_by == 'created_asc':
            deck.child_decks.sort(key=lambda d: d.created_at)
        elif sort_by == 'cards_desc' or sort_by == 'cards_asc':
            # Count cards including those in subdecks for each child deck
            child_decks_with_counts = [(d, d.count_all_flashcards()) for d in deck.child_decks]
            
            # Sort by card count
            if sort_by == 'cards_desc':
                child_decks_with_counts.sort(key=lambda x: x[1], reverse=True)
            else:  # cards_asc
                child_decks_with_counts.sort(key=lambda x: x[1])
            
            # Update the child_decks list with the sorted decks
            deck.child_decks = [d for d, _ in child_decks_with_counts]
        elif sort_by == 'due_desc':
            # Get due counts for all child decks
            child_deck_ids = [d.flashcard_deck_id for d in deck.child_decks]
            due_counts = batch_count_due_cards(child_deck_ids, current_user.id)
            
            # Sort child decks by due count
            deck.child_decks.sort(key=lambda d: due_counts.get(d.flashcard_deck_id, 0), reverse=True)
    
    # Get pagination parameters for flashcards
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort', 'created_desc')  # New default sort
    
    # Limit per_page to reasonable values
    per_page = min(max(per_page, 10), 100) 
    
    # For AJAX requests, return paginated flashcards JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"error": "Use the /flashcard/lazy_load endpoint for AJAX requests"})
    
    # Get total count for pagination info
    total_flashcards = db.session.query(
        func.count(Flashcards.flashcard_id)
    ).filter_by(
        flashcard_deck_id=deck_id
    ).scalar()
    
    # Base query for flashcards
    flashcards_query = Flashcards.query.filter_by(flashcard_deck_id=deck_id)
    
    # Apply sorting
    if sort_by == 'created_desc':
        flashcards_query = flashcards_query.order_by(desc(Flashcards.created_at))
    elif sort_by == 'created_asc':
        flashcards_query = flashcards_query.order_by(asc(Flashcards.created_at))
    elif sort_by == 'question':
        flashcards_query = flashcards_query.order_by(asc(Flashcards.question))
    elif sort_by == 'answer':
        flashcards_query = flashcards_query.order_by(asc(Flashcards.correct_answer))
    elif sort_by == 'due_asc':
        # Sort by due date, putting NULL values at the end
        flashcards_query = flashcards_query.order_by(
            case((Flashcards.due_date == None, 1), else_=0),
            asc(Flashcards.due_date)
        )
    elif sort_by == 'state':
        # Sort by learning state (0=new, 1=learning, 2=mastered, 3=forgotten)
        flashcards_query = flashcards_query.order_by(
            asc(Flashcards.state),
            desc(Flashcards.due_date)
        )
    
    # Get flashcards with pagination
    flashcards = flashcards_query.offset((page-1) * per_page).limit(per_page).all()
    
    # Create pagination metadata
    pagination = create_pagination_metadata(
        page, 
        per_page, 
        total_flashcards,
        {key: value for key, value in request.args.items() if key not in ['page']}
    )
    
    # Get due count
    due_count = count_due_flashcards(deck_id)
    
    return render_template(
        'deck.html',
        deck=deck,
        parent_decks=parent_decks,
        child_decks=deck.child_decks,
        flashcards=flashcards,
        pagination=pagination,
        total_flashcards=total_flashcards,
        due_count=due_count
    )

@deck_view_bp.route("/study/<int:deck_id>")
@login_required
def study_deck(deck_id):
    """Study a specific deck"""
    # Get the deck
    deck = FlashcardDecks.query.filter_by(flashcard_deck_id=deck_id, user_id=current_user.id).first_or_404()
    
    # Get parameters
    due_only = request.args.get('due_only') == 'true'
    
    # Check if it's an AJAX request for flashcard data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Get all due cards (still need the total count)
        all_cards = get_due_cards(deck_id, due_only)
        total_cards = len(all_cards)
        
        # Calculate pagination values
        total_pages = (total_cards + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_cards)
        
        # Get just the requested page of cards
        page_cards = all_cards[start_idx:end_idx]
        
        # Transform to JSON response format
        flashcard_data = []
        
        for card in page_cards:
            # Set default deck info
            deck_info = None
            
            # If card is from a subdeck, include subdeck info
            if card.flashcard_deck_id != deck_id:
                subdeck = FlashcardDecks.query.filter_by(flashcard_deck_id=card.flashcard_deck_id).first()
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
                'state': 0 if card.state is None else int(card.state),
                'retrievability': card.retrievability or 0,
                'due_date': card.due_date.isoformat() if card.due_date else None,
                'subdeck': deck_info
            })
        
        # Return paginated response
        return jsonify({
            'flashcards': flashcard_data,
            'total': total_cards,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages
            }
        })
    
    # Normal page load - calculate the count of cards for rendering the template
    # Create recursive CTE to find all decks including this one and its sub-decks
    cte = db.session.query(
        FlashcardDecks.flashcard_deck_id.label('id')
    ).filter(
        FlashcardDecks.flashcard_deck_id == deck_id
    ).cte(name='study_deck_hierarchy', recursive=True)

    cte = cte.union_all(
        db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == cte.c.id
        )
    )
    
    # Build a query that includes all cards in this deck and its subdecks
    if due_only:
        flashcards_count = db.session.query(db.func.count(Flashcards.flashcard_id)).filter(
            Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id)),
            db.or_(Flashcards.due_date <= get_current_time(), Flashcards.due_date == None),
            Flashcards.state != 2  # Exclude cards already mastered
        ).scalar()
    else:
        flashcards_count = db.session.query(db.func.count(Flashcards.flashcard_id)).filter(
            Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
        ).scalar()
    
    return render_template(
        "flashcards.html", 
        deck=deck,
        flashcards_count=flashcards_count,
        due_only=due_only
    )

@deck_view_bp.route("/random-deck")
@login_required
def random_deck():
    """Select a random deck to study, prioritizing decks with due cards"""
    # Get all decks for the current user
    user_decks = FlashcardDecks.query.filter_by(user_id=current_user.id).all()
    
    if not user_decks:
        # User has no decks
        return jsonify({
            "success": False, 
            "message": "You don't have any flashcard decks yet."
        }), 404
    
    # Get due counts for all decks
    deck_ids = [deck.flashcard_deck_id for deck in user_decks]
    due_counts = batch_count_due_cards(deck_ids, current_user.id)
    
    # Get card counts for all decks
    card_counts = {deck.flashcard_deck_id: deck.count_all_flashcards() for deck in user_decks}
    
    # 1. Separate decks with due cards
    decks_with_due = [deck for deck in user_decks if due_counts.get(deck.flashcard_deck_id, 0) > 0]
    
    # 2. Separate decks with any cards (even if not due)
    decks_with_cards = [deck for deck in user_decks if card_counts.get(deck.flashcard_deck_id, 0) > 0]
    
    import random
    
    if decks_with_due:
        # Prioritize decks with due cards
        selected_deck = random.choice(decks_with_due)
        return redirect(url_for('deck.deck_view.study_deck', deck_id=selected_deck.flashcard_deck_id, due_only='true'))
    elif decks_with_cards:
        # No decks with due cards, but some decks have cards - pick one of those
        selected_deck = random.choice(decks_with_cards)
        return redirect(url_for('deck.deck_view.study_deck', deck_id=selected_deck.flashcard_deck_id, no_due_cards='true'))
    else:
        # All decks are empty, just pick any deck and show appropriate message
        selected_deck = random.choice(user_decks)
        return redirect(url_for('deck.deck_view.study_deck', deck_id=selected_deck.flashcard_deck_id, empty_deck='true'))
