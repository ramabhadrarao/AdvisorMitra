from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from services.user_service import UserService
from services.plan_service import PlanService
from utils.decorators import admin_required, api_admin_required
from utils.helpers import save_profile_image, delete_profile_image
import os

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@login_required
@admin_required
def list():
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role')
    
    filters = {}
    if role_filter:
        filters['role'] = role_filter
    
    # Admins can only see agents and other admins, not owners
    if current_user.role == 'ADMIN':
        filters['role'] = {'$in': ['AGENT', 'ADMIN']}
    
    user_service = UserService()
    plan_service = PlanService()
    
    result = user_service.get_all_users(filters, page, 10)
    return render_template('users/list.html', **result)

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    user_service = UserService()
    plan_service = PlanService()
    
    if request.method == 'POST':
        user_data = {
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'full_name': request.form.get('full_name'),
            'phone': request.form.get('phone'),
            'role': request.form.get('role'),
            'is_active': True
        }
        
        # Validate role assignment
        if current_user.role == 'ADMIN' and user_data['role'] == 'OWNER':
            flash('You cannot create an owner account.', 'danger')
            return redirect(url_for('users.create'))
        
        # Handle plan assignment for agents
        if user_data['role'] == 'AGENT':
            plan_id = request.form.get('plan_id')
            if plan_id:
                user_data['plan_id'] = plan_id
        
        user_id, error = user_service.create_user(user_data, current_user.id)
        
        if user_id:
            flash('User created successfully.', 'success')
            return redirect(url_for('users.list'))
        else:
            flash(error, 'danger')
    
    # Get available plans for agent creation
    plans = plan_service.get_active_plans() if current_user.is_owner() else []
    
    return render_template('users/create.html', plans=plans)

@users_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_service = UserService()
    
    if request.method == 'POST':
        update_data = {
            'full_name': request.form.get('full_name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone')
        }
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                # Delete old image if exists
                if current_user.profile_image and current_user.profile_image != 'default.png':
                    delete_profile_image(current_user.profile_image)
                
                # Save new image
                filename = save_profile_image(file)
                if filename:
                    update_data['profile_image'] = filename
        
        success, message = user_service.update_user(current_user.id, update_data, current_user.id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('users.profile'))
    
    return render_template('users/profile.html')

@users_bp.route('/<user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_status(user_id):
    user_service = UserService()
    success, message = user_service.toggle_user_status(user_id, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('users.list'))

@users_bp.route('/<user_id>/assign-plan', methods=['POST'])
@login_required
@admin_required
def assign_plan(user_id):
    plan_id = request.form.get('plan_id')
    
    if not plan_id:
        flash('Please select a plan.', 'danger')
        return redirect(url_for('users.list'))
    
    user_service = UserService()
    success, message = user_service.assign_plan_to_agent(user_id, plan_id, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('users.list'))

# API endpoints
@users_bp.route('/api/list')
@login_required
@api_admin_required
def api_list():
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role')
    
    filters = {}
    if role_filter:
        filters['role'] = role_filter
    
    if current_user.role == 'ADMIN':
        filters['role'] = {'$in': ['AGENT', 'ADMIN']}
    
    user_service = UserService()
    result = user_service.get_all_users(filters, page, 10)
    
    users_data = []
    for user in result['users']:
        user_dict = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'phone': user.phone,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }
        
        if user.role == 'AGENT' and hasattr(user, 'plan'):
            user_dict['plan'] = {
                'name': user.plan.name,
                'expiry_date': user.plan_expiry_date.isoformat() if user.plan_expiry_date else None,
                'pdf_limit': user.pdf_limit,
                'pdf_generated': user.pdf_generated
            }
        
        users_data.append(user_dict)
    
    return jsonify({
        'success': True,
        'users': users_data,
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages']
    })

@users_bp.route('/api/create', methods=['POST'])
@login_required
@api_admin_required
def api_create():
    data = request.get_json()
    
    user_data = {
        'username': data.get('username'),
        'email': data.get('email'),
        'password': data.get('password'),
        'full_name': data.get('full_name'),
        'phone': data.get('phone'),
        'role': data.get('role'),
        'is_active': data.get('is_active', True)
    }
    
    # Validate required fields
    required_fields = ['username', 'email', 'password', 'role']
    for field in required_fields:
        if not user_data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    # Validate role assignment
    if current_user.role == 'ADMIN' and user_data['role'] == 'OWNER':
        return jsonify({'success': False, 'error': 'You cannot create an owner account'}), 403
    
    # Handle plan assignment for agents
    if user_data['role'] == 'AGENT':
        plan_id = data.get('plan_id')
        if plan_id:
            user_data['plan_id'] = plan_id
    
    user_service = UserService()
    user_id, error = user_service.create_user(user_data, current_user.id)
    
    if user_id:
        return jsonify({'success': True, 'user_id': user_id, 'message': 'User created successfully'})
    else:
        return jsonify({'success': False, 'error': error}), 400

@users_bp.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def api_profile():
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'full_name': current_user.full_name,
                'phone': current_user.phone,
                'role': current_user.role,
                'profile_image': current_user.profile_image
            }
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        update_data = {
            'full_name': data.get('full_name'),
            'email': data.get('email'),
            'phone': data.get('phone')
        }
        
        user_service = UserService()
        success, message = user_service.update_user(current_user.id, update_data, current_user.id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400