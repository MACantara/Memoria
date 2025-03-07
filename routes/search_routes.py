from flask import Blueprint, request, render_template, jsonify, g
from models import db, FlashcardDecks, Flashcards
from sqlalchemy import or_, and_
from routes.deck.utils import count_due_flashcards

search_bp = Blueprint('search', __name__, url_prefix='/search')

@search_bp.route('/', methods=['GET'])
def search():
    """Handle search requests and render search results page"""
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    scope = request.args.get('scope', 'all')
    per_page = 20
    
    # Get all decks for the study/stats modals
    g.all_decks = FlashcardDecks.query.all()
    
    # Empty query shows search page with no results
    if not query:
        return render_template('search_results.html', 
                              query='', 
                              deck_results=[], 
                              card_results=[],
                              total_decks=0,
                              total_cards=0,
                              page=page,
                              per_page=per_page,
                              scope=scope,
                              count_due_flashcards=count_due_flashcards)  # Pass the function
    
    # For AJAX requests, return JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return search_json(query, page, per_page, scope)
    
    # Regular request - perform search based on scope
    deck_results = []
    card_results = []
    total_decks = 0
    total_cards = 0
    
    if scope in ['all', 'decks']:
        deck_results, total_decks = search_decks(query, page, per_page)
    
    if scope in ['all', 'cards']:
        card_results, total_cards = search_flashcards(query, page, per_page)
    
    return render_template('search_results.html',
                          query=query,
                          deck_results=deck_results,
                          card_results=card_results,
                          total_decks=total_decks,
                          total_cards=total_cards,
                          page=page,
                          per_page=per_page,
                          scope=scope,
                          count_due_flashcards=count_due_flashcards)  # Pass the function

@search_bp.route('/api', methods=['GET'])
def search_api():
    """API endpoint for search (JSON only)"""
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search_type = request.args.get('type', 'all')  # 'all', 'decks', or 'cards'
    
    return search_json(query, page, per_page, search_type)

def search_json(query, page=1, per_page=20, search_type='all'):
    """Return search results as JSON"""
    if not query:
        return jsonify({
            'success': False,
            'message': 'No search query provided',
            'results': {}
        })
    
    results = {}
    
    if search_type in ['all', 'decks']:
        deck_results, total_decks = search_decks(query, page, per_page)
        results['decks'] = {
            'results': [deck.to_dict() for deck in deck_results],
            'total': total_decks,
            'page': page,
            'per_page': per_page
        }
    
    if search_type in ['all', 'cards']:
        card_results, total_cards = search_flashcards(query, page, per_page)
        results['cards'] = {
            'results': [card.to_search_dict() for card in card_results],
            'total': total_cards,
            'page': page,
            'per_page': per_page
        }
    
    return jsonify({
        'success': True,
        'query': query,
        'results': results
    })

def search_decks(query, page=1, per_page=20):
    """Search deck names and descriptions"""
    search_term = f'%{query}%'
    
    # Base query to search decks
    deck_query = FlashcardDecks.query.filter(
        or_(
            FlashcardDecks.name.ilike(search_term),
            FlashcardDecks.description.ilike(search_term)
        )
    )
    
    # Get total count
    total_decks = deck_query.count()
    
    # Paginate and get results
    decks = deck_query.order_by(
        # Sort exact matches first, then alphabetically
        FlashcardDecks.name.ilike(query).desc(),  # Exact matches first
        FlashcardDecks.name                        # Then alphabetically
    ).paginate(page=page, per_page=per_page, error_out=False).items
    
    return decks, total_decks

def search_flashcards(query, page=1, per_page=20):
    """Search flashcard questions and answers"""
    search_term = f'%{query}%'
    
    # Base query to search flashcards
    card_query = db.session.query(
        Flashcards, FlashcardDecks
    ).join(
        FlashcardDecks, 
        Flashcards.flashcard_deck_id == FlashcardDecks.flashcard_deck_id
    ).filter(
        or_(
            Flashcards.question.ilike(search_term),
            Flashcards.correct_answer.ilike(search_term)
        )
    )
    
    # Get total count
    total_cards = card_query.count()
    
    # Paginate and get results
    card_results = card_query.order_by(
        # Sort exact matches first, then by ID
        Flashcards.question.ilike(query).desc(),  # Exact matches first
        Flashcards.flashcard_id.desc()            # Then by newest first
    ).paginate(page=page, per_page=per_page, error_out=False).items
    
    # Process results to add deck information
    processed_results = []
    for card, deck in card_results:
        # Add deck reference to card
        card.deck = deck
        processed_results.append(card)
    
    return processed_results, total_cards
