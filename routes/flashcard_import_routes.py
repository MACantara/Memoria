from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
import os
import json
import tempfile
import shutil
from google import genai
import traceback
from routes.flashcard_generation_routes import parse_flashcards, generate_prompt_template

import_bp = Blueprint('import', __name__)

# Configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../temp_uploads')

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        
    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "File type not allowed"}), 400

    # Safely store the file in a temporary location
    temp_dir = tempfile.mkdtemp(dir=UPLOAD_FOLDER)
    filename = secure_filename(file.filename)
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)
    
    # Get other form data
    deck_name = request.form.get('deck_name', 'Imported Content')
    parent_deck_id = request.form.get('parent_deck_id')
    
    try:
        # Create a deck for the imported content
        deck = FlashcardDecks(
            name=deck_name,
            description=f"Imported from {filename} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id if parent_deck_id else None
        )
        db.session.add(deck)
        db.session.commit()
        
        # Use Gemini to process the file and generate flashcards
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # Upload file to Gemini
        uploaded_file = client.files.upload(file=file_path)
        
        # Generate content based on file
        # Use a modified version of the proven prompt
        file_content_prompt = f"""{generate_prompt_template('the document content', 15).split('Generate exactly')[0]}"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",  # For file processing
            contents=[file_content_prompt, uploaded_file]
        )
        
        # Parse the generated flashcards using the existing function
        flashcards_data = parse_flashcards(response.text)
        
        # Save to database
        cards_added = 0
        for card in flashcards_data:
            flashcard = Flashcards(
                question=card['question'],
                correct_answer=card['correct_answer'],
                incorrect_answers=json.dumps(card['incorrect_answers']),
                flashcard_deck_id=deck.flashcard_deck_id
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
        current_app.logger.error(f"Error processing uploaded file: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        # Clean up any created deck
        try:
            if 'deck' in locals():
                db.session.delete(deck)
                db.session.commit()
        except:
            db.session.rollback()
            
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        # Clean up temporary files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            current_app.logger.error(f"Error cleaning up temp files: {str(e)}")

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
        
        # Generate content based on text using the existing prompt template
        batch_size = 100
        
        prompt = f"""{generate_prompt_template({text_content}, batch_size)}"""

        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",  # For text processing
            contents=prompt
        )
        
        # Parse the generated flashcards using the existing function
        flashcards_data = parse_flashcards(response.text)
        
        # Save to database
        cards_added = 0
        for card in flashcards_data:
            flashcard = Flashcards(
                question=card['question'],
                correct_answer=card['correct_answer'],
                incorrect_answers=json.dumps(card['incorrect_answers']),
                flashcard_deck_id=deck.flashcard_deck_id
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
            if 'deck' in locals():
                db.session.delete(deck)
                db.session.commit()
        except:
            db.session.rollback()
            
        return jsonify({"success": False, "error": str(e)}), 500
