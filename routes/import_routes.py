from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from werkzeug.utils import secure_filename

from config import Config
from utils import allowed_file
from models.flashcard import Flashcards
from models import db
from services.file_service import FileProcessor
from services.storage_service import ProcessingState
from services.chunk_service import process_file_chunk_batch, get_file_state

# Create Blueprint
import_bp = Blueprint('import', __name__, url_prefix='/import')

@import_bp.route('/upload-file', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Make sure deck_id is provided
        deck_id = request.form.get('deck_id')
        if not deck_id:
            return jsonify({'error': 'Deck ID is required'}), 400

        # Create a safe filename and ensure upload directory exists
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Save file safely
        try:
            file.save(filepath)
        except Exception as e:
            current_app.logger.error(f"File save error: {str(e)}")
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Initialize processing state
        file_key = ProcessingState.init_file_state(filepath)
        state = ProcessingState.get_state(file_key)
        
        # Store deck_id with file_key for later use
        state['deck_id'] = deck_id
        ProcessingState.update_state(file_key, state)
        
        # Clean up old processing states
        ProcessingState.cleanup_old_states()
        
        return jsonify({
            'success': True, 
            'file_key': file_key, 
            'filename': filename,
            'total_chunks': state['total_chunks']
        })
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@import_bp.route('/generate-chunk', methods=['POST'])
def generate_chunk():
    """Generate flashcards from a specific chunk of a file"""
    try:
        data = request.get_json()
        file_key = data.get('file_key')
        chunk_index = data.get('chunk_index')
        
        if not file_key:
            return jsonify({'error': 'File key is required'}), 400
        
        state = ProcessingState.get_state(file_key)
        if not state:
            return jsonify({'error': 'Invalid file key'}), 400
        
        if chunk_index is None:
            chunk_index = state['current_index']
        
        if chunk_index >= state['total_chunks']:
            return jsonify({
                'message': 'All chunks processed',
                'is_complete': True
            })
        
        # Use the reference processor for generating flashcards from chunks
        result = process_file_chunk_batch(current_app.gemini_client, file_key, chunk_index)
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in generate_chunk: {str(e)}")
        return jsonify({'error': str(e)}), 500

@import_bp.route('/file-state', methods=['GET'])
def file_state():
    """Get current processing state for a file"""
    file_key = request.args.get('file_key')
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    result = get_file_state(file_key)
    return jsonify(result)

@import_bp.route('/all-file-flashcards', methods=['GET'])
def all_file_flashcards():
    """Get all flashcards for a file"""
    file_key = request.args.get('file_key')
    format_type = request.args.get('format', 'standard')  # 'standard' or 'mc' (multiple-choice)
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    if format_type == 'mc':
        # Return multiple-choice format if requested
        mc_flashcards = ProcessingState.get_mc_flashcards(file_key)
        return jsonify({
            'flashcards': ProcessingState.get_all_flashcards(file_key),  # For backward compatibility
            'mc_flashcards': mc_flashcards,
            'count': len(mc_flashcards)
        })
    else:
        # Return standard format by default
        all_flashcards = ProcessingState.get_all_flashcards(file_key)
        return jsonify({
            'flashcards': all_flashcards,
            'count': len(all_flashcards)
        })

@import_bp.route('/save-to-deck', methods=['POST'])
def save_to_deck():
    """Save generated flashcards to a deck"""
    try:
        data = request.get_json()
        file_key = data.get('file_key')
        deck_id = data.get('deck_id')
        
        if not file_key:
            return jsonify({'error': 'File key is required'}), 400
            
        if not deck_id:
            return jsonify({'error': 'Deck ID is required'}), 400
            
        # Get all multiple choice flashcards generated from this file
        mc_flashcards = ProcessingState.get_mc_flashcards(file_key)
        
        if not mc_flashcards:
            return jsonify({'error': 'No flashcards found for this file'}), 400
            
        # Save each flashcard to the database
        cards_added = 0
        for card in mc_flashcards:
            new_card = Flashcards(
                question=card['q'],
                correct_answer=card['ca'],
                incorrect_answers=card['ia'],
                flashcard_deck_id=deck_id
            )
            
            # Initialize FSRS state for the new card
            new_card.init_fsrs_state()
            
            db.session.add(new_card)
            cards_added += 1
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {cards_added} flashcards to deck',
            'count': cards_added
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving flashcards to deck: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save flashcards to deck'}), 500
