from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from models import db, FlashcardDecks, Flashcards
from datetime import datetime

deck_bp = Blueprint('deck', __name__)

@deck_bp.route("/<int:deck_id>")
def get_deck_flashcards(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    if deck.parent_deck_id is None:
        return render_template("deck.html", deck=deck)
    else:
        flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id).all()
        return render_template("flashcards.html", deck=deck, flashcards=flashcards)

@deck_bp.route("/<int:deck_id>/study")
def study_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    flashcards = Flashcards.query.join(FlashcardDecks).filter(
        db.or_(
            FlashcardDecks.flashcard_deck_id == deck_id,
            FlashcardDecks.parent_deck_id == deck_id
        )
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
        # Count items to be deleted for logging
        child_decks = FlashcardDecks.query.filter(
            FlashcardDecks.parent_deck_id == deck_id
        ).count()
        
        flashcards = Flashcards.query.filter(
            Flashcards.flashcard_deck_id.in_([
                deck_id,
                *[d.flashcard_deck_id for d in deck.child_decks]
            ])
        ).count()

        # Delete the deck (cascade will handle children)
        db.session.delete(deck)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": f"Deck deleted successfully along with {child_decks} sub-decks and {flashcards} flashcards"
        })
    except Exception as e:
        db.session.rollback()
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
