from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
from sqlalchemy.sql import func  # Add this import

deck_bp = Blueprint('deck', __name__)

@deck_bp.route("/<int:deck_id>")
def get_deck_flashcards(deck_id):
    """View deck structure and its contents"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id).all()
    return render_template("deck.html", deck=deck, flashcards=flashcards)

@deck_bp.route("/<int:deck_id>/study")
def study_deck(deck_id):
    """Study flashcards in this deck and all nested sub-decks"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Create recursive CTE to find all nested sub-decks
    cte = db.session.query(
        FlashcardDecks.flashcard_deck_id.label('id')
    ).filter(
        FlashcardDecks.flashcard_deck_id == deck_id
    ).cte(name='study_decks', recursive=True)

    cte = cte.union_all(
        db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == cte.c.id
        )
    )
    
    # Get all flashcards from current deck and all nested sub-decks
    flashcards = Flashcards.query.filter(
        Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
    ).all()
    
    return render_template("flashcards.html", deck=deck, flashcards=flashcards)

@deck_bp.route("/create", methods=["POST"])
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

@deck_bp.route("/rename/<int:deck_id>", methods=["PUT"])
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

@deck_bp.route("/delete/<int:deck_id>", methods=["DELETE"])
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
        print(f"Error deleting deck: {str(e)}")  # Add logging
        return jsonify({"success": False, "error": str(e)}), 500

@deck_bp.route("/create_empty", methods=["POST"])
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
