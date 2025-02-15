from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import os
import json
from google import genai
from models import db, Topic, Flashcard, Deck
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
    topics = Topic.query.order_by(Topic.created_at.desc()).all()
    return render_template("index.html", topics=topics)

@app.route("/generate", methods=["POST"])
def generate():
    user_input = request.form["topic"]
    batch_size = 100  # Maximum flashcards per request
    
    # Check if topic exists
    topic = Topic.query.filter_by(name=user_input).first()
    if not topic:
        topic = Topic(name=user_input)
        db.session.add(topic)
        db.session.commit()

    # Create a new deck for this generation
    deck = Deck(
        name=f"{user_input} Flashcards",
        description=f"Automatically generated flashcards about {user_input}",
        topic_id=topic.id
    )
    db.session.add(deck)
    db.session.commit()

    client = genai.Client(api_key=api_key)
    prompt_template = f"""You are an expert educator creating flashcards about {user_input}.
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
            
        # Add unique cards to the database
        cards_added = 0
        for card in batch_cards:
            # Check if similar question already exists
            if not Flashcard.query.filter_by(
                deck_id=deck.id, 
                question=card['question']
            ).first():
                flashcard = Flashcard(
                    question=card['question'],
                    correct_answer=card['correct_answer'],
                    incorrect_answers=json.dumps(card['incorrect_answers']),
                    topic_id=topic.id,
                    deck_id=deck.id
                )
                db.session.add(flashcard)
                cards_added += 1
        
        db.session.commit()
        print(f"Successfully added {cards_added} flashcards")
            
    except Exception as e:
        print(f"Error in flashcard generation: {e}")
        db.session.rollback()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "redirect_url": url_for('get_topic_flashcards', topic_id=topic.id)})
    return redirect(url_for('get_topic_flashcards', topic_id=topic.id))

@app.route("/generate_for_deck", methods=["POST"])
def generate_for_deck():
    deck_id = request.form.get("deck_id")
    subtopic = request.form.get("subtopic", "").strip()
    
    deck = Deck.query.get_or_404(deck_id)
    topic = Topic.query.get_or_404(deck.topic_id)
    
    focus = f"{topic.name} - {subtopic}" if subtopic else topic.name
    
    client = genai.Client(api_key=api_key)
    prompt_template = f"""You are an expert educator creating flashcards about {focus}.
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
            if not Flashcard.query.filter_by(
                deck_id=deck_id, 
                question=card['question']
            ).first():
                flashcard = Flashcard(
                    question=card['question'],
                    correct_answer=card['correct_answer'],
                    incorrect_answers=json.dumps(card['incorrect_answers']),
                    topic_id=deck.topic_id,
                    deck_id=deck_id
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

def is_topic_sufficiently_covered(topic_id):
    """Check if the topic has sufficient coverage based on card variety and concepts."""
    flashcards = Flashcard.query.filter_by(topic_id=topic_id).all()
    
    if len(flashcards) < 20:
        return False
        
    # Basic heuristic: check for question variety using keywords
    question_types = {
        'what': 0, 'how': 0, 'why': 0, 'when': 0, 
        'define': 0, 'explain': 0, 'compare': 0, 'analyze': 0
    }
    
    for card in flashcards:
        question = card.question.lower()
        for keyword in question_types:
            if keyword in question:
                question_types[keyword] += 1
                
    # Ensure we have at least 3 different types of questions
    different_types = sum(1 for count in question_types.values() if count > 0)
    return different_types >= 3

@app.route("/topic/<int:topic_id>")
def get_topic_flashcards(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    decks = Deck.query.filter_by(topic_id=topic_id).order_by(Deck.created_at.desc()).all()
    return render_template("topic.html", topic=topic, decks=decks)

@app.route("/deck/<int:deck_id>")
def get_deck_flashcards(deck_id):
    deck = Deck.query.get_or_404(deck_id)
    flashcards = Flashcard.query.filter_by(deck_id=deck_id).all()
    return render_template("flashcards.html", deck=deck, flashcards=flashcards)

@app.route("/deck/create", methods=["POST"])
def create_deck():
    topic_id = request.form.get("topic_id")
    name = request.form.get("name", "New Deck")
    description = request.form.get("description", "")
    
    deck = Deck(
        name=name,
        description=description,
        topic_id=topic_id
    )
    db.session.add(deck)
    db.session.commit()
    
    return jsonify({"success": True, "deck_id": deck.id})

@app.route("/update_progress", methods=["POST"])
def update_progress():
    data = request.json
    flashcard = Flashcard.query.get_or_404(data['flashcard_id'])
    
    if data['is_correct']:
        flashcard.correct_count += 1
    else:
        flashcard.incorrect_count += 1
    
    flashcard.last_reviewed = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})

@app.route("/deck/delete/<int:deck_id>", methods=["DELETE"])
def delete_deck(deck_id):
    """Delete a deck and its associated flashcards."""
    deck = Deck.query.get_or_404(deck_id)
    try:
        # Delete associated flashcards
        flashcards = Flashcard.query.filter_by(deck_id=deck_id).all()
        for flashcard in flashcards:
            db.session.delete(flashcard)
        db.session.delete(deck)
        db.session.commit()
        return jsonify({"success": True, "message": "Deck deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/topic/delete/<int:topic_id>", methods=["DELETE"])
def delete_topic(topic_id):
    """Delete a topic along with its decks and flashcards."""
    topic = Topic.query.get_or_404(topic_id)
    try:
        # Delete decks and their flashcards
        decks = Deck.query.filter_by(topic_id=topic_id).all()
        for deck in decks:
            flashcards = Flashcard.query.filter_by(deck_id=deck.id).all()
            for flashcard in flashcards:
                db.session.delete(flashcard)
            db.session.delete(deck)
        db.session.delete(topic)
        db.session.commit()
        return jsonify({"success": True, "message": "Topic deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/topic/rename/<int:topic_id>", methods=["PUT"])
def rename_topic(topic_id):
    """Rename a topic"""
    topic = Topic.query.get_or_404(topic_id)
    try:
        data = request.json
        topic.name = data.get('name')
        db.session.commit()
        return jsonify({"success": True, "message": "Topic renamed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/deck/rename/<int:deck_id>", methods=["PUT"])
def rename_deck(deck_id):
    """Rename a deck"""
    deck = Deck.query.get_or_404(deck_id)
    try:
        data = request.json
        deck.name = data.get('name')
        deck.description = data.get('description', deck.description)
        db.session.commit()
        return jsonify({"success": True, "message": "Deck renamed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

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