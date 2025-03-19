from flask import request, jsonify, session as flask_session, current_app, url_for
from flask_login import current_user, login_required
from routes.learning import learning_bp
from models import db, LearningSection, LearningQuestion
from google import genai
import json
import os
from config import Config
import traceback
from datetime import datetime

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@learning_bp.route('/section/<int:section_id>/mark-read', methods=['POST'])
@login_required
def mark_section_read(section_id):
    """Legacy endpoint that now redirects to the new API endpoint"""
    from routes.learning.api_routes import api_mark_section_read
    return api_mark_section_read(section_id)

@learning_bp.route('/section/<int:section_id>/complete', methods=['POST'])
@login_required
def mark_section_complete(section_id):
    """Legacy endpoint that now redirects to the new API endpoint"""
    from routes.learning.api_routes import api_mark_section_complete
    return api_mark_section_complete(section_id)

@learning_bp.route('/question/answer', methods=['POST'])
@login_required
def answer_question():
    """Legacy endpoint that now redirects to the new API endpoint"""
    from routes.learning.api_routes import api_answer_question
    return api_answer_question()

# Keep these helper functions since they are imported by api_routes.py
def generate_section_questions(section_id, num_questions=2):
    """Generate quiz questions for a section"""
    section = LearningSection.query.get(section_id)
    if not section or not section.content:
        return False
    
    # Check if questions already exist for this section
    existing_questions = LearningQuestion.query.filter_by(learning_section_id=section_id).count()
    if existing_questions > 0:
        return True  # Questions already exist
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Use the prompt from Config
        prompt = Config.LEARNING_QUESTIONS_PROMPT.format(
            topic=section.session.topic,
            section_title=section.title,
            section_content=section.content,
            num_questions=num_questions
        )
        
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config=Config.QUESTION_GEMINI_CONFIG
        )
        
        # Parse the JSON response with improved error handling
        try:
            # Extract JSON from response text
            response_text = response.text.strip()
            current_app.logger.debug(f"Raw questions response: {response_text}")
            
            # Find the JSON part (usually between [ and ])
            if '[' in response_text and ']' in response_text:
                start = response_text.find('[')
                end = response_text.rfind(']') + 1
                json_text = response_text[start:end]
                questions_data = json.loads(json_text)
            else:
                # Couldn't find JSON, log error
                current_app.logger.error(f"Could not extract JSON from: {response_text}")
                return False
            
            # Save each question
            for q_data in questions_data:
                question = LearningQuestion(
                    learning_session_id=section.session.learning_session_id,
                    learning_section_id=section_id,
                    question=q_data['question'],
                    correct_answer=q_data['correct_answer'],
                    incorrect_answers=json.dumps(q_data['incorrect_answers'])
                )
                db.session.add(question)
            
            db.session.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error parsing questions: {e}")
            current_app.logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error generating questions: {e}")
        current_app.logger.error(traceback.format_exc())
        return False

def clean_ai_generated_content(content):
    """
    Remove Markdown code block delimiters from AI-generated content
    """
    if not content:
        return content
        
    # Remove ```html and ``` markers
    content = content.replace('```html', '')
    content = content.replace('```', '')
    
    # Remove leading/trailing whitespace that might have been left
    content = content.strip()
    
    return content

def generate_section_content(section_id):
    """Helper function to generate content for a section"""
    section = LearningSection.query.get(section_id)
    if not section:
        return False
    
    client = genai.Client(api_key=api_key)
    
    # Use the prompt from Config
    prompt = Config.LEARNING_CONTENT_PROMPT.format(
        topic=section.session.topic,
        section_title=section.title
    )
    
    response = client.models.generate_content(
        model=Config.GEMINI_MODEL,
        contents=prompt,
        config=Config.LEARNING_GEMINI_CONFIG
    )
    
    # Make sure content is a string
    content_text = response.text
    if not isinstance(content_text, str):
        content_text = str(content_text)
    
    # Clean the content to remove any Markdown code block delimiters
    content_text = clean_ai_generated_content(content_text)
        
    # Save the generated content
    section.content = content_text
    db.session.commit()
    
    return True
