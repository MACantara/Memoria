from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
import os
import json
import traceback
from google import genai
# Import functions from flashcard_generation_routes instead of duplicating them
from routes.flashcard_generation_routes import (
    parse_flashcards, generate_prompt_template
)
from services.fsrs_scheduler import get_current_time

import_bp = Blueprint('import', __name__)

# Configuration - only txt files are allowed
ALLOWED_EXTENSIONS = {'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        
    # Check if the file type is allowed (only txt now)
    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "File type not allowed. Only TXT files are supported."}), 400
    
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
        
        # Create a deck for the imported content
        deck = FlashcardDecks(
            name=deck_name,
            description=f"Imported from {secure_filename(file.filename)} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id if parent_deck_id else None
        )
        db.session.add(deck)
        db.session.commit()
        
        batch_size = 100
        
        # Process the text with Gemini
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # Generate prompt using the existing function from flashcard_generation_routes
        prompt = generate_prompt_template(f"content in file: {secure_filename(file.filename)}", batch_size)
        
        # Use schema as a simple dictionary instead of Pydantic model
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "correct_answer": {"type": "string"},
                    "incorrect_answers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 3
                    }
                },
                "required": ["question", "correct_answer", "incorrect_answers"]
            }
        }
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=f"{prompt}\n\nContent:\n{file_text}",
            config={
                'response_mime_type': 'application/json',
                'response_schema': schema
            }
        )
        
        # Get parsed flashcards or fall back to manual parsing
        try:
            # Try to parse the response as JSON
            flashcards_data = json.loads(response.text)
            current_app.logger.info(f"Successfully parsed JSON output: {len(flashcards_data)} cards")
        except json.JSONDecodeError as parse_error:
            # Fallback to manual parsing if JSON parsing fails
            current_app.logger.warning(f"JSON parsing failed: {parse_error}. Falling back to manual parsing.")
            flashcards_data = parse_flashcards(response.text)
        
        if not flashcards_data:
            current_app.logger.warning("No flashcards were generated from the content")
            raise ValueError("No flashcards could be generated from this content")
        
        # Set current time for all cards to use same timestamp
        current_time = get_current_time()
        
        # Save to database
        cards_added = 0
        for card in flashcards_data:
            # Convert to dict if it's a Pydantic model
            if hasattr(card, 'model_dump'):
                card = card.model_dump()
                
            # Make sure we have at least one incorrect answer
            incorrect_answers = card['incorrect_answers'][:3]
            # Pad with empty answers if needed
            while len(incorrect_answers) < 3:
                incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
            
            flashcard = Flashcards(
                question=card['question'],
                correct_answer=card['correct_answer'],
                incorrect_answers=json.dumps(incorrect_answers),
                flashcard_deck_id=deck.flashcard_deck_id,
                due_date=current_time,  # Set due date to current time
                state=0  # Explicitly set to NEW_STATE
            )
            
            db.session.add(flashcard)
            cards_added += 1
        
        db.session.commit()
        current_app.logger.info(f"Successfully added {cards_added} flashcards to deck {deck_name}")
        
        # Return success response
        return jsonify({
            "success": True, 
            "message": f"Successfully generated {cards_added} flashcards",
            "redirect_url": url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing uploaded file: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        # Clean up any created deck
        try:
            if 'deck' in locals() and deck:
                db.session.delete(deck)
                db.session.commit()
        except:
            db.session.rollback()
            
        return jsonify({"success": False, "error": str(e)}), 500

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
        # Create a deck for the imported content
        deck = FlashcardDecks(
            name=deck_name,
            description=f"Generated from text on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id if parent_deck_id else None
        )
        db.session.add(deck)
        db.session.commit()
        
        # Use Gemini to process the text and generate flashcards
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # Generate prompt using the existing function from flashcard_generation_routes
        batch_size = 100
        prompt = generate_prompt_template("pasted text content", batch_size)
        
        # Use schema as a simple dictionary instead of Pydantic model
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "correct_answer": {"type": "string"},
                    "incorrect_answers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 3
                    }
                },
                "required": ["question", "correct_answer", "incorrect_answers"]
            }
        }
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=f"{prompt}\n\nContent:\n{text_content}",
            config={
                'response_mime_type': 'application/json',
                'response_schema': schema
            }
        )
        
        # Get parsed flashcards or fall back to manual parsing
        try:
            # Try to parse the response as JSON
            flashcards_data = json.loads(response.text)
            current_app.logger.info(f"Successfully parsed JSON output: {len(flashcards_data)} cards")
        except json.JSONDecodeError as parse_error:
            # Fallback to manual parsing if JSON parsing fails
            current_app.logger.warning(f"JSON parsing failed: {parse_error}. Falling back to manual parsing.")
            flashcards_data = parse_flashcards(response.text)
        
        if not flashcards_data:
            raise ValueError("No flashcards could be generated from this content")
        
        # Set current time for all cards to use same timestamp
        current_time = get_current_time()
        
        # Save to database - same code as in upload_file
        cards_added = 0
        for card in flashcards_data:
            # Convert to dict if it's a Pydantic model
            if hasattr(card, 'model_dump'):
                card = card.model_dump()
                
            # Make sure we have at least one incorrect answer
            incorrect_answers = card['incorrect_answers'][:3]
            # Pad with empty answers if needed
            while len(incorrect_answers) < 3:
                incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
                
            flashcard = Flashcards(
                question=card['question'],
                correct_answer=card['correct_answer'],
                incorrect_answers=json.dumps(incorrect_answers),
                flashcard_deck_id=deck.flashcard_deck_id,
                due_date=current_time,  # Set due date to current time
                state=0  # Explicitly set to NEW_STATE
            )
            
            db.session.add(flashcard)
            cards_added += 1
        
        db.session.commit()
        
        # Return success response
        return jsonify({
            "success": True, 
            "message": f"Successfully generated {cards_added} flashcards",
            "redirect_url": url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing text content: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        # Clean up any created deck
        try:
            if 'deck' in locals() and deck:
                db.session.delete(deck)
                db.session.commit()
        except:
            db.session.rollback()
            
        return jsonify({"success": False, "error": str(e)}), 500
