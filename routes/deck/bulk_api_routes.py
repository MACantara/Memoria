from flask import Blueprint, jsonify, request, current_app
from models import db, FlashcardDecks, Flashcards
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

bulk_api_bp = Blueprint('bulk_api', __name__)

@bulk_api_bp.route("/flashcards/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_flashcards():
    """Delete multiple flashcards at once"""
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({"success": False, "error": "No flashcard IDs provided"}), 400
    
    flashcard_ids = data['ids']
    if not flashcard_ids:
        return jsonify({"success": False, "error": "Empty ID list"}), 400
    
    try:
        # Get flashcards that belong to the current user
        flashcards = Flashcards.query.join(FlashcardDecks).filter(
            Flashcards.flashcard_id.in_(flashcard_ids),
            FlashcardDecks.user_id == current_user.id
        ).all()
        
        if not flashcards:
            return jsonify({"success": False, "error": "No valid flashcards found"}), 404
        
        # Delete each flashcard
        for flashcard in flashcards:
            db.session.delete(flashcard)
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "deleted_count": len(flashcards),
            "message": f"Successfully deleted {len(flashcards)} flashcards"
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk delete flashcards: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@bulk_api_bp.route("/flashcards/bulk-move", methods=["POST"])
@login_required
def bulk_move_flashcards():
    """Move multiple flashcards to another deck"""
    data = request.get_json()
    if not data or 'flashcard_ids' not in data or 'destination_deck_id' not in data:
        return jsonify({"success": False, "error": "Missing required parameters"}), 400
    
    flashcard_ids = data['flashcard_ids']
    destination_deck_id = data['destination_deck_id']
    
    if not flashcard_ids:
        return jsonify({"success": False, "error": "Empty flashcard ID list"}), 400
    
    # Verify destination deck belongs to current user
    dest_deck = FlashcardDecks.query.filter_by(
        flashcard_deck_id=destination_deck_id,
        user_id=current_user.id
    ).first()
    
    if not dest_deck:
        return jsonify({"success": False, "error": "Invalid destination deck"}), 404
    
    try:
        # Get flashcards that belong to the current user
        flashcards = Flashcards.query.join(FlashcardDecks).filter(
            Flashcards.flashcard_id.in_(flashcard_ids),
            FlashcardDecks.user_id == current_user.id
        ).all()
        
        if not flashcards:
            return jsonify({"success": False, "error": "No valid flashcards found"}), 404
        
        # Move each flashcard to the destination deck
        for flashcard in flashcards:
            flashcard.flashcard_deck_id = destination_deck_id
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "moved_count": len(flashcards),
            "message": f"Successfully moved {len(flashcards)} flashcards to {dest_deck.name}"
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk move flashcards: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@bulk_api_bp.route("/decks/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_decks():
    """Delete multiple decks at once"""
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({"success": False, "error": "No deck IDs provided"}), 400
    
    deck_ids = data['ids']
    if not deck_ids:
        return jsonify({"success": False, "error": "Empty ID list"}), 400
    
    try:
        # Get decks that belong to the current user
        decks = FlashcardDecks.query.filter(
            FlashcardDecks.flashcard_deck_id.in_(deck_ids),
            FlashcardDecks.user_id == current_user.id
        ).all()
        
        if not decks:
            return jsonify({"success": False, "error": "No valid decks found"}), 404
        
        # Delete each deck (cascades to delete flashcards)
        for deck in decks:
            db.session.delete(deck)
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "deleted_count": len(decks),
            "message": f"Successfully deleted {len(decks)} decks"
        })
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in bulk delete decks: {str(e)}")
        return jsonify({"success": False, "error": "Database error while deleting decks"}), 500
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk delete decks: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@bulk_api_bp.route("/decks/bulk-move", methods=["POST"])
@login_required
def bulk_move_decks():
    """Move multiple decks to another parent or to root level"""
    data = request.get_json()
    if not data or 'deck_ids' not in data:
        return jsonify({"success": False, "error": "Missing required parameters"}), 400
    
    deck_ids = data['deck_ids']
    parent_deck_id = data.get('parent_deck_id')  # None means move to root
    
    if not deck_ids:
        return jsonify({"success": False, "error": "Empty deck ID list"}), 400
    
    # If moving to a parent, verify it belongs to current user
    if parent_deck_id:
        parent_deck = FlashcardDecks.query.filter_by(
            flashcard_deck_id=parent_deck_id,
            user_id=current_user.id
        ).first()
        
        if not parent_deck:
            return jsonify({"success": False, "error": "Invalid parent deck"}), 404
    
    try:
        # Get decks that belong to the current user
        decks = FlashcardDecks.query.filter(
            FlashcardDecks.flashcard_deck_id.in_(deck_ids),
            FlashcardDecks.user_id == current_user.id
        ).all()
        
        if not decks:
            return jsonify({"success": False, "error": "No valid decks found"}), 404
        
        # Verify the parent is not one of the decks being moved or their descendants
        if parent_deck_id:
            # Check if parent is in selected decks
            if int(parent_deck_id) in [deck.flashcard_deck_id for deck in decks]:
                return jsonify({
                    "success": False, 
                    "error": "Cannot move a deck into itself"
                }), 400
            
            # Also check if parent is a descendant of any selected deck
            for deck in decks:
                if is_descendant(int(parent_deck_id), deck.flashcard_deck_id):
                    return jsonify({
                        "success": False, 
                        "error": "Cannot move a deck into one of its own sub-decks"
                    }), 400
        
        # Move each deck to the destination parent or root
        for deck in decks:
            deck.parent_deck_id = parent_deck_id
        
        db.session.commit()
        
        parent_name = 'root level' if not parent_deck_id else parent_deck.name
        return jsonify({
            "success": True, 
            "moved_count": len(decks),
            "message": f"Successfully moved {len(decks)} decks to {parent_name}"
        })
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in bulk move decks: {str(e)}")
        return jsonify({"success": False, "error": "Database error while moving decks"}), 500
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk move decks: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def is_descendant(deck_id, potential_ancestor_id):
    """Check if a deck is a descendant of another deck"""
    # Get the candidate deck
    deck = FlashcardDecks.query.get(deck_id)
    if not deck:
        return False
    
    # If this is a root deck, it can't be a descendant
    if deck.parent_deck_id is None:
        return False
    
    # Check if the immediate parent matches the ancestor
    if deck.parent_deck_id == potential_ancestor_id:
        return True
    
    # Recursively check the parent
    return is_descendant(deck.parent_deck_id, potential_ancestor_id)
