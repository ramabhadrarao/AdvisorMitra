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

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@login_required
@admin_required
def list():
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