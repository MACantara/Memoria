from flask import Blueprint, request, jsonify
from models import db, FlashcardDecks, Flashcards
from routes.deck.utils import is_descendant

# Change the URL prefix to match how it's being called
deck_management_bp = Blueprint('deck_management', __name__, url_prefix='')

@deck_management_bp.route("/create", methods=["POST"])
def create_deck():
    parent_deck_id = request.form.get("parent_deck_id")
    name = request.form.get("name", "New Deck")
    description = request.form.get("description", "")
    
    deck = FlashcardDecks(
        name=name,
        description=description,
        parent_deck_id=parent_deck_id
    )
    db.session.add(deck)
    db.session.commit()
    
    return jsonify({"success": True, "deck_id": deck.flashcard_deck_id})

@deck_management_bp.route("/rename/<int:deck_id>", methods=["PUT"])
def rename_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
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
def delete_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
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

@deck_management_bp.route("/create_empty", methods=["POST"])
def create_empty_deck():
    try:
        data = request.json
        deck = FlashcardDecks(
            name=data.get('name', 'New Deck'),
            description=data.get('description', ''),
            parent_deck_id=None
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
def move_deck(deck_id):
    """Move a deck to a new parent deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    try:
        data = request.json
        new_parent_id = data.get('new_parent_id')
        
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
