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
    """Mark a section as read and generate questions"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership
    if section.session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Generate questions for this section
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
        return jsonify({"error": "Failed to process. Please try again."}), 500

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
        
        # Create a prompt for generating focused quiz questions
        prompt = f"""
        Based on this educational content about "{section.session.topic}" on "{section.title}":
        
        {section.content}
        
        Generate {num_questions} focused multiple-choice questions that test understanding of the key concepts.
        
        Requirements:
        1. Each question should test ONE important concept from the content
        2. Questions should be clear and direct (avoid complex scenarios)
        3. The correct answer must be unambiguously supported by the content
        4. Provide 3 plausible but clearly incorrect alternatives
        5. Format your response as a JSON array of question objects:
        [{{
            "question": "What is X?",
            "correct_answer": "The correct answer",
            "incorrect_answers": ["Wrong 1", "Wrong 2", "Wrong 3"]
        }}]
        
        Only return the JSON array, nothing else.
        """
        
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

@learning_bp.route('/section/<int:section_id>/complete', methods=['POST'])
@login_required
def mark_section_complete(section_id):
    """Mark a section as completed and generate content for the next section if needed"""
    section = LearningSection.query.get_or_404(section_id)
    
    # Check ownership
    if section.session.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
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
    
    # Get next section to prepare content
    next_section = None
    for s in all_sections:
        if s.order == section.order + 1:
            next_section = s
            break
    
    # If there is a next section and it has no content, automatically generate content
    generate_next = False
    if next_section and not next_section.content:
        generate_next = True
        # Set a flag that we're generating content for this section
        if next_section:
            flask_session['generating_section_id'] = next_section.learning_section_id
            
        # Generate content for the next section in the background
        try:
            # This would be better as a background task, but we're simplifying
            # for now to avoid additional complexity
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            I'm learning about: {next_section.session.topic}
            
            Create concise, focused learning content for this specific section:
            "{next_section.title}"
            
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
            next_section.content = content_text
            
            # Clear the generation flag once complete
            if 'generating_section_id' in flask_session:
                flask_session.pop('generating_section_id', None)
        except Exception as e:
            current_app.logger.error(f"Error generating next section content: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            # Clear the flag if generation fails
            if 'generating_section_id' in flask_session:
                flask_session.pop('generating_section_id', None)
            # Even if generation fails, we still allow navigation to the next section
    
    db.session.commit()
    
    # If all completed, go to session view to see overall progress
    if all_completed:
        return jsonify({
            "success": True,
            "all_completed": True,
            "message": "Congratulations! You've completed this learning session.",
            "redirect": url_for('learning.view_session', session_id=section.learning_session_id)
        })
    
    # Otherwise, always navigate to the next section (even if generation failed)
    if next_section:
        return jsonify({
            "success": True,
            "all_completed": False,
            "message": "Section completed successfully!",
            "redirect": url_for('learning.view_section', section_id=next_section.learning_section_id)
        })
    else:
        # Fallback to session view if there's no next section (should rarely happen)
        return jsonify({
            "success": True,
            "all_completed": True,
            "message": "Section completed successfully!",
            "redirect": url_for('learning.view_session', session_id=section.learning_session_id)
        })

@learning_bp.route('/question/answer', methods=['POST'])
@login_required
def answer_question():
    """Record a user's answer to a learning question"""
    try:
        data = request.json
        question_id = data.get('question_id')
        answer = data.get('answer')
        is_correct = data.get('is_correct', False)
        
        # Get the question
        question = LearningQuestion.query.get_or_404(question_id)
        
        # Verify ownership
        if question.session.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
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
        return jsonify({"error": "Failed to record answer"}), 500
