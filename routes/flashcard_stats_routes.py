from flask import Blueprint, jsonify, render_template
from models import FlashcardDecks
from services.fsrs_scheduler import get_stats

stats_bp = Blueprint('stats', __name__)

@stats_bp.route("/deck/<int:deck_id>/view_stats")
def view_deck_stats(deck_id):
    """View spaced repetition stats for a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Auto-fix any cards with missing states when viewing stats
    from models import Flashcards
    Flashcards.fix_missing_states()
    
    return render_template("stats.html", deck=deck)

@stats_bp.route("/deck/<int:deck_id>/stats")
def deck_stats(deck_id):
    """Get spaced repetition stats data for a deck (JSON)"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    stats = get_stats(deck_id)
    return jsonify(stats)
