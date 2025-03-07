from flask import Blueprint, request, redirect, url_for, render_template, flash, jsonify
from models import db, FlashcardDecks, Flashcards
from flask_login import login_required, current_user
from ..auth.decorators import login_required_for_decks
from routes.deck.utils import is_descendant

management_bp = Blueprint('deck_management', __name__)

@management_bp.route('/create', methods=['POST'])
@login_required
def create_deck():
    parent_deck_id = request.form.get('parent_deck_id')
    name = request.form.get('name')
    description = request.form.get('description')
    
    # Validate parent deck ownership if provided
    if parent_deck_id:
        parent_deck = FlashcardDecks.query.get_or_404(parent_deck_id)
        if parent_deck.user_id and parent_deck.user_id != current_user.id:
            flash('You do not have permission to add sub-decks to this deck', 'error')
            return redirect(url_for('main.index'))
    
    new_deck = FlashcardDecks(
        name=name,
        description=description,
        parent_deck_id=parent_deck_id,
        user_id=current_user.id  # Associate with current user
    )
    db.session.add(new_deck)
    db.session.commit()
    
    return jsonify({"success": True, "deck_id": new_deck.flashcard_deck_id})

@management_bp.route('/create_empty', methods=['POST'])
@login_required
def create_empty_deck():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    
    new_deck = FlashcardDecks(
        name=name,
        description=description,
        user_id=current_user.id  # Associate with current user
    )
    db.session.add(new_deck)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "deck_id": new_deck.flashcard_deck_id,
        "message": "Empty deck created successfully"
    })

@management_bp.route('/rename/<int:deck_id>', methods=['PUT'])
@login_required
def rename_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if user owns this deck
    if deck.user_id and deck.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
    
    try:
        data = request.json
        deck.name = data.get('name')
        deck.description = data.get('description')
        db.session.commit()
        return jsonify({"success": True, "message": "Deck renamed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@management_bp.route('/delete/<int:deck_id>', methods=['DELETE'])
@login_required
def delete_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if user owns this deck
    if deck.user_id and deck.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
    
    try:
        # Create recursive CTE to find all sub-decks
        cte = db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == deck_id
        ).cte(name='sub_decks', recursive=True)

        cte = cte.union_all(
            db.session.query(
                FlashcardDecks.flashcard_deck_id.label('id')
            ).filter(
                FlashcardDecks.parent_deck_id == cte.c.id
            )
        )

        # Get all deck IDs including the parent
        all_deck_ids = [deck_id]  # Include the parent deck ID
        all_deck_ids.extend([row[0] for row in db.session.query(cte.c.id).all()])
        
        # Count sub-decks (excluding parent)
        sub_decks_count = len(all_deck_ids) - 1
        
        # Count flashcards from all levels
        flashcards_count = Flashcards.query.filter(
            Flashcards.flashcard_deck_id.in_(all_deck_ids)
        ).count()

        # Delete the deck (cascade will handle children)
        db.session.delete(deck)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": f"Deck deleted successfully along with {sub_decks_count} sub-deck{'s' if sub_decks_count != 1 else ''} "
                      f"and {flashcards_count} flashcard{'s' if flashcards_count != 1 else ''}"
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting deck: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@management_bp.route('/move/<int:deck_id>', methods=['PUT'])
@login_required
def move_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if user owns this deck
    if deck.user_id and deck.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
    
    try:
        data = request.json
        new_parent_id = data.get('new_parent_id')
        
        # Validate new parent ownership if provided
        if new_parent_id:
            new_parent = FlashcardDecks.query.get_or_404(new_parent_id)
            if new_parent.user_id and new_parent.user_id != current_user.id:
                return jsonify({'success': False, 'message': 'You do not have permission to move to this deck'}), 403
        
        # Validate the move
        if new_parent_id is not None:
            # Check that new parent exists
            new_parent = FlashcardDecks.query.get_or_404(new_parent_id)
            
            # Check for circular reference (can't move a deck into its own descendants)
            if is_descendant(new_parent_id, deck_id):
                return jsonify({"success": False, "error": "Cannot move a deck into its own subdeck"}), 400
            
            # Check if target is the same as current parent
            if deck.parent_deck_id == new_parent_id:
                return jsonify({"success": False, "error": "Deck is already in that location"}), 400
        elif deck.parent_deck_id is None:
            # Already at root level
            return jsonify({"success": False, "error": "Deck is already at root level"}), 400
        
        # Update the parent ID
        deck.parent_deck_id = new_parent_id
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Deck moved successfully"
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error moving deck: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
