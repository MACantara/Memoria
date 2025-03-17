from flask import request, jsonify, current_app, url_for
from flask_login import current_user, login_required
from routes.learning import learning_bp
from models import db, LearningSession, LearningSection, LearningQuestion
from google import genai
import json
import os
from config import Config
import traceback
from datetime import datetime

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@learning_bp.route('/api/section/<int:section_id>', methods=['GET'])
@login_required
def get_section_data(section_id):
    """API endpoint to get section data for the unified learning flow"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership through the session
    if section.session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Return section data
    return jsonify({
        "id": section.learning_section_id,
        "title": section.title,
        "content": section.content,
        "order": section.order,
        "is_completed": section.is_completed,
        "session_id": section.learning_session_id
    })

@learning_bp.route('/api/section/<int:section_id>/generate-content', methods=['POST'])
@login_required
def api_generate_section_content(section_id):
    """API endpoint to generate content for a section"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership
    if section.session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Create a prompt for generating concise section content
        prompt = f"""
        I'm learning about: {section.session.topic}
        
        Create concise, focused learning content for this specific section:
        "{section.title}"
        
        Requirements:
        1. Keep content brief but substantive (approximately 250-350 words)
        2. Focus on core concepts and essential knowledge
        3. Use simple language and explain technical terms
        4. Include 1-2 clear examples or applications
        5. Use bullet points or short paragraphs for readability
        6. Format with HTML for structure (use h3, p, ul, li tags)
        
        The goal is to help me understand this topic without overwhelming me with too much information.
        """
        
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config=Config.LEARNING_GEMINI_CONFIG
        )
        
        # Make sure content is a string
        content_text = response.text
        if not isinstance(content_text, str):
            content_text = str(content_text)
            
        # Save the generated content
        section.content = content_text
        section.session.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Content generated successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating content: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/section/<int:section_id>/mark-read', methods=['POST'])
@login_required
def api_mark_section_read(section_id):
    """API endpoint to mark a section as read and generate questions"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership
    if section.session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    try:
        # Generate questions for this section
        from routes.learning.interaction_routes import generate_section_questions
        questions_generated = generate_section_questions(section_id)
        
        if questions_generated:
            # Update session step to move to questions mode
            session = section.session
            session.current_step = 'question'
            db.session.commit()
            
            # Get the questions to return
            questions = LearningQuestion.query.filter_by(learning_section_id=section_id).all()
            questions_data = [q.to_dict() for q in questions]
            
            return jsonify({
                "success": True,
                "message": "Questions generated successfully",
                "questions": questions_data
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to generate questions. Please try again."
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error marking section read: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/question/answer', methods=['POST'])
@login_required
def api_answer_question():
    """API endpoint to record a user's answer to a question"""
    try:
        data = request.json
        question_id = data.get('question_id')
        answer = data.get('answer')
        is_correct = data.get('is_correct', False)
        
        # Get the question
        question = LearningQuestion.query.get_or_404(question_id)
        
        # Verify ownership
        if question.session.user_id != current_user.id:
            return jsonify({"error": "Unauthorized access"}), 403
        
        # Record the answer
        question.user_answer = answer
        question.is_correct = is_correct
        question.attempts += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Answer recorded successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error recording answer: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/section/<int:section_id>/complete', methods=['POST'])
@login_required
def api_mark_section_complete(section_id):
    """API endpoint to mark a section as completed"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership
    if section.session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized access"}), 403
    
    # Mark as completed
    section.is_completed = True
    section.session.last_updated = datetime.utcnow()
    
    # Check if all sections are complete
    all_sections = LearningSection.query.filter_by(
        learning_session_id=section.learning_session_id
    ).all()
    all_completed = all(s.is_completed for s in all_sections)
    if all_completed:
        section.session.status = 'completed'
    
    # Get next section
    next_section = None
    for s in all_sections:
        if s.order == section.order + 1:
            next_section = s
            break
    
    # Generate content for next section if needed
    if next_section and not next_section.content:
        from routes.learning.interaction_routes import generate_section_content
        try:
            # This is a simplified approach; ideally, this would be a background task
            generate_section_content(next_section.learning_section_id)
        except Exception as e:
            current_app.logger.error(f"Error generating next section content: {e}")
            # Continue even if content generation fails
    
    db.session.commit()
    
    # Prepare response data
    response_data = {
        "success": True,
        "all_completed": all_completed,
        "message": "Section completed successfully!"
    }
    
    # Add next section ID if available
    if next_section:
        response_data["next_section_id"] = next_section.learning_section_id
    
    return jsonify(response_data)

# Helper function to generate content for a section
def generate_section_content(section_id):
    """Generate content for a section"""
    section = LearningSection.query.get(section_id)
    if not section:
        return False
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    I'm learning about: {section.session.topic}
    
    Create concise, focused learning content for this specific section:
    "{section.title}"
    
    Requirements:
    1. Keep content brief but substantive (approximately 250-350 words)
    2. Focus on core concepts and essential knowledge
    3. Use simple language and explain technical terms
    4. Include 1-2 clear examples or applications
    5. Use bullet points or short paragraphs for readability
    6. Format with HTML for structure (use h3, p, ul, li tags)
    
    The goal is to help me understand this topic without overwhelming me with too much information.
    """
    
    response = client.models.generate_content(
        model=Config.GEMINI_MODEL,
        contents=prompt,
        config=Config.LEARNING_GEMINI_CONFIG
    )
    
    # Make sure content is a string
    content_text = response.text
    if not isinstance(content_text, str):
        content_text = str(content_text)
        
    # Save the generated content
    section.content = content_text
    db.session.commit()
    
    return True
