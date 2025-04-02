from flask import Blueprint, request, jsonify, abort, current_app
from models import db, FlashcardDecks, Flashcards
from utils import is_descendant, get_descendant_deck_ids  # Updated import path
from flask_login import current_user, login_required

# Change the URL prefix to match how it's being called
deck_management_bp = Blueprint('deck_management', __name__, url_prefix='')

@deck_management_bp.route("/create", methods=["POST"])
@login_required
def create_deck():
    # Check if the request is JSON or form data
    if request.is_json:
        data = request.json
        parent_deck_id = data.get("parent_deck_id")
        
        # Check if this is a batch creation request
        if 'decks' in data:
            # Handle batch creation
            return create_multiple_decks(parent_deck_id)
        else:
            # Handle single deck creation with JSON data
            name = data.get("name", "New Deck")
            description = data.get("description", "")
    else:
        # Handle form data submission
        parent_deck_id = request.form.get("parent_deck_id")
        
        # Check if this is a batch creation request
        if 'decks' in request.form:
            # Handle batch creation
            return create_multiple_decks(parent_deck_id)
        else:
            # Handle single deck creation with form data
            name = request.form.get("name", "New Deck")
            description = request.form.get("description", "")
    
    # If parent deck is provided, check if it belongs to current user
    if parent_deck_id:
        parent_deck = FlashcardDecks.query.get_or_404(parent_deck_id)
        if parent_deck.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized access"}), 403
    
    # Create the deck with the current user's ID
    deck = FlashcardDecks(
        name=name,
        description=description,
        parent_deck_id=parent_deck_id,
        user_id=current_user.id
    )
    db.session.add(deck)
    db.session.commit()
    
    return jsonify({"success": True, "deck_id": deck.flashcard_deck_id})

def create_multiple_decks(parent_deck_id=None):
    """Create multiple decks at once"""
    # Check if the parent deck belongs to current user (if provided)
    if parent_deck_id:
        parent_deck = FlashcardDecks.query.get_or_404(parent_deck_id)
        if parent_deck.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized access"}), 403
    
    # Get deck data from either form data or JSON
    if request.json:
        decks_data = request.json.get('decks', [])
    else:
        # Parse form data for decks
        decks_data = request.form.get('decks')
        if decks_data:
            try:
                import json
                decks_data = json.loads(decks_data)
            except:
                return jsonify({"success": False, "error": "Invalid deck data format"}), 400
    
    # Validate that we have decks to create
    if not decks_data or not isinstance(decks_data, list):
        return jsonify({"success": False, "error": "No decks provided"}), 400
    
    created_decks = []
    try:
        for deck_info in decks_data:
            name = deck_info.get('name', '').strip()
            description = deck_info.get('description', '').strip()
            
            # Skip empty deck names
            if not name:
                continue
                
            # Create new deck
            deck = FlashcardDecks(
                name=name,
                description=description,
                parent_deck_id=parent_deck_id,
                user_id=current_user.id
            )
            db.session.add(deck)
            db.session.flush()  # Get the ID without committing
            
            # Track created deck ID
            created_decks.append({
                'deck_id': deck.flashcard_deck_id,
                'name': name
            })
        
        # Commit all decks at once
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Successfully created {len(created_decks)} deck(s)",
            "decks": created_decks
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@deck_management_bp.route("/rename/<int:deck_id>", methods=["PUT"])
@login_required
def rename_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if the deck belongs to the current user
    if deck.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403
    
    try:
        data = request.json
        deck.name = data.get('name')
        deck.description = data.get('description')
        db.session.commit()
        return jsonify({"success": True, "message": "Deck renamed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@deck_management_bp.route("/delete/<int:deck_id>", methods=["DELETE"])
@login_required
def delete_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if the deck belongs to the current user
    if deck.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403
    
    try:
        # Create a materialized path to improve hierarchy traversal
        all_deck_ids = get_descendant_deck_ids(deck_id)
        
        # Count sub-decks (excluding parent)
        sub_decks_count = len(all_deck_ids) - 1
        
        # More efficient count using direct SQL count
        flashcards_count = db.session.query(
            db.func.count(Flashcards.flashcard_id)
        ).filter(
            Flashcards.flashcard_deck_id.in_(all_deck_ids)
        ).scalar() or 0

        # Process flashcard deletion in batches to avoid timeout
        if flashcards_count > 0:
            batch_delete_flashcards(all_deck_ids, batch_size=1000)  # Increased batch size

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

def batch_delete_flashcards(deck_ids, batch_size=1000):
    """
    More efficient batch deletion with direct SQL for larger batches
    """
    try:
        # Use raw SQL for more efficient deletion in large batches
        while True:
            # Get IDs using a much larger batch size
            card_ids = db.session.query(Flashcards.flashcard_id).filter(
                Flashcards.flashcard_deck_id.in_(deck_ids)
            ).limit(batch_size).all()
            
            if not card_ids:
                break
                
            batch_ids = [id[0] for id in card_ids]
            batch_count = len(batch_ids)
            
            # Execute direct SQL for faster batch deletion
            db.session.execute(
                "DELETE FROM flashcards WHERE flashcard_id IN :ids",
                {"ids": tuple(batch_ids)}
            )
            
            # Commit each batch
            db.session.commit()
            print(f"Deleted batch of {batch_count} flashcards")
    except Exception as e:
        db.session.rollback()
        print(f"Error in batch deletion: {str(e)}")
        raise

@deck_management_bp.route("/create_empty", methods=["POST"])
@login_required
def create_empty_deck():
    try:
        # Check if request is JSON
        if request.is_json:
            data = request.json
            
            # Check if this is a batch creation request
            if 'decks' in data:
                # Handle batch creation
                return create_multiple_decks()
            else:
                # Handle single deck creation (legacy support)
                deck = FlashcardDecks(
                    name=data.get('name', 'New Deck'),
                    description=data.get('description', ''),
                    parent_deck_id=None,
                    user_id=current_user.id
                )
        else:
            # Handle form data submission
            deck = FlashcardDecks(
                name=request.form.get('name', 'New Deck'),
                description=request.form.get('description', ''),
                parent_deck_id=None,
                user_id=current_user.id
            )
            
        db.session.add(deck)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "deck_id": deck.flashcard_deck_id,
            "message": "Empty deck created successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@deck_management_bp.route("/move/<int:deck_id>", methods=["PUT"])
@login_required
def move_deck(deck_id):
    """Move a deck to a new parent deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if the deck belongs to the current user
    if deck.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized access"}), 403
    
    try:
        data = request.json
        new_parent_id = data.get('new_parent_id')
        
        # Validate the move
        if new_parent_id is not None:
            # Check that new parent exists
            new_parent = FlashcardDecks.query.get_or_404(new_parent_id)
            
            # Check if new parent belongs to current user
            if new_parent.user_id != current_user.id:
                return jsonify({"success": False, "error": "Unauthorized access"}), 403
            
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
