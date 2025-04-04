from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required

from config import Config
from utils import allowed_file
from models import db, FlashcardDecks, Flashcards, ImportFile, ImportChunk, ImportFlashcard
from services.file_service import FileProcessor
from services.storage_service import ProcessingState
from services.chunk_service import process_file_chunk_batch, get_file_state, cleanup_all_flashcards

# Create Blueprint
import_bp = Blueprint('import', __name__, url_prefix='/import')

@import_bp.route('/upload-file', methods=['POST'])
@login_required
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
            
        # Validate deck belongs to current user
        deck = FlashcardDecks.query.filter_by(
            flashcard_deck_id=deck_id, 
            user_id=current_user.id
        ).first()
        
        if not deck:
            return jsonify({'error': 'Invalid deck ID'}), 403

        # Create a safe filename and ensure upload directory exists
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Save file temporarily for processing
        try:
            file.save(filepath)
        except Exception as e:
            current_app.logger.error(f"File save error: {str(e)}")
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Initialize processing state in the database
        file_key = ProcessingState.init_file_state(filepath)
        
        # Update deck ID in the state
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if import_file:
            import_file.deck_id = deck_id
            db.session.commit()
        
        # Clean up old processing states
        ProcessingState.cleanup_old_states()
        
        # Delete the temporary file after processing
        try:
            os.remove(filepath)
        except:
            current_app.logger.warning(f"Failed to delete temporary file: {filepath}")
        
        return jsonify({
            'success': True, 
            'file_key': file_key, 
            'filename': filename,
            'total_chunks': import_file.total_chunks if import_file else 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@import_bp.route('/generate-chunk', methods=['POST'])
@login_required
def generate_chunk():
    """Generate flashcards from a specific chunk of a file"""
    try:
        data = request.get_json()
        file_key = data.get('file_key')
        chunk_index = data.get('chunk_index')
        
        if not file_key:
            return jsonify({'error': 'File key is required'}), 400
        
        # Verify the file belongs to the current user
        import_file = ImportFile.query.filter_by(file_key=file_key, user_id=current_user.id).first()
        if not import_file:
            return jsonify({'error': 'Import file not found or access denied'}), 403
        
        if chunk_index is None:
            chunk_index = import_file.current_index
        
        if chunk_index >= import_file.total_chunks:
            # If all chunks are processed, clean up all flashcards to free up space
            cleanup_all_flashcards(file_key)
            
            return jsonify({
                'message': 'All chunks processed',
                'is_complete': True,
                'total_saved_cards': import_file.total_saved_cards
            })
        
        # Use the processor for generating and auto-saving flashcards from chunks
        result = process_file_chunk_batch(current_app.gemini_client, file_key, chunk_index)
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in generate_chunk: {str(e)}")
        return jsonify({'error': str(e)}), 500

@import_bp.route('/file-state', methods=['GET'])
@login_required
def file_state():
    """Get current processing state for a file"""
    file_key = request.args.get('file_key')
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    # Verify the file belongs to the current user
    import_file = ImportFile.query.filter_by(file_key=file_key, user_id=current_user.id).first()
    if not import_file:
        return jsonify({'error': 'Import file not found or access denied'}), 403
    
    # Get file state info
    result = {
        'total_chunks': import_file.total_chunks,
        'processed_chunks': import_file.processed_chunks_count,
        'current_index': import_file.current_index,
        'flashcard_count': ImportFlashcard.query.filter_by(file_id=import_file.id).count(),
        'is_complete': import_file.is_complete,
        'next_chunk': import_file.current_index if import_file.current_index < import_file.total_chunks else None,
        'total_saved_cards': import_file.total_saved_cards,
        'saved_chunks': import_file.saved_chunks
    }
    
    return jsonify(result)

@import_bp.route('/all-file-flashcards', methods=['GET'])
@login_required
def all_file_flashcards():
    """Get all flashcards for a file"""
    file_key = request.args.get('file_key')
    format_type = request.args.get('format', 'standard')  # 'standard' or 'mc' (multiple-choice)
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    # Verify the file belongs to the current user
    import_file = ImportFile.query.filter_by(file_key=file_key, user_id=current_user.id).first()
    if not import_file:
        return jsonify({'error': 'Import file not found or access denied'}), 403
    
    if format_type == 'mc':
        # Return multiple-choice format for the frontend
        flashcards = ImportFlashcard.query.filter_by(file_id=import_file.id).all()
        
        mc_flashcards = [{
            'q': card.question,
            'ca': card.correct_answer,
            'ia': card.incorrect_answers
        } for card in flashcards]
        
        # Also include simple format for backward compatibility
        simple_format = [f"Q: {card.question} | A: {card.correct_answer}" for card in flashcards]
        
        return jsonify({
            'flashcards': simple_format,
            'mc_flashcards': mc_flashcards,
            'count': len(flashcards),
            'total_saved_cards': import_file.total_saved_cards
        })
    else:
        # Return standard format by default
        flashcards = ImportFlashcard.query.filter_by(file_id=import_file.id).all()
        simple_format = [f"Q: {card.question} | A: {card.correct_answer}" for card in flashcards]
        
        return jsonify({
            'flashcards': simple_format,
            'count': len(flashcards),
            'total_saved_cards': import_file.total_saved_cards
        })

@import_bp.route('/save-to-deck', methods=['POST'])
@login_required
def save_to_deck():
    """
    Manual save endpoint for backward compatibility
    Used if auto-save fails for some reason
    """
    try:
        data = request.get_json()
        file_key = data.get('file_key')
        deck_id = data.get('deck_id')
        flashcards = data.get('flashcards', [])
        
        if not file_key:
            return jsonify({'error': 'File key is required'}), 400
            
        if not deck_id:
            return jsonify({'error': 'Deck ID is required'}), 400
            
        # Verify the file belongs to the current user
        import_file = ImportFile.query.filter_by(file_key=file_key, user_id=current_user.id).first()
        if not import_file:
            return jsonify({'error': 'Import file not found or access denied'}), 403
            
        # Verify the deck belongs to the current user
        deck = FlashcardDecks.query.filter_by(
            flashcard_deck_id=deck_id, 
            user_id=current_user.id
        ).first()
        
        if not deck:
            return jsonify({'error': 'Invalid deck ID'}), 403
        
        # No flashcards provided, get unsaved ones from database
        if not flashcards:
            unsaved_cards = ImportFlashcard.query.filter_by(
                file_id=import_file.id,
                is_saved=False
            ).all()
            
            flashcards = [{
                'q': card.question,
                'ca': card.correct_answer,
                'ia': card.incorrect_answers
            } for card in unsaved_cards]
        
        if not flashcards:
            return jsonify({'error': 'No flashcards found for this file'}), 400
        
        # Save each flashcard to the database
        cards_added = 0
        # Get current time for all cards to use same timestamp
        from services.fsrs_scheduler import get_current_time
        current_time = get_current_time()
        
        for card in flashcards:
            # Extract and validate required fields
            question = card.get('q', '')
            correct_answer = card.get('ca', '')
            incorrect_answers = card.get('ia', [])
            
            # Skip incomplete cards
            if not question or not correct_answer:
                current_app.logger.warning(f"Skipping incomplete card: {card}")
                continue
            
            # Ensure incorrect_answers is a list and limit to 3 items
            if not isinstance(incorrect_answers, list):
                incorrect_answers = [str(incorrect_answers)]
            incorrect_answers = incorrect_answers[:3]
            
            # Pad with empty answers if needed
            while len(incorrect_answers) < 3:
                incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
            
            # Create a new flashcard
            new_card = Flashcards(
                question=question,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers,
                flashcard_deck_id=int(deck_id),
                due_date=current_time,
                state=0
            )
            
            # Initialize FSRS state for the new card
            new_card.init_fsrs_state()
            
            # Add to session
            db.session.add(new_card)
            cards_added += 1
            
            # Mark as saved in the import flashcards table
            if import_file:
                import_card = ImportFlashcard.query.filter_by(
                    file_id=import_file.id,
                    question=question,
                    correct_answer=correct_answer
                ).first()
                
                if import_card:
                    import_card.is_saved = True
        
        # Commit all changes at once
        db.session.commit()
        current_app.logger.info(f"Added {cards_added} flashcards to deck {deck_id}")
        
        # Update total saved count in import file
        if import_file:
            import_file.total_saved_cards += cards_added
            
            # If this was the last batch of cards, clean up all flashcards
            if import_file.is_complete:
                cleanup_all_flashcards(file_key)
            
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {cards_added} flashcards to deck',
            'count': cards_added,
            'total_saved_cards': import_file.total_saved_cards if import_file else cards_added
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving flashcards to deck: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Failed to save flashcards to deck: {str(e)}'}), 500

@import_bp.route('/saved-status', methods=['GET'])
@login_required
def get_saved_status():
    """Get the saved status for a file processing job"""
    file_key = request.args.get('file_key')
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    # Verify the file belongs to the current user
    import_file = ImportFile.query.filter_by(file_key=file_key, user_id=current_user.id).first()
    if not import_file:
        return jsonify({'error': 'Import file not found or access denied'}), 403
    
    # Get saved chunks
    saved_chunks = [chunk.index for chunk in ImportChunk.query.filter_by(
        file_id=import_file.id,
        is_saved=True
    ).all()]
    
    # Calculate percentage complete for saving
    save_progress = 0
    if import_file.total_chunks > 0:
        save_progress = int(len(saved_chunks) / import_file.total_chunks * 100)
    
    return jsonify({
        'file_key': file_key,
        'total_chunks': import_file.total_chunks,
        'saved_chunks': len(saved_chunks),
        'saved_chunks_list': saved_chunks,
        'save_progress': save_progress,
        'is_complete': import_file.is_complete,
        'total_saved_cards': import_file.total_saved_cards,
        'fully_saved': len(saved_chunks) == import_file.total_chunks and import_file.is_complete,
        'deck_id': import_file.deck_id
    })
