from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
import os
import json
import traceback
from google import genai
# Import functions from generation_routes using relative import
from .generation_routes import (
    parse_flashcards
)
from services.fsrs_scheduler import get_current_time
from config import Config

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
        
        batch_size = Config.DEFAULT_BATCH_SIZE
        
        # Process the text with Gemini
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # Generate prompt using the Config class
        prompt = Config.generate_prompt_template(f"content in file: {secure_filename(file.filename)}", batch_size)
        
        print(f"Processing file upload: '{file.filename}', content length: {len(file_text)} chars")
        
        print("Sending request to Gemini API...")
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=f"{prompt}\n\nContent:\n{file_text[:1000]}..." if len(file_text) > 1000 else f"{prompt}\n\nContent:\n{file_text}",
            config=Config.GEMINI_CONFIG
        )
        
        # Try to parse the response as JSON
        try:
            # Try to parse the response as JSON
            flashcards_data = json.loads(response.text)
            current_app.logger.info(f"Successfully parsed JSON output: {len(flashcards_data)} cards")
            print(f"Successfully parsed JSON: {len(flashcards_data)} cards")
            
        except json.JSONDecodeError as parse_error:
            # Fallback to manual parsing if JSON parsing fails
            print(f"JSON parsing failed: {parse_error}. Falling back to manual parsing.")
            print(f"Response text type: {type(response.text)}")
            flashcards_data = parse_flashcards(response.text)
            print(f"Manual parsing result: {len(flashcards_data)} cards extracted")
        
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
            # Update URL to use the correct endpoint
            "redirect_url": url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing uploaded file: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        print(f"Error in file upload processing: {str(e)}")
        print(traceback.format_exc())  # Print full stack trace for debugging
        
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
            description=f"Imported from text on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id if parent_deck_id else None
        )
        db.session.add(deck)
        db.session.commit()
        
        batch_size = Config.DEFAULT_BATCH_SIZE
        
        # Process the text with Gemini
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # Generate prompt using the existing function from generation_routes
        prompt = generate_prompt_template(f"content: {deck_name}", batch_size)
        
        print(f"Processing text import: '{deck_name}', content length: {len(text_content)} chars")
        
        content_for_api = text_content
        
        print("Sending request to Gemini API...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=f"{prompt}\n\nContent:\n{content_for_api}",
            config={
                'response_mime_type': 'application/json',
                'response_schema': schema
            }
        )
        
        # Try to parse the response as JSON
        try:
            flashcards_data = json.loads(response.text)
            print(f"Successfully parsed JSON: {len(flashcards_data)} cards")
        except json.JSONDecodeError as parse_error:
            # Fallback to manual parsing if JSON parsing fails
            print(f"JSON parsing failed: {parse_error}. Falling back to manual parsing.")
            flashcards_data = parse_flashcards(response.text)
            print(f"Manual parsing result: {len(flashcards_data)} cards extracted")
        
        if not flashcards_data:
            raise ValueError("No flashcards could be generated from this content")
        
        # Set current time for all cards to use same timestamp
        current_time = get_current_time()
        
        # Save to database
        cards_added = 0
        for card in flashcards_data:
            if hasattr(card, 'model_dump'):
                card = card.model_dump()
                
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
                flashcard_deck_id=deck.flashcard_deck_id,
                due_date=current_time,
                state=0
            )
            
            db.session.add(flashcard)
            cards_added += 1
        
        db.session.commit()
        print(f"Successfully added {cards_added} flashcards to deck {deck_name}")
        
        # Return success response
        return jsonify({
            "success": True, 
            "message": f"Successfully generated {cards_added} flashcards",
            # Update URL to use the correct endpoint
            "redirect_url": url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        })
        
    except Exception as e:
        print(f"Error in text processing: {str(e)}")
        print(traceback.format_exc())
        
        # Clean up any created deck
        try:
            if 'deck' in locals() and deck:
                db.session.delete(deck)
                db.session.commit()
        except:
            db.session.rollback()
            
        return jsonify({"success": False, "error": str(e)}), 500