from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from services.auth_service import authenticate_user, register_user, update_profile

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    data = request.form
    login_id = data.get('login_id')  # Can be username or email
    password = data.get('password')
    
    if not login_id or not password:
        flash('Please provide both login ID and password', 'error')
        return render_template('auth/login.html')
    
    user, message = authenticate_user(login_id, password)
    
    if not user:
        flash(message, 'error')
        return render_template('auth/login.html')
    
    login_user(user)
    flash('Login successful', 'success')
    
    # Redirect to the next page or dashboard
    next_page = request.args.get('next')
    return redirect(next_page or url_for('main.index'))

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'GET':
        return render_template('auth/signup.html')
    
    data = request.form
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    # Basic validation
    if not username or not email or not password:
        flash('Please fill in all fields', 'error')
        return render_template('auth/signup.html')
    
    if password != confirm_password:
        flash('Passwords do not match', 'error')
        return render_template('auth/signup.html')
    
    success, message = register_user(username, email, password)
    
    if not success:
        flash(message, 'error')
        return render_template('auth/signup.html')
    
    flash('Registration successful! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Handle user profile view and updates"""
    if request.method == 'GET':
        return render_template('auth/profile.html')
    
    data = request.form
    username = data.get('username')
    email = data.get('email')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    # Validate password match if provided
    if new_password and new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return render_template('auth/profile.html')
    
    # Don't proceed with empty current password if trying to change sensitive info
    if (new_password or username != current_user.username or email != current_user.email) and not current_password:
        flash('Current password is required to update profile', 'error')
        return render_template('auth/profile.html')
    
    success, message = update_profile(
        current_user.id,
        username=username,
        email=email,
        current_password=current_password,
        new_password=new_password
    )
    
    if not success:
        flash(message, 'error')
    else:
        flash(message, 'success')
    
    return render_template('auth/profile.html')
