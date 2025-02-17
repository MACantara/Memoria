from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import os
import json
from google import genai
from models import db, FlashcardDecks, Flashcards
from datetime import datetime

load_dotenv()
api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

app = Flask(__name__)
# Update database URL to use postgresql:// instead of postgres://
db_url = os.getenv('POSTGRES_URL_NON_POOLING', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET"])
def index():
    decks = FlashcardDecks.query.filter(FlashcardDecks.parent_deck_id.is_(None))\
        .order_by(FlashcardDecks.created_at.desc()).all()
    return render_template("index.html", decks=decks)

@app.route("/generate", methods=["POST"])
def generate():
    deck_name = request.form["topic"]
    batch_size = 100
    
    # Create a new main deck
    deck = FlashcardDecks(
        name=deck_name,
        description=f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        parent_deck_id=None
    )
    db.session.add(deck)
    db.session.commit()

    client = genai.Client(api_key=api_key)
    prompt_template = f"""You are an expert educator creating flashcards about {deck_name}.
    Generate comprehensive, accurate, and engaging flashcards following these guidelines:

    1. Each flashcard must have:
       - A clear, concise question that tests understanding
       - One definitively correct answer
       - Three plausible but incorrect answers
       - All answers should be roughly the same length and style
    
    2. Question types should include:
       - Factual recall (25% of cards)
       - Concept application (25% of cards)
       - Problem-solving (25% of cards)
       - Relationships between concepts (25% of cards)
    
    3. Ensure:
       - No duplicate questions or answers
       - All content is factually accurate
       - Clear, unambiguous wording
       - Progressive difficulty (easy -> medium -> hard)
    
    4. Format each flashcard exactly as:
    question: [question text]
    correct: [correct answer]
    incorrect: [wrong answer 1]; [wrong answer 2]; [wrong answer 3]

    Generate exactly {batch_size} unique flashcards covering different aspects of the topic.
    Ensure comprehensive coverage by:
    1. Breaking down the topic into key subtopics
    2. Creating equal numbers of cards for each subtopic
    3. Varying question types within each subtopic
    4. Including both fundamental and advanced concepts"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-preview-02-05",
            contents=prompt_template
        )
        
        batch_cards = parse_flashcards(response.text)
        if not batch_cards:
            raise ValueError("No valid flashcards generated")
            
        cards_added = 0
        for card in batch_cards:
            if not Flashcards.query.filter_by(
                flashcard_deck_id=deck.flashcard_deck_id,
                question=card['question']
            ).first():
                flashcard = Flashcards(
                    question=card['question'],
                    correct_answer=card['correct_answer'],
                    incorrect_answers=json.dumps(card['incorrect_answers']),
                    flashcard_deck_id=deck.flashcard_deck_id
                )
                db.session.add(flashcard)
                cards_added += 1
        
        db.session.commit()
        print(f"Successfully added {cards_added} flashcards")
            
    except Exception as e:
        print(f"Error in flashcard generation: {e}")
        db.session.rollback()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "redirect_url": url_for('get_deck_flashcards', deck_id=deck.flashcard_deck_id)})
    return redirect(url_for('get_deck_flashcards', deck_id=deck.flashcard_deck_id))

@app.route("/generate_for_deck", methods=["POST"])
def generate_for_deck():
    deck_id = request.form.get("deck_id")
    subtopic = request.form.get("subtopic", "").strip()
    
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Create a sub-deck for this generation
    sub_deck = FlashcardDecks(
        name=f"{subtopic if subtopic else 'Generated'} {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        description=f"Generated flashcards about {subtopic if subtopic else deck.name}",
        parent_deck_id=deck.flashcard_deck_id
    )
    db.session.add(sub_deck)
    db.session.commit()

    client = genai.Client(api_key=api_key)
    prompt_template = f"""You are an expert educator creating flashcards about {subtopic if subtopic else deck.name}.
    Generate exactly 100 comprehensive, accurate, and engaging flashcards following these guidelines:

    1. Each flashcard must have:
       - A clear, concise question that tests understanding
       - One definitively correct answer
       - Three plausible but incorrect answers
       - All answers should be roughly the same length and style
    
    2. Question types should include:
       - Factual recall (25% of cards)
       - Concept application (25% of cards)
       - Problem-solving (25% of cards)
       - Relationships between concepts (25% of cards)
    
    3. Ensure:
       - No duplicate questions or answers
       - All content is factually accurate
       - Clear, unambiguous wording
       - Progressive difficulty (easy -> medium -> hard)
    
    4. Format each flashcard exactly as:
    question: [question text]
    correct: [correct answer]
    incorrect: [wrong answer 1]; [wrong answer 2]; [wrong answer 3]

    Ensure comprehensive coverage by:
    1. Breaking down the topic into key subtopics
    2. Creating equal numbers of cards for each subtopic
    3. Varying question types within each subtopic
    4. Including both fundamental and advanced concepts"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-preview-02-05",
            contents=prompt_template
        )
        
        batch_cards = parse_flashcards(response.text)
        if not batch_cards:
            return jsonify({"success": False, "error": "No valid flashcards generated"})
            
        cards_added = 0
        for card in batch_cards:
            if not Flashcards.query.filter_by(
                flashcard_deck_id=sub_deck.flashcard_deck_id,
                question=card['question']
            ).first():
                flashcard = Flashcards(
                    question=card['question'],
                    correct_answer=card['correct_answer'],
                    incorrect_answers=json.dumps(card['incorrect_answers']),
                    flashcard_deck_id=sub_deck.flashcard_deck_id
                )
                db.session.add(flashcard)
                cards_added += 1
        
        db.session.commit()
        return jsonify({
            "success": True, 
            "message": f"Successfully added {cards_added} flashcards to deck"
        })
            
    except Exception as e:
        print(f"Error in flashcard generation: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})

@app.route("/deck/<int:deck_id>")
def get_deck_flashcards(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    if deck.parent_deck_id is None:
        # This is a main deck, show its sub-decks
        return render_template("deck.html", deck=deck)
    else:
        # This is a sub-deck, show its flashcards
        flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id).all()
        return render_template("flashcards.html", deck=deck, flashcards=flashcards)

@app.route("/deck/create", methods=["POST"])
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

@app.route("/update_progress", methods=["POST"])
def update_progress():
    data = request.json
    flashcard = Flashcards.query.get_or_404(data['flashcard_id'])
    
    if data['is_correct']:
        flashcard.correct_count += 1
    else:
        flashcard.incorrect_count += 1
    
    flashcard.last_reviewed = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})

def parse_flashcards(text):
    flashcards = []
    flashcard_responses = text.split("question:")

    for card_response in flashcard_responses[1:]:  # Skip first empty split
        try:
            question_start = 0
            correct_start = card_response.lower().index("correct:") + len("correct:")
            incorrect_start = card_response.lower().index("incorrect:") + len("incorrect:")
            
            question = card_response[question_start:correct_start].replace("correct:", "").strip()
            correct_answer = card_response[correct_start:incorrect_start].replace("incorrect:", "").strip()
            incorrect_answers = [
                ans.strip().split('**')[0].strip() # Remove any **text** markers
                for ans in card_response[incorrect_start:].split(";")
                if ans.strip()
            ]

            # Clean up any remaining markdown or extra text
            question = question.replace('*', '').strip()
            correct_answer = correct_answer.replace('*', '').strip()
            
            if len(incorrect_answers) >= 3:  # Ensure we have enough wrong answers
                flashcards.append({
                    "question": question,
                    "correct_answer": correct_answer,
                    "incorrect_answers": incorrect_answers[:3],  # Take only first 3 wrong answers
                })
        except ValueError as e:
            print(f"Error parsing flashcard: {e}")
            continue

    return flashcards

# Configuration for local development
if __name__ == "__main__":
    # Ensure all tables exist
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {e}")

    # Enable debug mode for development
    app.debug = True
    
    # Run the application
    try:
        print("Starting development server...")
        print("Access the application at: http://localhost:5000")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting development server: {e}")