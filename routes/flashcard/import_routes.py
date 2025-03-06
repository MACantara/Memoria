from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
import os
import json
import traceback
import uuid
from google import genai

from services.file_service import FileProcessor
from services.storage_service import ProcessingState
from utils import chunk_text, clean_flashcard_text
from services.fsrs_scheduler import get_current_time
from config import Config

import_bp = Blueprint('import', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@import_bp.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload and initialize processing"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file part"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No selected file"}), 400
            
        if not allowed_file(file.filename):
            return jsonify({
                "success": False, 
                "error": f"File type not allowed. Only {', '.join(Config.ALLOWED_EXTENSIONS).upper()} files are supported."
            }), 400

        # Create a safe filename and ensure upload directory exists
        filename = secure_filename(file.filename)
        deck_name = request.form.get('deck_name', 'Imported Content')
        parent_deck_id = request.form.get('parent_deck_id')
        
        # Create a unique filename to prevent collisions
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Save file safely
        try:
            file.save(filepath)
        except Exception as e:
            print(f"File save error: {str(e)}")
            return jsonify({"success": False, "error": "Failed to save file"}), 500
            
        # Create a deck for the imported content
        deck = FlashcardDecks(
            name=deck_name,
            description=f"Imported from {filename} on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id if parent_deck_id else None
        )
        db.session.add(deck)
        db.session.commit()
        
        # Initialize processing state
        file_key = ProcessingState.init_file_state(filepath)
        state = ProcessingState.get_state(file_key)
        
        # Store the deck ID in the state for later use
        state['deck_id'] = deck.flashcard_deck_id
        ProcessingState.update_state(file_key, state)
        
        # Clean up old processing states
        ProcessingState.cleanup_old_states()
        
        return jsonify({
            "success": True, 
            "file_key": file_key, 
            "filename": filename,
            "deck_id": deck.flashcard_deck_id,
            "total_chunks": state['total_chunks'],
            "message": f"File uploaded successfully. Processing in {state['total_chunks']} chunks."
        })
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        print(traceback.format_exc())
        
        # Clean up any created deck
        try:
            if 'deck' in locals() and deck:
                db.session.delete(deck)
                db.session.commit()
        except:
            db.session.rollback()
            
        return jsonify({"success": False, "error": str(e)}), 500

@import_bp.route("/process-chunk", methods=["POST"])
def process_chunk():
    """Process a specific chunk of an uploaded file"""
    data = request.json
    file_key = data.get('file_key')
    chunk_index = data.get('chunk_index')
    
    if not file_key:
        return jsonify({"success": False, "error": "File key is required"}), 400
    
    state = ProcessingState.get_state(file_key)
    if not state:
        return jsonify({"success": False, "error": "Invalid file key"}), 400
    
    deck_id = state.get('deck_id')
    if not deck_id:
        return jsonify({"success": False, "error": "No associated deck found"}), 400
    
    if chunk_index is None:
        chunk_index = state['current_index']
    
    if chunk_index >= state['total_chunks']:
        return jsonify({
            "success": True,
            "message": "All chunks processed",
            "is_complete": True,
            "deck_id": deck_id
        })
    
    try:
        # Get chunk content
        chunk = ProcessingState.get_chunk(file_key, chunk_index)
        if not chunk:
            return jsonify({"success": False, "error": f"Cannot read chunk {chunk_index}"}), 500
        
        # Process the chunk with Gemini
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # Generate prompt for this chunk
        prompt = Config.generate_prompt_template(f"content from chunk {chunk_index+1}", 
                                                Config.DEFAULT_BATCH_SIZE)
        
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=f"{prompt}\n\nContent:\n{chunk}",
            config=Config.GEMINI_CONFIG
        )
        
        chunk_flashcards = []
        mc_data = []
        
        # Try to parse JSON response
        try:
            flashcards_data = json.loads(response.text)
            
            # Format flashcards for compatibility with existing UI
            for card in flashcards_data:
                # Format: Q: [question] | A: [correct_answer]
                formatted_card = f"Q: {card['q']} | A: {card['ca']}"
                chunk_flashcards.append(formatted_card)
                mc_data.append(card)
                
        except json.JSONDecodeError:
            # Fallback to legacy format if JSON parsing fails
            raw_cards = response.text.split('\n')
            for card in raw_cards:
                if 'Q:' in card and '|' in card and 'A:' in card:
                    cleaned = clean_flashcard_text(card)
                    if cleaned:
                        chunk_flashcards.append(cleaned)
        
        # Store the multiple-choice data if available
        if mc_data:
            ProcessingState.append_mc_flashcards(file_key, mc_data)
            
        # Also store the formatted cards for backward compatibility
        ProcessingState.append_flashcards(file_key, chunk_flashcards)
        
        # Save to database
        current_time = get_current_time()
        cards_added = 0
        
        for card in mc_data:
            # Use the abbreviated field names
            question = card.get('q', '')
            correct_answer = card.get('ca', '')
            incorrect_answers = card.get('ia', [])[:3]
                
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
        
        # Update processing state
        state['processed_chunks'].append(chunk_index)
        state['current_index'] = chunk_index + 1
        
        if len(state['processed_chunks']) == state['total_chunks']:
            state['is_complete'] = True
        
        ProcessingState.update_state(file_key, state)
        
        return jsonify({
            "success": True,
            "chunk_index": chunk_index,
            "cards_added": cards_added,
            "total_chunks": state['total_chunks'],
            "processed_chunks": len(state['processed_chunks']),
            "is_complete": state['is_complete'],
            "deck_id": deck_id
        })
        
    except Exception as e:
        print(f"Error processing chunk {chunk_index}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@import_bp.route("/file-state", methods=["GET"])
def file_state():
    """Get current processing state for a file"""
    file_key = request.args.get('file_key')
    
    if not file_key:
        return jsonify({"success": False, "error": "File key is required"}), 400
    
    state = ProcessingState.get_state(file_key)
    if not state:
        return jsonify({"success": False, "error": "Invalid file key"}), 400
    
    all_flashcards = ProcessingState.get_all_flashcards(file_key)
    
    return jsonify({
        "success": True,
        "total_chunks": state['total_chunks'],
        "processed_chunks": len(state['processed_chunks']),
        "current_index": state['current_index'],
        "flashcard_count": len(all_flashcards),
        "is_complete": state['is_complete'],
        "deck_id": state.get('deck_id'),
        "next_chunk": state['current_index'] if state['current_index'] < state['total_chunks'] else None
    })

@import_bp.route("/process-text", methods=["POST"])
def process_text():
    """Process pasted text"""
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
        
        # Create a temporary file to store the text
        temp_dir = Config.UPLOAD_FOLDER
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file = os.path.join(temp_dir, f"{uuid.uuid4()}.txt")
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Initialize processing state
        file_key = ProcessingState.init_file_state(temp_file)
        state = ProcessingState.get_state(file_key)
        
        # Store the deck ID in the state
        state['deck_id'] = deck.flashcard_deck_id
        ProcessingState.update_state(file_key, state)
        
        return jsonify({
            "success": True,
            "file_key": file_key,
            "deck_id": deck.flashcard_deck_id,
            "total_chunks": state['total_chunks'],
            "message": f"Text imported successfully. Processing in {state['total_chunks']} chunks."
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

@import_bp.route("/all-flashcards", methods=["GET"])
def all_flashcards():
    """Get all flashcards generated for a file"""
    file_key = request.args.get('file_key')
    format_type = request.args.get('format', 'standard')  # 'standard' or 'mc' (multiple-choice)
    
    if not file_key:
        return jsonify({"success": False, "error": "File key is required"}), 400
    
    state = ProcessingState.get_state(file_key)
    if not state:
        return jsonify({"success": False, "error": "Invalid file key"}), 400
    
    if format_type == 'mc':
        # Return multiple-choice format if requested
        mc_flashcards = ProcessingState.get_mc_flashcards(file_key)
        return jsonify({
            "success": True,
            "flashcards": ProcessingState.get_all_flashcards(file_key),  # For backward compatibility
            "mc_flashcards": mc_flashcards,
            "count": len(mc_flashcards),
            "deck_id": state.get('deck_id')
        })
    else:
        # Return standard format by default
        all_flashcards = ProcessingState.get_all_flashcards(file_key)
        return jsonify({
            "success": True,
            "flashcards": all_flashcards,
            "count": len(all_flashcards),
            "deck_id": state.get('deck_id')
        })