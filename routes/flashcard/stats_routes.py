from flask import Blueprint, render_template, jsonify, request, abort, redirect, url_for, flash
from models import db, FlashcardDecks, Flashcards
from flask_login import login_required, current_user
from ..auth.decorators import login_required_for_decks
from sqlalchemy import func
from datetime import datetime, timedelta

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/deck/<int:deck_id>/view_stats')
@login_required_for_decks
def view_deck_stats(deck_id):
    """View statistics for a flashcard deck"""
    # Get the deck and verify permissions
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if user has access to this deck
    if deck.user_id and deck.user_id != current_user.id:
        flash('You do not have permission to view stats for this deck', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('stats.html', deck=deck)

@stats_bp.route('/api/deck/<int:deck_id>/stats')
@login_required
def get_deck_stats(deck_id):
    """API endpoint to get statistics for a deck"""
    try:
        # Get the deck
        deck = FlashcardDecks.query.get_or_404(deck_id)
        
        # Check if user has access to this deck
        if deck.user_id and deck.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized access'}), 403
        
        # Get mastery stats
        mastery_stats = deck.get_mastery_stats()
        
        # Calculate retention rate (if there have been any reviews)
        total_reviews = 0  # Implement review count logic
        correct_reviews = 0  # Implement correct review count logic
        retention_rate = 0
        
        if total_reviews > 0:
            retention_rate = (correct_reviews / total_reviews) * 100
            
        # Get upcoming reviews
        current_time = datetime.now()
        next_day = current_time + timedelta(days=1)
        next_week = current_time + timedelta(days=7)
        
        # Create recursive CTE query to get all cards in the deck hierarchy
        from sqlalchemy.sql import text
        
        # Use SQLAlchemy to safely build the recursive query
        cte_query = db.session.query(FlashcardDecks.flashcard_deck_id.label('id')) \
            .filter(FlashcardDecks.flashcard_deck_id == deck_id) \
            .cte(name='deck_hierarchy', recursive=True)
            
        cte_query = cte_query.union_all(
            db.session.query(FlashcardDecks.flashcard_deck_id) \
            .filter(FlashcardDecks.parent_deck_id == cte_query.c.id)
        )
        
        # Get counts for upcoming reviews
        due_today = db.session.query(func.count(Flashcards.flashcard_id)) \
            .filter(
                Flashcards.flashcard_deck_id.in_(db.session.query(cte_query.c.id)),
                Flashcards.due_date <= current_time
            ).scalar() or 0
            
        due_tomorrow = db.session.query(func.count(Flashcards.flashcard_id)) \
            .filter(
                Flashcards.flashcard_deck_id.in_(db.session.query(cte_query.c.id)),
                Flashcards.due_date > current_time,
                Flashcards.due_date <= next_day
            ).scalar() or 0
            
        due_week = db.session.query(func.count(Flashcards.flashcard_id)) \
            .filter(
                Flashcards.flashcard_deck_id.in_(db.session.query(cte_query.c.id)),
                Flashcards.due_date > next_day,
                Flashcards.due_date <= next_week
            ).scalar() or 0
        
        # Return deck stats as JSON
        return jsonify({
            'success': True,
            'stats': {
                'total_cards': mastery_stats['total'],
                'new_cards': mastery_stats['new'],
                'learning_cards': mastery_stats['learning'],
                'mastered_cards': mastery_stats['mastered'],
                'forgotten_cards': mastery_stats['forgotten'],
                'mastery_percentage': mastery_stats['mastery_percentage'],
                'retention_rate': retention_rate,
                'upcoming_reviews': {
                    'due_today': due_today,
                    'due_tomorrow': due_tomorrow,
                    'due_week': due_week
                }
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/api/deck/<int:deck_id>/upcoming_reviews')
@login_required
def get_upcoming_reviews(deck_id):
    """Get paginated upcoming reviews for a deck"""
    try:
        # Get the deck
        deck = FlashcardDecks.query.get_or_404(deck_id)
        
        # Check if user has access to this deck
        if deck.user_id and deck.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized access'}), 403
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
        
        # Create recursive CTE query to get all cards in the deck hierarchy
        cte_query = db.session.query(FlashcardDecks.flashcard_deck_id.label('id')) \
            .filter(FlashcardDecks.flashcard_deck_id == deck_id) \
            .cte(name='deck_hierarchy', recursive=True)
            
        cte_query = cte_query.union_all(
            db.session.query(FlashcardDecks.flashcard_deck_id) \
            .filter(FlashcardDecks.parent_deck_id == cte_query.c.id)
        )
        
        # Get flashcards with due dates, ordered by due date
        query = db.session.query(Flashcards) \
            .filter(Flashcards.flashcard_deck_id.in_(db.session.query(cte_query.c.id))) \
            .order_by(Flashcards.due_date.asc().nullslast())
            
        # Paginate the results
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        cards = []
        for card in paginated.items:
            cards.append({
                'id': card.flashcard_id,
                'question': card.question,
                'last_reviewed': card.last_reviewed.isoformat() if card.last_reviewed else None,
                'due_date': card.due_date.isoformat() if card.due_date else None,
                'state': card.state or 0,
                'state_name': card.get_state_name(),
                'retrievability': card.retrievability or 0
            })
        
        # Return paginated results
        return jsonify({
            'success': True,
            'reviews': cards,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
