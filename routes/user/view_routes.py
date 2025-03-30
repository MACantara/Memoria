from flask import render_template, abort, redirect, url_for
from models import User, FlashcardDecks, Flashcards
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
    
    # Get public decks (for demonstration - you may need to add a public field to decks)
    # For now, we'll just show all decks if the user is viewing their own profile
    if current_user.is_authenticated and current_user.id == user.id:
        public_decks = FlashcardDecks.query.filter_by(user_id=user.id).all()
    else:
        # In a real implementation, you'd filter by public decks
        # For now, showing a limited set of decks as "public" for demo purposes
        public_decks = FlashcardDecks.query.filter_by(user_id=user.id).limit(5).all()
    
    # Render the profile template
    return render_template(
        'user/profile.html', 
        user=user,
        deck_count=deck_count,
        card_count=card_count,
        mastered_count=mastered_count,
        public_decks=public_decks
    )

@user_bp.route('/me')
@login_required
def my_profile():
    """Redirect to the current user's profile"""
    return redirect(url_for('user.profile', username=current_user.username))
