# controllers/auth_controller.py
# Enhanced auth controller with agent registration

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import AuthService
from services.user_service import UserService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        auth_service = AuthService()
        user, error = auth_service.authenticate_user(username, password)
        
        if user:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash(error, 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register-agent/<token>', methods=['GET', 'POST'])
def register_agent(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Validate email match
        if request.form.get('email') != request.form.get('confirm_email'):
            flash('Email addresses do not match.', 'danger')
            return render_template('auth/register_agent.html', token=token)
        
        # Validate password confirmation
        if request.form.get('password') != request.form.get('confirm_password'):
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_agent.html', token=token)
        
        agent_data = {
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'full_name': request.form.get('full_name'),
            'phone': request.form.get('phone'),
            'salutation': request.form.get('salutation'),
            'gender': request.form.get('gender'),
            'city': request.form.get('city'),
            'organization': request.form.get('organization'),
            'professional_role': request.form.get('professional_role'),
            'is_lic_advisor': request.form.get('is_lic_advisor'),
            'sells_mutual_funds': request.form.get('sells_mutual_funds'),
            'sells_health_insurance': request.form.get('sells_health_insurance'),
            'sells_term_insurance': request.form.get('sells_term_insurance')
        }
        
        user_service = UserService()
        agent_id, error = user_service.register_agent_via_link(agent_data, token)
        
        if agent_id:
            flash('Registration successful! Your account is pending approval.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'danger')
    
    return render_template('auth/register_agent.html', token=token)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
        else:
            auth_service = AuthService()
            success, message = auth_service.change_password(
                current_user.id,
                old_password,
                new_password
            )
            
            if success:
                flash(message, 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash(message, 'danger')
    
    return render_template('auth/change_password.html')