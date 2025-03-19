from flask import redirect, url_for, render_template, abort
from flask_login import current_user, login_required
from routes.learning import learning_bp
from models import db, LearningSection

@learning_bp.route('/section/<int:section_id>')
@login_required
def view_section(section_id):
    """
    Legacy route that now redirects to the unified session view,
    with a section ID parameter to focus on that section.
    """
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership through the session
    if section.session.user_id != current_user.id:
        abort(403)
    
    # Redirect to the unified session view instead
    return redirect(url_for('learning.view_session', 
                           session_id=section.session.learning_session_id, 
                           active_section=section_id))

@learning_bp.route('/section/<int:section_id>/generate')
@login_required
def generate_section_content(section_id):
    """
    Legacy route for generating content for a specific section.
    Now serves as a fallback for old links and shows a transition page.
    """
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership through the session
    if section.session.user_id != current_user.id:
        abort(403)
    
    # Show the generation page, but it will use the unified flow's JS
    return render_template(
        'learning/generate_content.html',
        section=section,
        session=section.session
    )

@learning_bp.route('/section/<int:section_id>/process-content', methods=['POST'])
@login_required
def process_section_content(section_id):
    """
    Legacy endpoint that now redirects to the new API endpoint.
    """
    from routes.learning.api_routes import api_generate_section_content
    return api_generate_section_content(section_id)
