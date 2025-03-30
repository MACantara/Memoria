from flask import render_template, abort, redirect, url_for, flash, g
from models.user import User
from models import FlashcardDecks, Flashcards
from flask_login import current_user, login_required
from routes.user import user_bp
from sqlalchemy import func, and_

@user_bp.route('/<username>')
def profile(username):
    """View a user's profile by username"""
    # Find the user by username
    user = User.query.filter_by(username=username).first_or_404()
    
    # Get user statistics
    deck_count = FlashcardDecks.query.filter_by(user_id=user.id).count()
    
    card_count = Flashcards.query.join(FlashcardDecks).filter(
        FlashcardDecks.user_id == user.id
    ).count()
    
    mastered_count = Flashcards.query.join(FlashcardDecks).filter(
        and_(
            FlashcardDecks.user_id == user.id,
            Flashcards.state == 2  # Mastered state
        )
    ).count()
    
    # Get public decks properly filtered
    if current_user.is_authenticated and current_user.id == user.id:
        # If viewing own profile, show all decks
        public_decks = FlashcardDecks.query.filter_by(user_id=user.id).all()
        is_own_profile = True
    else:
        # Otherwise, show only public decks
        public_decks = FlashcardDecks.query.filter_by(
            user_id=user.id, 
            is_public=True
        ).all()
        is_own_profile = False
    
    # Add all decks to g for modals
    if current_user.is_authenticated:
        g.all_decks = FlashcardDecks.query.filter_by(user_id=current_user.id).all()
    
    # Render the profile template
    return render_template(
        'user/profile.html', 
        user=user,
        deck_count=deck_count,
        card_count=card_count,
        mastered_count=mastered_count,
        public_decks=public_decks,
        is_own_profile=is_own_profile
    )

@user_bp.route('/me')
@login_required
def my_profile():
    """Redirect to the current user's profile"""
    return redirect(url_for('user.profile', username=current_user.username))
