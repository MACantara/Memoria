from flask import request, render_template, redirect, url_for, jsonify, session as flask_session, current_app, abort
from flask_login import current_user, login_required
from routes.learning import learning_bp
from models import db, LearningSession, LearningSection, LearningQuestion
from google import genai
import os
from config import Config
import traceback
from datetime import datetime

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@learning_bp.route('/section/<int:section_id>')
@login_required
def view_section(section_id):
    """View content for a specific section with step-by-step progression"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership through the session
    if section.session.user_id != current_user.id:
        abort(403)
    
    # If content hasn't been generated yet, redirect to generate content
    if not section.content:
        return redirect(url_for('learning.generate_section_content', section_id=section_id))
    
    # Update session's current section
    session = section.session
    session.current_section = section.order
    
    # Get all questions for this section
    questions = LearningQuestion.query.filter_by(learning_section_id=section_id).all()
    
    # Get active question
    active_question = section.get_active_question()
    
    # Update session step
    if section.is_completed:
        session.current_step = 'complete'
    elif active_question or questions:
        session.current_step = 'question'
    else:
        session.current_step = 'content'
        
    db.session.commit()
    
    # Get all sections for scrollable content
    all_sections = LearningSection.query.filter_by(
        learning_session_id=section.session.learning_session_id
    ).order_by(LearningSection.order).all()
    
    # Find next section that doesn't have content yet (for preview)
    next_section = None
    for s in all_sections:
        if s.order > section.order and not s.content:
            next_section = s
            break
    
    # Check if we're currently generating the next section
    is_generating_next = False
    if 'generating_section_id' in flask_session:
        is_generating_next = flask_session['generating_section_id'] == (next_section.learning_section_id if next_section else None)
    
    return render_template(
        'learning/section.html',
        section=section,
        session=session,
        questions=questions,
        active_question=active_question,
        step=session.current_step,
        all_sections=all_sections,
        next_section=next_section,
        is_generating_next=is_generating_next
    )

@learning_bp.route('/section/<int:section_id>/generate')
@login_required
def generate_section_content(section_id):
    """Generate content for a specific section"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership through the session
    if section.session.user_id != current_user.id:
        abort(403)
    
    return render_template(
        'learning/generate_content.html',
        section=section,
        session=section.session
    )

@learning_bp.route('/section/<int:section_id>/process-content', methods=['POST'])
@login_required
def process_section_content(section_id):
    """Process and save the generated content for a section"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership
    if section.session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Get the outline for context
        outline = section.session.get_outline_as_list()
        
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
            contents=prompt
        )
        
        # Make sure content is a string, not a dict or other object
        content_text = response.text
        if not isinstance(content_text, str):
            content_text = str(content_text)
            
        # Save the generated content
        section.content = content_text
        section.session.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "redirect": url_for('learning.view_section', section_id=section_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating content: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Failed to generate content. Please try again."}), 500
