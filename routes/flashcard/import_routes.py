from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
import os
import json
import traceback
from google import genai
from .generation_routes import parse_flashcards
from services.fsrs_scheduler import get_current_time
from config import Config

import_bp = Blueprint('import', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Helper functions to reduce duplication
def create_deck(name, description, parent_deck_id=None):
    """Create a new flashcard deck"""
    deck = FlashcardDecks(
        name=name,
        description=description,
        parent_deck_id=parent_deck_id if parent_deck_id else None
    )
    db.session.add(deck)
    db.session.commit()
    return deck

def generate_flashcards_with_gemini(content, topic, batch_size=None):
    """Generate flashcards using Gemini API"""
    if batch_size is None:
        batch_size = Config.DEFAULT_BATCH_SIZE
        
    api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # Generate prompt using the Config class
    prompt = Config.generate_prompt_template(topic, batch_size)
    
    print(f"Processing content: '{topic}', content length: {len(content)} chars")
    print("Sending request to Gemini API...")
    
    # Use Config.CHUNK_SIZE instead of hard-coded value
    content_for_api = content[:Config.CHUNK_SIZE] if len(content) > Config.CHUNK_SIZE else content
    
    response = client.models.generate_content(
        model=Config.GEMINI_MODEL,
        contents=f"{prompt}\n\nContent:\n{content_for_api}",
        config=Config.GEMINI_CONFIG
    )
    
    # Parse response
    try:
        flashcards_data = json.loads(response.text)
        print(f"Successfully parsed JSON: {len(flashcards_data)} cards")
    except json.JSONDecodeError as parse_error:
        print(f"JSON parsing failed: {parse_error}. Falling back to manual parsing.")
        flashcards_data = parse_flashcards(response.text)
        print(f"Manual parsing result: {len(flashcards_data)} cards extracted")
    
    if not flashcards_data:
        raise ValueError("No flashcards could be generated from this content")
        
    return flashcards_data

def save_flashcards_to_database(flashcards_data, deck_id):
    """Save generated flashcards to database"""
    current_time = get_current_time()
    cards_added = 0
    
    for card in flashcards_data:
        # Convert to dict if it's a Pydantic model
        if hasattr(card, 'model_dump'):
            card = card.model_dump()
        
        # Use the abbreviated field names (with fallback to old names)
        question = card.get('q', card.get('question', ''))
        correct_answer = card.get('ca', card.get('correct_answer', ''))
        incorrect_answers = card.get('ia', card.get('incorrect_answers', []))[:3]
            
        # Pad with empty answers if needed
        while len(incorrect_answers) < 3:
            incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
        
        flashcard = Flashcards(
            question=question,
            correct_answer=correct_answer,
            incorrect_answers=json.dumps(incorrect_answers),
            flashcard_deck_id=deck_id,
            due_date=current_time,
            state=0
        )
        
        db.session.add(flashcard)
        cards_added += 1
    
    db.session.commit()
    return cards_added

def handle_error(error, deck=None):
    """Handle errors in the import process"""
    print(f"Error in processing: {str(error)}")
    print(traceback.format_exc())
    
    # Clean up any created deck
    try:
        if deck:
            db.session.delete(deck)
            db.session.commit()
    except:
        db.session.rollback()
        
    return jsonify({"success": False, "error": str(error)}), 500

@import_bp.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload and generate flashcards from content"""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
        
    file = request.files['file']
    
    # If user does not select file, browser submits an empty part without filename
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    # Check if the file type is allowed
    if not allowed_file(file.filename):
        return jsonify({
            "success": False, 
            "error": f"File type not allowed. Only {', '.join(Config.ALLOWED_EXTENSIONS).upper()} files are supported."
        }), 400
    
    # Get form data
    deck_name = request.form.get('deck_name', 'Imported Content')
    parent_deck_id = request.form.get('parent_deck_id')
    
    try:
        # Read the text content directly from the uploaded file
        file_text = file.read().decode('utf-8', errors='replace')
        current_app.logger.info(f"Read {len(file_text)} characters from uploaded file")
        
        # Check if we have enough text to process
        if len(file_text) < 100:
            return jsonify({
                "success": False, 
                "error": "Not enough text in the file. Please provide a file with more content."
            }), 400
        
        # Create deck
        deck = create_deck(
            name=deck_name,
            description=f"Imported from {secure_filename(file.filename)} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id
        )
        
        # Generate flashcards
        topic = f"content in file: {secure_filename(file.filename)}"
        flashcards_data = generate_flashcards_with_gemini(file_text, topic)
        
        # Save to database
        cards_added = save_flashcards_to_database(flashcards_data, deck.flashcard_deck_id)
        current_app.logger.info(f"Successfully added {cards_added} flashcards to deck {deck_name}")
        
        # Return success response
        return jsonify({
            "success": True, 
            "message": f"Successfully generated {cards_added} flashcards",
            "redirect_url": url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing uploaded file: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return handle_error(e, deck if 'deck' in locals() else None)

@import_bp.route("/process-text", methods=["POST"])
def process_text():
    """Process pasted text to generate flashcards"""
    data = request.json
    text_content = data.get('text', '')
    deck_name = data.get('deck_name', 'Text Import')
    parent_deck_id = data.get('parent_deck_id')
    
    if not text_content or len(text_content) < 50:
        return jsonify({
            "success": False, 
            "error": "Text content is too short. Please provide more content."
        }), 400
    
    try:
        # Create deck
        deck = create_deck(
            name=deck_name,
            description=f"Imported from text on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id
        )
        
        # Generate flashcards
        topic = f"content: {deck_name}"
        flashcards_data = generate_flashcards_with_gemini(text_content, topic)
        
        # Save to database
        cards_added = save_flashcards_to_database(flashcards_data, deck.flashcard_deck_id)
        print(f"Successfully added {cards_added} flashcards to deck {deck_name}")
        
        # Return success response
        return jsonify({
            "success": True, 
            "message": f"Successfully generated {cards_added} flashcards",
            "redirect_url": url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        })
        
    except Exception as e:
        return handle_error(e, deck if 'deck' in locals() else None)