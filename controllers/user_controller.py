# controllers/user_controller.py
# Enhanced user controller with approval workflow

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from services.user_service import UserService
from services.plan_service import PlanService
from services.coupon_service import CouponService
from utils.decorators import admin_required, api_admin_required, super_admin_required, partner_required
from utils.helpers import save_profile_image, delete_profile_image, log_activity
import os
from datetime import datetime

from models import get_users_collection
from models.user import User
from bson import ObjectId

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@login_required
@admin_required
def list():
    # For partners, redirect to agents view
    if current_user.is_partner():
        return redirect(url_for('users.agents'))
    
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role')
    status_filter = request.args.get('status')
    
    filters = {}
    if role_filter:
        filters['role'] = role_filter
    if status_filter:
        filters['approval_status'] = status_filter
    
    user_service = UserService()
    
    # Super admin sees all users with partner info
    if current_user.is_super_admin():
        result = user_service.get_all_users_with_partners(filters, page, 10)
    # Partner sees only their agents
    elif current_user.is_partner():
        filters['role'] = 'AGENT'
        filters['partner_id'] = ObjectId(current_user.id)
        result = user_service.get_partner_agents(current_user.id, filters, page, 10)
    else:
        result = {'users': [], 'total': 0, 'page': 1, 'per_page': 10, 'total_pages': 0}
    
    return render_template('users/list.html', **result)

@users_bp.route('/create-partner', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_partner():
    if request.method == 'POST':
        partner_data = {
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'full_name': request.form.get('full_name'),
            'phone': request.form.get('phone'),
            'is_active': True,
            'requires_double_approval': request.form.get('requires_double_approval') == 'on',
            'pdf_limit': int(request.form.get('pdf_limit', 0)),
            'assigned_plans': request.form.getlist('assigned_plans'),
            'assigned_coupons': request.form.getlist('assigned_coupons')
        }
        
        user_service = UserService()
        partner_id, error = user_service.create_partner(partner_data, current_user.id)
        
        if partner_id:
            flash('Partner created successfully.', 'success')
            return redirect(url_for('users.list'))
        else:
            flash(error, 'danger')
    
    # Get available plans and coupons
    plan_service = PlanService()
    coupon_service = CouponService()
    plans = plan_service.get_active_plans()
    coupons_result = coupon_service.get_all_coupons(page=1, per_page=100)
    
    return render_template('users/create_partner.html', 
                         plans=plans, 
                         coupons=coupons_result['coupons'])

@users_bp.route('/pending-approvals')
@login_required
@admin_required
def pending_approvals():
    page = request.args.get('page', 1, type=int)
    user_service = UserService()
    
    filters = {'approval_status': {'$in': ['PENDING', 'PARTNER_APPROVED']}}
    
    if current_user.is_super_admin():
        result = user_service.get_all_users_with_partners(filters, page, 10)
    elif current_user.is_partner():
        filters['partner_id'] = current_user._id
        result = user_service.get_partner_agents(current_user.id, filters, page, 10)
    else:
        result = {'users': [], 'total': 0, 'page': 1, 'per_page': 10, 'total_pages': 0}
    
    return render_template('users/pending_approvals.html', **result)

@users_bp.route('/<user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user_service = UserService()
    success, message = user_service.approve_user(user_id, current_user.id, current_user.role)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('users.pending_approvals'))

@users_bp.route('/<user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    reason = request.form.get('reason', 'No reason provided')
    
    user_service = UserService()
    success, message = user_service.reject_user(user_id, current_user.id, current_user.role, reason)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('users.pending_approvals'))

@users_bp.route('/generate-registration-link', methods=['POST'])
@login_required
@admin_required
def generate_registration_link():
    user_service = UserService()
    
    # For super admin, get partner_id from form
    if current_user.is_super_admin():
        partner_id = request.form.get('partner_id')
        if not partner_id:
            return jsonify({'success': False, 'error': 'Partner ID required'}), 400
    else:
        # Partners generate links for themselves
        partner_id = current_user.id
    
    token = user_service.create_agent_registration_link(
        partner_id, 
        current_user.id, 
        current_user.role
    )
    
    # Generate full URL
    registration_url = url_for('auth.register_agent', token=token, _external=True)
    
    return jsonify({
        'success': True,
        'registration_url': registration_url,
        'token': token
    })

@users_bp.route('/<partner_id>/update-limits', methods=['POST'])
@login_required
@super_admin_required
def update_partner_limits(partner_id):
    pdf_limit = int(request.form.get('pdf_limit', 0))
    
    user_service = UserService()
    success, message = user_service.update_partner_limits(partner_id, pdf_limit, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('users.list'))

@users_bp.route('/<user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details"""
    user_service = UserService()
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('users.list'))
    
    # Check permissions
    if current_user.is_partner():
        if user.role != 'AGENT' or str(user.partner_id) != current_user.id:
            flash('You can only edit your own agents.', 'danger')
            return redirect(url_for('users.list'))
    
    if request.method == 'POST':
        update_data = {
            'full_name': request.form.get('full_name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'is_active': request.form.get('is_active') == 'on'
        }
        
        # Handle profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                # Delete old image if exists
                if user.profile_image:
                    delete_profile_image(user.profile_image)
                
                # Save new image
                filename = save_profile_image(file)
                if filename:
                    update_data['profile_image'] = filename
        
        # Partner-specific updates (only super admin can update)
        if user.role == 'PARTNER' and current_user.is_super_admin():
            update_data['pdf_limit'] = int(request.form.get('pdf_limit', 0))
            update_data['requires_double_approval'] = request.form.get('requires_double_approval') == 'on'
            update_data['assigned_plans'] = request.form.getlist('assigned_plans')
            update_data['assigned_coupons'] = request.form.getlist('assigned_coupons')
        
        success, message = user_service.update_user(user_id, update_data, current_user.id)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('users.list'))
        else:
            flash(message, 'danger')
    
    # Get additional data based on user role
    partner = None
    plan = None
    plans = []
    coupons = []
    
    if user.role == 'AGENT' and user.partner_id:
        partner = user_service.get_user_by_id(str(user.partner_id))
        if user.plan_id:
            plan_service = PlanService()
            plan = plan_service.get_plan_by_id(str(user.plan_id))
    
    if user.role == 'PARTNER' and current_user.is_super_admin():
        plan_service = PlanService()
        coupon_service = CouponService()
        plans = plan_service.get_active_plans()
        coupons_result = coupon_service.get_all_coupons(page=1, per_page=100)
        coupons = coupons_result['coupons']
    
    return render_template('users/edit.html',
                         user=user,
                         partner=partner,
                         plan=plan,
                         plans=plans,
                         coupons=coupons)

@users_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
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
                if current_user.profile_image:
                    delete_profile_image(current_user.profile_image)
                
                # Save new image
                filename = save_profile_image(file)
                if filename:
                    update_data['profile_image'] = filename
        
        user_service = UserService()
        success, message = user_service.update_user(current_user.id, update_data, current_user.id)
        
        if success:
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('users.profile'))
        else:
            flash(message, 'danger')
    
    return render_template('users/profile.html')

@users_bp.route('/partner-resources')
@login_required
@partner_required
def partner_resources():
    """View partner's assigned resources"""
    user_service = UserService()
    plan_service = PlanService()
    coupon_service = CouponService()
    
    # Get assigned plans
    assigned_plans = []
    if current_user.assigned_plans:
        for plan_id in current_user.assigned_plans:
            plan = plan_service.get_plan_by_id(str(plan_id))
            if plan:
                assigned_plans.append(plan)
    
    # Get assigned coupons with usage stats
    assigned_coupons = []
    if current_user.assigned_coupons:
        for coupon_id in current_user.assigned_coupons:
            coupon = coupon_service.get_coupon_by_id(str(coupon_id))
            if coupon:
                # Get partner-specific usage stats
                if hasattr(coupon, 'partner_limits') and coupon.partner_limits:
                    partner_limit = coupon.partner_limits.get(current_user.id)
                    if partner_limit:
                        coupon.usage_stats = partner_limit
                assigned_coupons.append(coupon)
    
    # Get PDF usage
    stats = user_service.get_partner_statistics(current_user.id)
    pdf_used = stats['pdf_generated'] if stats else 0
    
    return render_template('users/partner_resources.html',
                         assigned_plans=assigned_plans,
                         assigned_coupons=assigned_coupons,
                         pdf_used=pdf_used)

# controllers/user_controller.py - Replace the assign_plan route (around line 285)
# Add this to controllers/user_controller.py (at the end of the file)

@users_bp.route('/api/payment-details/<user_id>')
@login_required
@admin_required
def api_payment_details(user_id):
    """Get payment details for an agent"""
    user_service = UserService()
    user = user_service.get_user_by_id(user_id)
    
    if not user or user.role != 'AGENT':
        return jsonify({'error': 'User not found or not an agent'}), 404
    
    # Check permissions
    if current_user.is_partner():
        if str(user.partner_id) != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
    
    payment_data = {
        'payment_confirmed': user.payment_confirmed,
        'payment_amount': user.payment_amount,
        'payment_method': user.payment_method,
        'payment_reference': user.payment_reference,
        'payment_date': user.payment_date.isoformat() if user.payment_date else None,
        'payment_proof': user.payment_proof,
        'plan_price_paid': user.plan_price_paid,
        'plan_coupon_used': user.plan_coupon_used
    }
    
    return jsonify({
        'success': True,
        'payment': payment_data
    })

@users_bp.route('/payment-proof/<filename>')
@login_required
@admin_required
def view_payment_proof(filename):
    """Serve payment proof file"""
    from flask import send_from_directory
    import os
    
    # Security check - ensure filename is safe
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    
    payment_folder = current_app.config.get('PAYMENT_UPLOAD_FOLDER', 'static/uploads/payments')
    file_path = os.path.join(current_app.root_path, payment_folder, filename)
    
    if not os.path.exists(file_path):
        return "File not found", 404
    
    # Get the directory and filename
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    
    return send_from_directory(directory, filename)
@users_bp.route('/<user_id>/assign-plan', methods=['POST'])
@login_required
@admin_required
def assign_plan(user_id):
    """Assign plan to agent with payment confirmation"""
    user_service = UserService()
    user = user_service.get_user_by_id(user_id)
    
    if not user or user.role != 'AGENT':
        flash('Invalid user or user is not an agent.', 'danger')
        return redirect(url_for('users.list'))
    
    # Check permissions
    if current_user.is_partner():
        if str(user.partner_id) != current_user.id:
            flash('You can only assign plans to your own agents.', 'danger')
            return redirect(url_for('users.list'))
    
    plan_id = request.form.get('plan_id')
    coupon_code = request.form.get('coupon_code')
    
    if not plan_id:
        flash('Please select a plan.', 'danger')
        return redirect(url_for('users.list'))
    
    # Prepare payment data
    payment_data = None
    if request.form.get('payment_confirmed') == 'on':
        payment_data = {
            'payment_confirmed': True,
            'payment_date': datetime.utcnow(),
            'payment_amount': request.form.get('payment_amount'),
            'payment_method': request.form.get('payment_method'),
            'payment_reference': request.form.get('payment_reference')
        }
        
        # Handle payment proof upload
        if 'payment_proof' in request.files:
            file = request.files['payment_proof']
            if file and file.filename:
                from utils.helpers import save_payment_proof
                filename = save_payment_proof(file)
                if filename:
                    payment_data['payment_proof'] = filename
    
    # Assign plan
    success, message = user_service.assign_plan_to_agent(
        user_id,
        plan_id,
        current_user.id,
        coupon_code,
        payment_data
    )
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('users.list'))

@users_bp.route('/partners')
@login_required
@super_admin_required
def partners():
    """View all partners (super admin only)"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status')
    
    filters = {'role': 'PARTNER'}
    if status_filter == 'active':
        filters['is_active'] = True
        filters['approval_status'] = 'APPROVED'
    elif status_filter == 'inactive':
        filters['$or'] = [{'is_active': False}, {'approval_status': {'$ne': 'APPROVED'}}]
    
    user_service = UserService()
    result = user_service.get_all_users_with_partners(filters, page, 10)
    
    # Calculate additional stats
    users = get_users_collection()
    total_partners = result['total']
    active_count = users.count_documents({'role': 'PARTNER', 'is_active': True, 'approval_status': 'APPROVED'})
    
    # Calculate total PDF limits and usage
    all_partners = users.find({'role': 'PARTNER'})
    total_pdf_limit = sum(p.get('pdf_limit', 0) for p in all_partners)
    
    # Calculate total PDFs used by all agents
    all_agents = users.find({'role': 'AGENT'})
    total_pdf_used = sum(a.get('agent_pdf_generated', 0) for a in all_agents)
    
    return render_template('users/partners.html',
                         partners=result['users'],
                         total=total_partners,
                         active_count=active_count,
                         total_pdf_limit=total_pdf_limit,
                         total_pdf_used=total_pdf_used,
                         page=result['page'],
                         per_page=result['per_page'],
                         total_pages=result['total_pages'])

@users_bp.route('/agents')
@login_required
@admin_required
def agents():
    """View agents (super admin sees all, partner sees their own)"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status')
    partner_id_filter = request.args.get('partner_id')
    
    filters = {'role': 'AGENT'}
    if status_filter:
        filters['approval_status'] = status_filter
    
    user_service = UserService()
    
    # For partners, always filter by their ID
    if current_user.is_partner():
        partner_id_filter = current_user.id
    
    # Apply partner filter if specified
    if partner_id_filter:
        filters['partner_id'] = ObjectId(partner_id_filter)
    
    # Get agents
    if current_user.is_super_admin():
        result = user_service.get_all_users_with_partners(filters, page, 10)
    else:
        result = user_service.get_partner_agents(current_user.id, filters, page, 10)
    
    # Get partners list for filter dropdown (super admin only)
    partners_list = []
    selected_partner = None
    if current_user.is_super_admin():
        users = get_users_collection()
        partners_data = users.find({'role': 'PARTNER', 'is_active': True})
        partners_list = [User(p) for p in partners_data]
        
        # Get selected partner info
        if partner_id_filter:
            partner_data = users.find_one({'_id': ObjectId(partner_id_filter)})
            if partner_data:
                selected_partner = User(partner_data)
    
    return render_template('users/agents.html',
                         agents=result['users'],
                         total=result['total'],
                         page=result['page'],
                         per_page=result['per_page'],
                         total_pages=result['total_pages'],
                         partners_list=partners_list,
                         selected_partner=selected_partner)

@users_bp.route('/<user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_status(user_id):
    """Toggle user active status"""
    user_service = UserService()
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(request.referrer or url_for('users.list'))
    
    # Check permissions
    if current_user.is_partner():
        if user.role != 'AGENT' or str(user.partner_id) != current_user.id:
            flash('You can only manage your own agents.', 'danger')
            return redirect(request.referrer or url_for('users.list'))
    
    # Prevent self-deactivation
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(request.referrer or url_for('users.list'))
    
    # Toggle status
    new_status = not user.is_active
    users = get_users_collection()
    users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {
            'is_active': new_status,
            'updated_at': datetime.utcnow()
        }}
    )
    
    # Log activity
    status_text = "activated" if new_status else "deactivated"
    log_activity(
        current_user.id,
        'USER_STATUS_CHANGE',
        f"User {user.username} {status_text}",
        {'user_id': user_id, 'new_status': new_status}
    )
    
    flash(f'User {status_text} successfully.', 'success')
    return redirect(request.referrer or url_for('users.list'))

# API endpoints with proper permission checks
@users_bp.route('/api/partner-stats/<partner_id>')
@login_required
def api_partner_stats(partner_id):
    # Check permissions
    if not current_user.is_super_admin() and current_user.id != partner_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_service = UserService()
    stats = user_service.get_partner_statistics(partner_id)
    
    if stats:
        return jsonify({'success': True, 'stats': stats})
    else:
        return jsonify({'success': False, 'error': 'Partner not found'}), 404

@users_bp.route('/api/list')
@login_required
def api_users_list():
    """API endpoint to get users list"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role')
    
    filters = {}
    if role_filter:
        filters['role'] = role_filter
    
    user_service = UserService()
    
    if current_user.is_super_admin():
        result = user_service.get_all_users_with_partners(filters, page, 10)
    elif current_user.is_partner():
        result = user_service.get_partner_agents(current_user.id, filters, page, 10)
    else:
        result = {'users': [], 'total': 0, 'page': 1, 'per_page': 10, 'total_pages': 0}
    
    # Convert users to dict format
    users_data = []
    for user in result['users']:
        user_dict = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'is_active': user.is_active,
            'approval_status': user.approval_status,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }
        
        if user.role == 'AGENT':
            user_dict['partner_id'] = str(user.partner_id) if user.partner_id else None
            user_dict['pdf_generated'] = user.agent_pdf_generated
            user_dict['pdf_limit'] = user.agent_pdf_limit
            if hasattr(user, 'plan') and user.plan:
                user_dict['plan'] = {
                    'id': user.plan.id,
                    'name': user.plan.name
                }
        
        users_data.append(user_dict)
    
    return jsonify({
        'success': True,
        'users': users_data,
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages']
    })