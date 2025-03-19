from datetime import datetime
import json
from models import db
import sqlalchemy as sa
from flask_login import current_user

class LearningSession(db.Model):
    __tablename__ = 'learning_sessions'
    
    learning_session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='active')  # active, completed, archived
    outline = db.Column(db.Text, nullable=True)  # JSON string of section titles
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    current_section = db.Column(db.Integer, default=0)  # Current section index
    current_step = db.Column(db.String(50), default='content')  # content, question, complete
    
    # Relationships
    user = db.relationship('User', backref=db.backref('learning_sessions', lazy=True))
    sections = db.relationship('LearningSection', backref='session', lazy=True, 
                              cascade="all, delete-orphan", order_by="LearningSection.order")
    
    def get_outline_as_list(self):
        """Return the outline as a list of strings"""
        if not self.outline:
            return []
        try:
            return json.loads(self.outline)
        except:
            return []
    
    def get_completion_percentage(self):
        """Calculate the completion percentage of this session"""
        if not self.sections:
            return 0
            
        completed_sections = sum(1 for section in self.sections if section.is_completed)
        return round((completed_sections / len(self.sections)) * 100)

class LearningSection(db.Model):
    __tablename__ = 'learning_sections'
    
    learning_section_id = db.Column(db.Integer, primary_key=True)
    learning_session_id = db.Column(db.Integer, db.ForeignKey('learning_sessions.learning_session_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Generated content for this section
    order = db.Column(db.Integer, nullable=False)  # Order in the outline
    is_completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    questions = db.relationship('LearningQuestion', backref='section', lazy=True, cascade="all, delete-orphan")
    
    def get_active_question(self):
        """Get the first unanswered question for this section"""
        for question in self.questions:
            if not question.is_answered:
                return question
        return None
    
    def all_questions_answered_correctly(self):
        """Check if all questions for this section are answered correctly"""
        if not self.questions:
            return True
        return all(q.is_correct for q in self.questions)

class LearningQuestion(db.Model):
    __tablename__ = 'learning_questions'
    
    learning_question_id = db.Column(db.Integer, primary_key=True)
    learning_session_id = db.Column(db.Integer, db.ForeignKey('learning_sessions.learning_session_id'), nullable=False)
    learning_section_id = db.Column(db.Integer, db.ForeignKey('learning_sections.learning_section_id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    incorrect_answers = db.Column(db.Text, nullable=False)  # JSON array of incorrect answers
    user_answer = db.Column(db.Text, nullable=True)  # The answer the user selected
    is_correct = db.Column(db.Boolean, nullable=True)  # Whether the user's answer was correct
    explanation = db.Column(db.Text, nullable=True)  # Explanation of the correct answer
    attempts = db.Column(db.Integer, default=0)  # Number of attempts
    
    # Relationships
    session = db.relationship('LearningSession', backref=db.backref('questions', lazy=True))
    
    @property
    def is_answered(self):
        """Check if the question has been answered"""
        return self.user_answer is not None
    
    def get_incorrect_answers(self):
        """Get the incorrect answers as a list"""
        if not self.incorrect_answers:
            return []
        try:
            return json.loads(self.incorrect_answers)
        except:
            return []
    
    def check_answer(self, answer):
        """Check if the provided answer is correct"""
        self.user_answer = answer
        self.attempts += 1
        self.is_correct = (answer == self.correct_answer)
        db.session.add(self)
        db.session.commit()
        return self.is_correct
    
    def to_dict(self):
        """Convert the question to a dictionary for API responses"""
        return {
            'id': self.learning_question_id,
            'question': self.question,
            'correct_answer': self.correct_answer,
            'incorrect_answers': self.get_incorrect_answers(),
            'user_answer': self.user_answer,
            'is_correct': self.is_correct,
            'explanation': self.explanation,
            'attempts': self.attempts
        }
