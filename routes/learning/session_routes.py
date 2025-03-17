from flask import request, render_template, redirect, url_for, jsonify, current_app, abort, flash
from flask_login import current_user, login_required
from routes.learning import learning_bp
from models import db, LearningSession, LearningSection
from google import genai
import json
import os
from config import Config
import traceback
from datetime import datetime

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@learning_bp.route('/')
@login_required
def index():
    """Display the landing page for the learning feature"""
    # Get user's active and recent sessions
    active_sessions = LearningSession.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).order_by(LearningSession.last_updated.desc()).limit(5).all()
    
    completed_sessions = LearningSession.query.filter_by(
        user_id=current_user.id,
        status='completed'
    ).order_by(LearningSession.last_updated.desc()).limit(5).all()
    
    return render_template(
        'learning/index.html',
        active_sessions=active_sessions,
        completed_sessions=completed_sessions
    )

@learning_bp.route('/start', methods=['POST'])
@login_required
def start_session():
    """Start a new learning session"""
    topic = request.form.get('topic')
    if not topic:
        # If no topic provided, redirect back to index with error
        flash("Please enter a topic to learn about", "warning")
        return redirect(url_for('learning.index'))
    
    # Create a new learning session
    learning_session = LearningSession(
        user_id=current_user.id,
        topic=topic,
        status='active'
    )
    
    db.session.add(learning_session)
    db.session.commit()
    
    # Redirect to generate the outline
    return redirect(url_for('learning.generate_outline', session_id=learning_session.learning_session_id))

@learning_bp.route('/session/<int:session_id>/generate-outline')
@login_required
def generate_outline(session_id):
    """Generate an outline for the given learning session"""
    # Get the learning session
    learning_session = LearningSession.query.get_or_404(session_id)
    
    # Check ownership
    if learning_session.user_id != current_user.id:
        abort(403)
    
    # If outline already exists, redirect to session view
    if learning_session.outline:
        return redirect(url_for('learning.view_session', session_id=session_id))
    
    return redirect(url_for('learning.view_session', 
                           session_id=session_id, 
                           generate_outline='true'))

@learning_bp.route('/session/<int:session_id>/process-outline', methods=['POST'])
@login_required
def process_outline(session_id):
    """Process the outline generation request"""
    learning_session = LearningSession.query.get_or_404(session_id)
    
    # Check ownership
    if learning_session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Create a prompt for generating an outline - specify conciseness
        prompt = f"""
        Create a structured learning outline for: {learning_session.topic}
        
        Please provide a concise outline with 4-6 focused sections that would help someone learn this topic efficiently.
        Each section should be specific and focused on one aspect.
        
        Format your response as a JSON array of section titles as simple strings and not numbered, like this example:
        ["Introduction to {learning_session.topic}", "Key Concepts", ...]
        
        Important requirements:
        - Make sections focused on one aspect each
        - Use clear, straightforward language
        - Keep titles concise (under 8 words)
        - Arrange sections in a logical learning progression
        - Do NOT return complex data structures, only string titles
        
        Only return the JSON array of section title strings, nothing else.
        """
        
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config=Config.LEARNING_GEMINI_CONFIG
        )
        
        # Parse the JSON response with improved error handling
        try:
            # Extract JSON from response text (handling potential formatting)
            response_text = response.text.strip()
            current_app.logger.debug(f"Raw response: {response_text}")
            
            # Find the JSON part (usually between [ and ])
            if '[' in response_text and ']' in response_text:
                start = response_text.find('[')
                end = response_text.rfind(']') + 1
                json_text = response_text[start:end]
                outline_sections = json.loads(json_text)
            else:
                # If JSON formatting fails, try to extract sections manually
                lines = response_text.split('\n')
                outline_sections = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('['):
                        outline_sections.append(line)
            
            # Validate and convert each section to ensure it's a string
            validated_sections = []
            for item in outline_sections:
                if isinstance(item, dict):
                    # Handle case where the API returned question objects
                    if 'q' in item:
                        # Use the question as the section title
                        validated_sections.append(f"Section: {item['q']}")
                    else:
                        # Use the first key-value pair as a fallback
                        first_key = next(iter(item))
                        validated_sections.append(f"Section: {item[first_key]}")
                elif item:
                    # Keep valid string items
                    validated_sections.append(str(item))
            
            # If we couldn't get any valid sections, create some generic ones
            if not validated_sections:
                validated_sections = [
                    f"Section 1: Introduction to {learning_session.topic}",
                    f"Section 2: Key Concepts of {learning_session.topic}",
                    f"Section 3: Applications of {learning_session.topic}",
                    f"Section 4: Advanced Topics in {learning_session.topic}",
                    f"Section 5: Future Perspectives on {learning_session.topic}"
                ]
                
            # Save the outline
            learning_session.outline = json.dumps(validated_sections)
            
            # Create learning sections based on the outline
            for i, section_title in enumerate(validated_sections):
                section = LearningSection(
                    learning_session_id=session_id,
                    title=section_title,
                    order=i
                )
                db.session.add(section)
            
            db.session.commit()
            
            return jsonify({
                "success": True, 
                "redirect": url_for('learning.view_session', session_id=session_id)
            })
            
        except Exception as e:
            current_app.logger.error(f"Error parsing outline: {e}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({"error": "Failed to generate a proper outline. Please try again."}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error generating outline: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Failed to generate outline. Please try again."}), 500

@learning_bp.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View a learning session with its outline and progress"""
    learning_session = LearningSession.query.get_or_404(session_id)
    
    # Check ownership
    if learning_session.user_id != current_user.id:
        abort(403)
    
    # Get sections and completion status
    sections = LearningSection.query.filter_by(learning_session_id=session_id).order_by(LearningSection.order).all()
    
    # Calculate progress
    completion_percentage = learning_session.get_completion_percentage()
    
    return render_template(
        'learning/session.html',
        session=learning_session,
        sections=sections,
        completion_percentage=completion_percentage
    )
