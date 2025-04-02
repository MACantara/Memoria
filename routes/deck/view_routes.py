from flask import Blueprint, request, render_template, jsonify, g, abort, current_app, redirect, url_for
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time
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
    # Performance: Use cache first if available
    from flask import current_app
    cache_key = f"deck_view:{deck_id}:{current_user.id}"
    
    cache_data = None
    if hasattr(current_app, 'cache') and current_app.cache:
        cache_data = current_app.cache.get(cache_key)
    
    if cache_data:
        deck, parent_decks, child_decks = cache_data
    else:
        # Use more selective loading - don't load all relationships at once
        deck = FlashcardDecks.query.get_or_404(deck_id)
        
        # Check ownership
        if deck.user_id != current_user.id:
            abort(403)  # Unauthorized
        
        # Load parent decks with a separate efficient query
        parent_decks = []
        if deck.parent_deck_id:
            # Get all ancestors with a single query
            ancestors_query = """
            WITH RECURSIVE ancestors(id, name, parent_id) AS (
                SELECT fd.flashcard_deck_id, fd.name, fd.parent_deck_id
                FROM flashcard_decks fd
                WHERE fd.flashcard_deck_id = :deck_id
                UNION ALL
                SELECT fd.flashcard_deck_id, fd.name, fd.parent_deck_id
                FROM flashcard_decks fd, ancestors a
                WHERE fd.flashcard_deck_id = a.parent_id
            )
            SELECT id, name, parent_id FROM ancestors WHERE id != :deck_id
            ORDER BY parent_id ASC NULLS FIRST
            """
            try:
                ancestors = db.session.execute(ancestors_query, {"deck_id": deck.parent_deck_id}).fetchall()
                parent_decks = [{"flashcard_deck_id": a.id, "name": a.name} for a in ancestors]
            except Exception as e:
                current_app.logger.error(f"Error fetching ancestors: {str(e)}")
        
        # Load child decks in a separate query
        child_decks = FlashcardDecks.query.filter_by(
            parent_deck_id=deck_id
        ).with_entities(
            FlashcardDecks.flashcard_deck_id,
            FlashcardDecks.name,
            FlashcardDecks.created_at
        ).all()
        
        # Cache the loaded data
        if hasattr(current_app, 'cache') and current_app.cache:
            current_app.cache.set(cache_key, (deck, parent_decks, child_decks), timeout=300)
    
    # Get sort parameter for child decks
    sort_by = request.args.get('sort', 'name')
    
    # Apply sorting to child_decks list (pre-fetched without ORM overhead)
    if child_decks:
        # Use a lighter approach to sorting
        if sort_by == 'name':
            child_decks = sorted(child_decks, key=lambda d: d.name)
        elif sort_by == 'created_desc':
            child_decks = sorted(child_decks, key=lambda d: d.created_at or datetime.min, reverse=True)
        elif sort_by == 'created_asc':
            child_decks = sorted(child_decks, key=lambda d: d.created_at or datetime.min)
        # Skip expensive due counts for initial load - can be loaded via AJAX if needed
    
    # Get pagination parameters for flashcards
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort', 'created_desc')
    
    # Optimize or defer the expensive query - only count flashcards DIRECTLY in this deck
    # This avoids the recursive CTE for the initial page load
    total_flashcards = db.session.query(
        func.count(Flashcards.flashcard_id)
    ).filter_by(
        flashcard_deck_id=deck_id
    ).scalar() or 0
    
    # Only fetch flashcards if there are any (avoid empty queries)
    flashcards = []
    if total_flashcards > 0:
        # Base query for flashcards - only include what's needed for the current page
        flashcards_query = Flashcards.query.filter_by(flashcard_deck_id=deck_id)
        
        # Apply sorting
        if sort_by == 'created_desc':
            flashcards_query = flashcards_query.order_by(desc(Flashcards.created_at))
        elif sort_by == 'created_asc':
            flashcards_query = flashcards_query.order_by(asc(Flashcards.created_at))
        elif sort_by == 'question':
            flashcards_query = flashcards_query.order_by(func.lower(Flashcards.question))
        elif sort_by == 'answer':
            flashcards_query = flashcards_query.order_by(asc(Flashcards.correct_answer))
        elif sort_by == 'due_asc':
            flashcards_query = flashcards_query.order_by(
                case((Flashcards.due_date == None, 1), else_=0),
                asc(Flashcards.due_date)
            )
        elif sort_by == 'state':
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
    
    # Defer due count calculation to an AJAX request after page load
    # This dramatically speeds up the initial page render
    due_count = 0  # Will be populated by JavaScript
    
    # Log performance timing
    current_app.logger.info(f"Rendering deck {deck_id} with {total_flashcards} flashcards")
    
    return render_template(
        'deck.html',
        deck=deck,
        parent_decks=parent_decks,
        child_decks=child_decks,
        flashcards=flashcards,
        pagination=pagination,
        total_flashcards=total_flashcards,
        due_count=due_count,
        defer_due_count=True  # Tell template to load due counts via AJAX
    )

@deck_view_bp.route("/api/due-count/<int:deck_id>")
@login_required
def get_deck_due_count(deck_id):
    """Get due count for a deck via AJAX"""
    try:
        # Check if count is in cache
        cache_key = f"deck_due_count:{deck_id}:{current_user.id}"
        
        if hasattr(current_app, 'cache') and current_app.cache:
            cached_count = current_app.cache.get(cache_key)
            if cached_count is not None:
                return jsonify({"due_count": cached_count})
        
        # Not in cache, calculate it
        due_count = count_due_flashcards(deck_id)
        
        # Cache the result
        if hasattr(current_app, 'cache') and current_app.cache:
            current_app.cache.set(cache_key, due_count, timeout=300)  # 5 min cache
        
        return jsonify({"due_count": due_count})
    except Exception as e:
        current_app.logger.error(f"Error calculating due count: {str(e)}")
        return jsonify({"due_count": 0, "error": str(e)})

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
    
    # AJAX request for loading flashcards - modified to use pagination
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
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
        
        # Use a query instead of loading all cards at once
        query = Flashcards.query.filter(
            Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
        )
        
        # Apply due filtering if needed
        if due_only:
            query = query.filter(
                db.or_(Flashcards.due_date <= get_current_time(), Flashcards.due_date == None),
                Flashcards.state != 2  # Exclude cards already mastered
            )
        
        # Order by due date
        query = query.order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            asc(Flashcards.due_date),
            asc(Flashcards.flashcard_id)
        )
        
        # Apply pagination
        paginated_cards = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Serialize flashcards with only needed fields
        flashcard_data = []
        for card in paginated_cards.items:
            # Only include subdeck info if from a different deck
            deck_info = None
            if card.flashcard_deck_id != deck_id:
                deck_info = {
                    'deck_id': card.flashcard_deck_id,
                    'deck_name': getattr(card, 'deck_name', None)  # Add joined field
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
        
        # Return paginated data
        return jsonify({
            'flashcards': flashcard_data,
            'pagination': {
                'total': paginated_cards.total,
                'pages': paginated_cards.pages,
                'page': page,
                'per_page': per_page,
                'has_next': paginated_cards.has_next,
                'has_prev': paginated_cards.has_prev
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
    # Pass batch size for loading
    batch_size = 20  # Set your desired batch size
    
    return render_template(
        "flashcards.html", 
        deck=deck,
        flashcards_count=flashcards_count,
        batch_size=batch_size,
        due_only=due_only
    )

# Update the get_due_cards function to explicitly order cards by due date
def get_due_cards(deck_id, due_only=False):
    """Get cards due for review"""
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
    
    # Always order by due date (null values first, then earliest due date)
    # This ensures consistent ordering in both Due Only and Study All modes
    query = query.order_by(
        # Cards with no due date come first
        case((Flashcards.due_date == None, 0), else_=1),
        # Then order by due date (earliest first)
        asc(Flashcards.due_date),
        # Finally by ID for stable ordering of cards with the same due date
        asc(Flashcards.flashcard_id)
    )
        
    return query.all()

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

# Add a new API endpoint for lazy loading
@deck_view_bp.route("/flashcards/lazy_load/<int:deck_id>")
@login_required
def lazy_load_flashcards(deck_id):
    """Lazy load flashcards as user scrolls"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    sort_by = request.args.get('sort', 'created_desc')
    
    # Apply filtering
    query = Flashcards.query.filter_by(flashcard_deck_id=deck_id)
    
    # Apply sorting
    if sort_by == 'created_desc':
        query = query.order_by(desc(Flashcards.created_at))
    elif sort_by == 'created_asc':
        query = query.order_by(asc(Flashcards.created_at))
    elif sort_by == 'question':
        query = query.order_by(func.lower(Flashcards.question))
    elif sort_by == 'answer':
        query = query.order_by(asc(Flashcards.correct_answer))
    elif sort_by == 'due_asc':
        query = query.order_by(
            case((Flashcards.due_date == None, 1), else_=0),
            asc(Flashcards.due_date)
        )
    elif sort_by == 'state':
        query = query.order_by(
            asc(Flashcards.state),
            desc(Flashcards.due_date)
        )
    
    # Return only necessary fields
    flashcards = query.with_entities(
        Flashcards.flashcard_id,
        Flashcards.question,
        Flashcards.correct_answer,
        Flashcards.state,
        Flashcards.due_date
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "flashcards": [
            {
                "id": f.flashcard_id,
                "question": f.question,
                "correct_answer": f.correct_answer,
                "state": f.state,
                "due_date": f.due_date.isoformat() if f.due_date else None
            } for f in flashcards.items
        ],
        "pagination": {
            "total": flashcards.total,
            "pages": flashcards.pages,
            "page": page
        }
    })
