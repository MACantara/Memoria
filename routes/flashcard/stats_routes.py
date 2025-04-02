from flask import Blueprint, jsonify, render_template, request, url_for, redirect
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_stats, get_current_time
from datetime import datetime, timedelta
from sqlalchemy import case
import traceback

stats_bp = Blueprint('stats', __name__)

@stats_bp.route("/deck/<int:deck_id>/view_stats")
@stats_bp.route("/deck/<int:deck_id>/view_stats/<int:page>")
def view_deck_stats(deck_id, page=1):
    """
    View spaced repetition stats for a deck
    Now supports an optional page parameter to maintain pagination state in the URL
    """
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    return render_template("stats.html", deck=deck, current_page=page)

@stats_bp.route("/deck/<int:deck_id>/stats")
def deck_stats(deck_id):
    """Get spaced repetition stats for a deck as JSON with caching"""
    from flask import current_app
    cache_key = f"deck_stats:{deck_id}"
    
    # Try to get stats from cache
    if hasattr(current_app, 'cache') and current_app.cache:
        cached_stats = current_app.cache.get(cache_key)
        if cached_stats:
            return jsonify(cached_stats)
    
    # Not in cache, calculate stats
    deck = FlashcardDecks.query.get_or_404(deck_id)
    stats = get_stats(deck_id)
    
    # Cache the result
    if hasattr(current_app, 'cache') and current_app.cache:
        current_app.cache.set(cache_key, stats, timeout=1800)  # Cache for 30 minutes
    
    return jsonify(stats)

@stats_bp.route("/deck/<int:deck_id>/retention")
def deck_retention(deck_id):
    """Get retention analytics for a deck with caching"""
    from flask import current_app
    cache_key = f"deck_retention:{deck_id}"
    
    # Try to get from cache
    if hasattr(current_app, 'cache') and current_app.cache:
        cached_retention = current_app.cache.get(cache_key)
        if cached_retention:
            return jsonify(cached_retention)
    
    # Optimize query to only retrieve needed fields and apply indexing
    cards_with_retention = Flashcards.query.with_entities(
        Flashcards.retrievability
    ).filter_by(
        flashcard_deck_id=deck_id
    ).filter(
        Flashcards.retrievability > 0,
        Flashcards.last_reviewed.isnot(None)
    ).all()
    
    # Calculate retention statistics
    retention_data = {
        'total_cards_studied': len(cards_with_retention),
        'has_retention_data': len(cards_with_retention) > 0,
    }
    
    # Only include average retention if there are cards with review history
    if cards_with_retention:
        retention_data['average_retention'] = sum(c.retrievability for c in cards_with_retention) / len(cards_with_retention)
        retention_data['retention_distribution'] = get_retention_distribution(cards_with_retention)
    else:
        retention_data['average_retention'] = None
        retention_data['retention_distribution'] = {}
    
    # Cache the result
    if hasattr(current_app, 'cache') and current_app.cache:
        current_app.cache.set(cache_key, retention_data, timeout=1800)  # Cache for 30 minutes
        
    return jsonify(retention_data)

def get_retention_distribution(cards):
    """Calculate retention distribution in 10% buckets"""
    distribution = {
        '0-10%': 0,
        '10-20%': 0,
        '20-30%': 0,
        '30-40%': 0,
        '40-50%': 0,
        '50-60%': 0,
        '60-70%': 0,
        '70-80%': 0,
        '80-90%': 0,
        '90-100%': 0
    }
    
    for card in cards:
        r = card.retrievability
        if r < 0.1:
            distribution['0-10%'] += 1
        elif r < 0.2:
            distribution['10-20%'] += 1
        elif r < 0.3:
            distribution['20-30%'] += 1
        elif r < 0.4:
            distribution['30-40%'] += 1
        elif r < 0.5:
            distribution['40-50%'] += 1
        elif r < 0.6:
            distribution['50-60%'] += 1
        elif r < 0.7:
            distribution['60-70%'] += 1
        elif r < 0.8:
            distribution['70-80%'] += 1
        elif r < 0.9:
            distribution['80-90%'] += 1
        else:
            distribution['90-100%'] += 1
    
    return distribution

@stats_bp.route("/deck/<int:deck_id>/upcoming-reviews")
def get_upcoming_reviews(deck_id):
    """Get upcoming review cards data with pagination and caching"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build a cache key that includes pagination
        from flask import current_app
        cache_key = f"upcoming_reviews:{deck_id}:{page}:{per_page}"
        
        # Try to get from cache
        if hasattr(current_app, 'cache') and current_app.cache:
            cached_results = current_app.cache.get(cache_key)
            if cached_results:
                return jsonify(cached_results)
        
        # Create recursive CTE to find all decks including this one and its sub-decks
        cte = db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.flashcard_deck_id == deck_id
        ).cte(name='review_decks', recursive=True)

        cte = cte.union_all(
            db.session.query(
                FlashcardDecks.flashcard_deck_id.label('id')
            ).filter(
                FlashcardDecks.parent_deck_id == cte.c.id
            )
        )
        
        # Get current time in UTC
        current_time = get_current_time()
        
        # Use WITH_ENTITIES to only select needed fields
        query = Flashcards.query.with_entities(
            Flashcards.flashcard_id,
            Flashcards.question,
            Flashcards.due_date,
            Flashcards.last_reviewed,
            Flashcards.state,
            Flashcards.retrievability,
            Flashcards.flashcard_deck_id
        ).filter(
            Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
        ).order_by(
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc()
        )
        
        # Apply pagination
        paginated_cards = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format results with more efficient processing
        results = []
        for card in paginated_cards.items:
            # Simplify state name determination
            state_names = ["New", "Learning", "Mastered", "Forgotten"]
            state_value = card.state or 0
            state_name = state_names[state_value] if state_value < len(state_names) else "Unknown"
            
            # Format dates directly, without checking for None repeatedly
            due_date_str = "Not scheduled" if card.due_date is None else card.due_date.isoformat() + 'Z'
            last_reviewed_str = "Never" if card.last_reviewed is None else card.last_reviewed.isoformat() + 'Z'
            
            results.append({
                'id': card.flashcard_id,
                'question': card.question,
                'due_date': due_date_str,
                'last_reviewed': last_reviewed_str,
                'state': state_name,
                'state_value': state_value,
                'retrievability': card.retrievability or 0.0,
                'deck_id': card.flashcard_deck_id
            })
        
        # Update pagination URLs to use correct endpoint
        pagination_urls = {
            'current_url': url_for('stats.view_deck_stats', deck_id=deck_id, page=page),
            'base_url': url_for('stats.view_deck_stats', deck_id=deck_id),
            'next_url': url_for('stats.view_deck_stats', deck_id=deck_id, page=paginated_cards.next_num) if paginated_cards.has_next else None,
            'prev_url': url_for('stats.view_deck_stats', deck_id=deck_id, page=paginated_cards.prev_num) if paginated_cards.has_prev else None,
        }
        
        response_data = {
            'cards': results,
            'pagination': {
                'total': paginated_cards.total,
                'pages': paginated_cards.pages,
                'page': page,
                'per_page': per_page,
                'has_next': paginated_cards.has_next,
                'has_prev': paginated_cards.has_prev,
                'next_page': paginated_cards.next_num,
                'prev_page': paginated_cards.prev_num,
                'urls': pagination_urls
            }
        }
        
        # Cache the result
        if hasattr(current_app, 'cache') and current_app.cache:
            current_app.cache.set(cache_key, response_data, timeout=300)  # Cache for 5 minutes
            
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting upcoming review cards: {e}")
        print(traceback.format_exc())  # Now using correctly imported traceback
        return jsonify({'error': str(e)}), 500
