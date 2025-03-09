from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from models import db, User
from datetime import datetime
from flask_login import login_user, logout_user, current_user

ph = PasswordHasher()

def hash_password(password):
    """Hash a password using Argon2"""
    return ph.hash(password)

def verify_password(user, password):
    """Verify a password against the stored hash"""
    try:
        ph.verify(user.password_hash, password)
        return True
    except VerifyMismatchError:
        return False

def register_user(username, email, password):
    """Register a new user"""
    # Check if user already exists
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return False, "Username or email already exists"
    
    # Hash password and create user
    password_hash = hash_password(password)
    
    new_user = User(
        username=username,
        email=email,
        password_hash=password_hash
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return True, "Registration successful"

def authenticate_user(login_id, password):
    """Authenticate a user by username or email"""
    # Find user by username or email
    user = User.query.filter(
        (User.username == login_id) | (User.email == login_id)
    ).first()
    
    if not user:
        return None, "Invalid username or email"
    
    if not verify_password(user, password):
        return None, "Invalid password"
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    return user, "Login successful"

def update_profile(user_id, username=None, email=None, current_password=None, new_password=None):
    """Update user profile"""
    user = User.query.get(user_id)
    if not user:
        return False, "User not found"
    
    # Verify current password if changing password or sensitive fields
    if current_password:
        if not verify_password(user, current_password):
            return False, "Current password is incorrect"
        
        if new_password:
            user.password_hash = hash_password(new_password)
    
    # Update username if provided and not already taken
    if username and username != user.username:
        if User.query.filter_by(username=username).first():
            return False, "Username already taken"
        user.username = username
    
    # Update email if provided and not already taken
    if email and email != user.email:
        if User.query.filter_by(email=email).first():
            return False, "Email already taken"
        user.email = email
    
    db.session.commit()
    return True, "Profile updated successfully"
