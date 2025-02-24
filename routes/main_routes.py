from flask import Blueprint, render_template
from models import FlashcardDecks

main_bp = Blueprint('main', __name__)

@main_bp.route("/", methods=["GET"])
def index():
    decks = FlashcardDecks.query.filter(FlashcardDecks.parent_deck_id.is_(None))\
        .order_by(FlashcardDecks.created_at.desc()).all()
    return render_template("index.html", decks=decks)
