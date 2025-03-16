from flask import Blueprint, render_template, g, request, url_for
from models import db, FlashcardDecks, Flashcards
from flask_login import current_user, login_required
from utils import count_due_flashcards, batch_count_due_cards, create_pagination_metadata
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc, asc, case, text, literal_column

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    """Main page - show decks for the current user or welcome page for logged out users"""
    if current_user.is_authenticated:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int) # Default 12 decks per page
        sort_by = request.args.get('sort', 'name')  # Default sort by name
        
        # Limit per_page to reasonable values
        per_page = min(max(per_page, 4), 24)
        
        # Count total top-level decks for this user
        total_decks = FlashcardDecks.query.filter_by(
            parent_deck_id=None, 
            user_id=current_user.id
        ).count()
        
        # Get top-level decks with pagination
        decks_query = FlashcardDecks.query.filter_by(
            parent_deck_id=None, 
            user_id=current_user.id
        ).options(
            # Eagerly load child_decks to avoid N+1 query problem 
            joinedload(FlashcardDecks.child_decks),
            # Eagerly load counts that will be needed for display
            joinedload(FlashcardDecks.flashcards)
        )
        
        # Apply sorting
        if sort_by == 'name':
            decks_query = decks_query.order_by(FlashcardDecks.name)
        elif sort_by == 'created_desc':
            decks_query = decks_query.order_by(desc(FlashcardDecks.created_at))
        elif sort_by == 'created_asc':
            decks_query = decks_query.order_by(asc(FlashcardDecks.created_at))
        elif sort_by == 'cards_desc' or sort_by == 'cards_asc':
            # We need to get all decks first so we can count all cards including those in subdecks
            all_decks = decks_query.all()
            
            # Calculate total card count for each deck (including subdecks)
            deck_with_counts = [(deck, deck.count_all_flashcards()) for deck in all_decks]
            
            # Sort the list by card count
            if sort_by == 'cards_desc':
                deck_with_counts.sort(key=lambda x: x[1], reverse=True)
            else:  # cards_asc
                deck_with_counts.sort(key=lambda x: x[1])
            
            # Get the properly sorted decks
            sorted_decks = [deck for deck, _ in deck_with_counts]
            
            # Apply pagination after sorting
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            decks = sorted_decks[start_idx:end_idx]
            
            # Create pagination metadata
            pagination = create_pagination_metadata(
                page, 
                per_page, 
                total_decks,
                {key: value for key, value in request.args.items() if key not in ['page']}
            )
            
            # Get all decks in a single efficient query for dropdown menus
            all_decks = FlashcardDecks.query.filter_by(
                user_id=current_user.id
            ).options(
                # Eager load relationships needed for templates
                joinedload(FlashcardDecks.parent_deck),
                joinedload(FlashcardDecks.child_decks)
            ).all()
            
            # Make all decks available to templates
            g.all_decks = all_decks
            
            # Get deck IDs for due count calculation
            deck_ids = [deck.flashcard_deck_id for deck in decks]
            
            # Calculate due counts efficiently in a batch
            due_counts = batch_count_due_cards(deck_ids, current_user.id)
            
            # Create an optimized due count function for templates
            def optimized_count_due(deck_id):
                return due_counts.get(deck_id, 0)
            
            return render_template(
                'index.html', 
                decks=decks, 
                count_due_flashcards=optimized_count_due,
                pagination=pagination
            )
        elif sort_by == 'due_desc':
            # We'll sort after fetching since due count requires recursive calculation
            pass
        
        # If we didn't return early in the cards_desc/cards_asc case, apply pagination
        decks = decks_query.offset((page-1) * per_page).limit(per_page).all()
        
        # Special handling for due_desc sort (must happen after query)
        if sort_by == 'due_desc':
            # Get deck IDs first
            deck_ids = [deck.flashcard_deck_id for deck in decks]
            # Get due counts efficiently
            due_counts = batch_count_due_cards(deck_ids, current_user.id)
            # Sort manually by due count
            decks.sort(key=lambda d: due_counts.get(d.flashcard_deck_id, 0), reverse=True)
        
        # Create pagination metadata
        pagination = create_pagination_metadata(
            page, 
            per_page, 
            total_decks,
            {key: value for key, value in request.args.items() if key not in ['page']}
        )
        
        # Get all decks in a single efficient query for dropdown menus
        all_decks = FlashcardDecks.query.filter_by(
            user_id=current_user.id
        ).options(
            # Eager load relationships needed for templates
            joinedload(FlashcardDecks.parent_deck),
            joinedload(FlashcardDecks.child_decks)
        ).all()
        
        # Make all decks available to templates
        g.all_decks = all_decks
        
        # Get deck IDs for due count calculation
        deck_ids = [deck.flashcard_deck_id for deck in decks]
        
        # Calculate due counts efficiently in a batch
        due_counts = batch_count_due_cards(deck_ids, current_user.id)
        
        # Create an optimized due count function for templates
        def optimized_count_due(deck_id):
            return due_counts.get(deck_id, 0)
        
        return render_template(
            'index.html', 
            decks=decks, 
            count_due_flashcards=optimized_count_due,
            pagination=pagination
        )
    else:
        # Show welcome page for logged out users
        return render_template('index.html')
        
@main_bp.route('/api/due-counts')
@login_required
def get_due_counts_api():
    """API endpoint to get due counts for decks"""
    # Get deck IDs to check from query params or all user decks
    deck_ids_param = request.args.get('deck_ids')
    if deck_ids_param:
        try:
            deck_ids = [int(id_str) for id_str in deck_ids_param.split(',')]
        except ValueError:
            return {"success": False, "error": "Invalid deck IDs format"}, 400
    else:
        # Get all deck IDs for the user
        deck_ids = [d.flashcard_deck_id for d in 
                   FlashcardDecks.query.with_entities(FlashcardDecks.flashcard_deck_id)
                   .filter_by(user_id=current_user.id).all()]
    
    # Get counts efficiently
    counts = batch_count_due_cards(deck_ids, current_user.id)
    
    return {"success": True, "counts": counts}
