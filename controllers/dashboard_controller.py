# controllers/dashboard_controller.py
# Enhanced dashboard with role-specific views

from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user
from models import get_users_collection, get_plans_collection, get_coupons_collection, get_activities_collection
from services.user_service import UserService
from services.plan_service import PlanService
from services.coupon_service import CouponService
from utils.decorators import admin_required
from datetime import datetime

dashboard_bp = Blueprint('dashboard_api', __name__)

@dashboard_bp.route('/api/dashboard-stats')
@login_required
def get_dashboard_stats():
    """Get role-specific dashboard statistics"""
    if current_user.is_super_admin():
        return get_super_admin_stats()
    elif current_user.is_partner():
        return get_partner_stats()
    elif current_user.is_agent():
        return get_agent_stats()
    else:
        return jsonify({'error': 'Invalid role'}), 400

def get_super_admin_stats():
    """Get super admin dashboard statistics"""
    users = get_users_collection()
    plans = get_plans_collection()
    coupons = get_coupons_collection()
    
    total_partners = users.count_documents({'role': 'PARTNER'})
    active_partners = users.count_documents({'role': 'PARTNER', 'is_active': True, 'approval_status': 'APPROVED'})
    total_agents = users.count_documents({'role': 'AGENT'})
    active_agents = users.count_documents({'role': 'AGENT', 'is_active': True, 'approval_status': 'APPROVED'})
    pending_approvals = users.count_documents({'approval_status': {'$in': ['PENDING', 'PARTNER_APPROVED']}})
    active_plans = plans.count_documents({'is_active': True})
    active_coupons = coupons.count_documents({'is_active': True})
    
    # Calculate total PDF usage across all partners
    partners = users.find({'role': 'PARTNER'})
    total_pdf_limit = sum(p.get('pdf_limit', 0) for p in partners)
    
    # Calculate total PDFs generated
    agents = users.find({'role': 'AGENT'})
    total_pdfs_generated = sum(a.get('agent_pdf_generated', 0) for a in agents)
    
    return jsonify({
        'success': True,
        'stats': {
            'total_partners': total_partners,
            'active_partners': active_partners,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'pending_approvals': pending_approvals,
            'active_plans': active_plans,
            'active_coupons': active_coupons,
            'total_pdf_limit': total_pdf_limit,
            'total_pdfs_generated': total_pdfs_generated
        }
    })

def get_partner_stats():
    """Get partner dashboard statistics"""
    user_service = UserService()
    stats = user_service.get_partner_statistics(current_user.id)
    
    # Add assigned resources count
    stats['assigned_plans'] = len(current_user.assigned_plans) if current_user.assigned_plans else 0
    stats['assigned_coupons'] = len(current_user.assigned_coupons) if current_user.assigned_coupons else 0
    
    return jsonify({
        'success': True,
        'stats': stats
    })

def get_agent_stats():
    """Get agent dashboard statistics"""
    stats = {
        'plan_status': 'No Plan',
        'days_remaining': 0,
        'pdf_generated': current_user.agent_pdf_generated,
        'pdf_limit': current_user.agent_pdf_limit,
        'pdf_remaining': max(0, current_user.agent_pdf_limit - current_user.agent_pdf_generated)
    }
    
    if current_user.plan_expiry_date:
        now = datetime.utcnow()
        if current_user.plan_expiry_date > now:
            stats['plan_status'] = 'Active'
            stats['days_remaining'] = (current_user.plan_expiry_date - now).days
        else:
            stats['plan_status'] = 'Expired'
    
    return jsonify({
        'success': True,
        'stats': stats
    })

@dashboard_bp.route('/api/recent-activities')
@login_required
def get_recent_activities():
    """Get recent activities based on user role"""
    activities = get_activities_collection()
    users = get_users_collection()
    
    # Build query based on role
    query = {}
    if current_user.is_partner():
        # Get activities for partner and their agents
        agent_ids = [a['_id'] for a in users.find({'partner_id': current_user._id, 'role': 'AGENT'})]
        query = {'$or': [
            {'user_id': current_user._id},
            {'user_id': {'$in': agent_ids}},
            {'metadata.partner_id': str(current_user._id)}
        ]}
    elif current_user.is_agent():
        # Get only agent's own activities
        query = {'user_id': current_user._id}
    
    # Super admin sees all activities (no filter)
    
    # Get recent activities
    recent = list(activities.find(query).sort('created_at', -1).limit(10))
    
    # Format activities with user info
    formatted_activities = []
    for activity in recent:
        user_data = users.find_one({'_id': activity.get('user_id')})
        formatted_activities.append({
            'id': str(activity['_id']),
            'user': user_data['username'] if user_data else 'Unknown',
            'type': activity.get('activity_type'),
            'description': activity.get('description'),
            'created_at': activity.get('created_at').isoformat() if activity.get('created_at') else None
        })
    
    return jsonify({
        'success': True,
        'activities': formatted_activities
    })