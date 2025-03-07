from datetime import datetime
from flask_login import UserMixin
from passlib.hash import argon2
from . import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    decks = db.relationship('FlashcardDecks', backref='owner', lazy=True)
    
    def set_password(self, password):
        """Hash password with Argon2"""
        self.password_hash = argon2.hash(password)
        
    def check_password(self, password):
        """Verify password against stored hash"""
        return argon2.verify(password, self.password_hash)
