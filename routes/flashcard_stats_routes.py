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
    """Get spaced repetition stats for a deck as JSON"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    stats = get_stats(deck_id)
    return jsonify(stats)

@stats_bp.route("/deck/<int:deck_id>/retention")
def deck_retention(deck_id):
    """Get retention analytics for a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Query for cards with retrievability values AND review history
    cards_with_retention = Flashcards.query.filter_by(flashcard_deck_id=deck_id)\
        .filter(
            Flashcards.retrievability > 0,
            Flashcards.last_reviewed.isnot(None)  # Only include cards that have been reviewed
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
    """Get upcoming review cards data for a specific deck"""
    try:
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
        
        # Query for all cards
        query = Flashcards.query.filter(
            Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
        )
        
        # Order the results by due date
        query = query.order_by(
            # Cards with no due date first, then by due date ascending
            case((Flashcards.due_date == None, 0), else_=1),
            Flashcards.due_date.asc()
        )
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Paginate the results
        paginated_cards = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format results
        results = []
        for card in paginated_cards.items:
            # Determine card state name
            state_name = "New"
            if card.state == 1:
                state_name = "Learning"
            elif card.state == 2:
                state_name = "Mastered"
            elif card.state == 3:
                state_name = "Forgotten"
            
            # Format due date
            due_date_str = "Not scheduled" if card.due_date is None else card.due_date.isoformat()
            last_reviewed_str = "Never" if card.last_reviewed is None else card.last_reviewed.isoformat()
            
            results.append({
                'id': card.flashcard_id,
                'question': card.question,
                'due_date': due_date_str,
                'last_reviewed': last_reviewed_str,
                'state': state_name,
                'state_value': card.state or 0,
                'retrievability': card.retrievability or 0.0,
                'deck_id': card.flashcard_deck_id
            })
        
        # Build pagination URLs - removed filter parameter
        pagination_urls = {
            'current_url': url_for('stats.view_deck_stats', deck_id=deck_id, page=page),
            'base_url': url_for('stats.view_deck_stats', deck_id=deck_id),
            'next_url': url_for('stats.view_deck_stats', deck_id=deck_id, page=paginated_cards.next_num) if paginated_cards.has_next else None,
            'prev_url': url_for('stats.view_deck_stats', deck_id=deck_id, page=paginated_cards.prev_num) if paginated_cards.has_prev else None,
        }
        
        return jsonify({
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
        })
        
    except Exception as e:
        print(f"Error getting upcoming review cards: {e}")
        print(traceback.format_exc())  # Now using correctly imported traceback
        return jsonify({'error': str(e)}), 500