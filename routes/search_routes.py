from flask import Blueprint, request, render_template, jsonify, g
from models import db, FlashcardDecks, Flashcards
from sqlalchemy import or_, and_, func, text, desc
from utils import count_due_flashcards

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
                              count_due_flashcards=count_due_flashcards,
                              min=min)
    
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
                          count_due_flashcards=count_due_flashcards,
                          min=min)

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
    """Search deck names and descriptions with improved fuzzy matching"""
    # Split the query into individual terms for fuzzy matching
    search_terms = query.lower().split()
    
    if not search_terms:
        return [], 0
    
    # Base query to search decks
    deck_query = FlashcardDecks.query
    
    # Create conditions for each term - if ANY term matches, include the deck
    term_conditions = []
    for term in search_terms:
        search_pattern = f'%{term}%'
        term_conditions.append(
            or_(
                FlashcardDecks.name.ilike(search_pattern),
                FlashcardDecks.description.ilike(search_pattern)
            )
        )
    
    # Apply the conditions - match if ANY term is found
    deck_query = deck_query.filter(or_(*term_conditions))
    
    # Get total count
    total_decks = deck_query.count()
    
    # Calculate relevance score for sorting
    # 1. Exact match with name gets highest priority
    # 2. Starting of name gets second priority
    # 3. Count how many terms match in name and description
    decks_with_scores = []
    for deck in deck_query.all():
        score = 0
        deck_name_lower = deck.name.lower()
        deck_desc_lower = deck.description.lower() if deck.description else ""
        
        # Exact match gets highest score
        if deck_name_lower == query.lower():
            score += 100
        
        # Name starts with query term gets high score
        for term in search_terms:
            if deck_name_lower.startswith(term):
                score += 50
        
        # Count matches in name
        for term in search_terms:
            if term in deck_name_lower:
                score += 10
        
        # Count matches in description
        for term in search_terms:
            if term in deck_desc_lower:
                score += 5
        
        decks_with_scores.append((deck, score))
    
    # Sort by score and paginate manually
    decks_with_scores.sort(key=lambda x: x[1], reverse=True)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_decks = [deck for deck, score in decks_with_scores[start_idx:end_idx]]
    
    return paginated_decks, total_decks

def search_flashcards(query, page=1, per_page=20):
    """Search flashcard questions and answers with improved fuzzy matching"""
    # Split the query into individual terms for fuzzy matching
    search_terms = query.lower().split()
    
    if not search_terms:
        return [], 0
    
    # Base query to search flashcards
    card_query = db.session.query(
        Flashcards, FlashcardDecks
    ).join(
        FlashcardDecks, 
        Flashcards.flashcard_deck_id == FlashcardDecks.flashcard_deck_id
    )
    
    # Create conditions for each term - if ANY term matches, include the flashcard
    term_conditions = []
    for term in search_terms:
        search_pattern = f'%{term}%'
        term_conditions.append(
            or_(
                Flashcards.question.ilike(search_pattern),
                Flashcards.correct_answer.ilike(search_pattern),
                # Also search incorrect answers if they're stored as strings
                func.cast(Flashcards.incorrect_answers, db.String).ilike(search_pattern)
            )
        )
    
    # Apply the conditions - match if ANY term is found
    card_query = card_query.filter(or_(*term_conditions))
    
    # Get total count
    total_cards = card_query.count()
    
    # Calculate relevance score for sorting
    cards_with_scores = []
    for card, deck in card_query.all():
        score = 0
        question_lower = card.question.lower()
        answer_lower = card.correct_answer.lower()
        
        # Question contains exact query gets highest score
        if query.lower() in question_lower:
            score += 50
        
        # Count matches in question
        for term in search_terms:
            if term in question_lower:
                score += 10
        
        # Count matches in answer
        for term in search_terms:
            if term in answer_lower:
                score += 5
        
        # Additional points for match in incorrect answers
        if hasattr(card, 'incorrect_answers') and card.incorrect_answers:
            incorrect_text = ' '.join(str(ans).lower() for ans in card.incorrect_answers)
            for term in search_terms:
                if term in incorrect_text:
                    score += 3
        
        cards_with_scores.append((card, deck, score))
    
    # Sort by score and paginate manually
    cards_with_scores.sort(key=lambda x: x[2], reverse=True)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Process results to add deck information
    processed_results = []
    for card, deck, _ in cards_with_scores[start_idx:end_idx]:
        # Add deck reference to card
        card.deck = deck
        processed_results.append(card)
    
    return processed_results, total_cards
