from flask import Blueprint, jsonify, render_template
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_stats

stats_bp = Blueprint('stats', __name__)

@stats_bp.route("/deck/<int:deck_id>/view_stats")
def view_deck_stats(deck_id):
    """View spaced repetition stats for a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Auto-fix any cards with missing states when viewing stats
    Flashcards.fix_missing_states()
    
    return render_template("stats.html", deck=deck)

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
    
    # Query for cards with retrievability values
    cards_with_retention = Flashcards.query.filter_by(flashcard_deck_id=deck_id)\
        .filter(Flashcards.retrievability > 0).all()
    
    # Calculate retention statistics
    retention_data = {
        'total_cards_studied': len(cards_with_retention),
        'average_retention': sum(c.retrievability for c in cards_with_retention) / len(cards_with_retention) \
            if cards_with_retention else 0,
        'retention_distribution': get_retention_distribution(cards_with_retention)
    }
    
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
