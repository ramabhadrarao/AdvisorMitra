from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import get_users_collection, get_plans_collection, get_coupons_collection, get_activities_collection
from utils.decorators import admin_required
from datetime import datetime

dashboard_bp = Blueprint('dashboard_api', __name__)

@dashboard_bp.route('/api/stats')
@login_required
@admin_required
def get_stats():
    """Get dashboard statistics"""
    users = get_users_collection()
    plans = get_plans_collection()
    coupons = get_coupons_collection()
    
    # Get counts based on user role
    if current_user.is_owner():
        total_users = users.count_documents({})
        total_agents = users.count_documents({'role': 'AGENT'})
        active_plans = plans.count_documents({'is_active': True})
        active_coupons = coupons.count_documents({'is_active': True})
    else:
        # Admin can only see agents and admins
        total_users = users.count_documents({'role': {'$in': ['AGENT', 'ADMIN']}})
        total_agents = users.count_documents({'role': 'AGENT'})
        active_plans = 0
        active_coupons = 0
    
    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'total_agents': total_agents,
            'active_plans': active_plans,
            'active_coupons': active_coupons
        }
    })

@dashboard_bp.route('/api/recent-activities')
@login_required
@admin_required
def get_recent_activities():
    """Get recent activities"""
    activities = get_activities_collection()
    users = get_users_collection()
    
    # Get recent activities
    recent = list(activities.find().sort('created_at', -1).limit(10))
    
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