import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import current_app
import secrets

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_profile_image(file):
    """Save uploaded profile image and return filename"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(file.filename)
        filename = random_hex + f_ext
        
        # Ensure upload directory exists
        upload_path = os.path.join(current_app.root_path, current_app.config['PROFILE_UPLOAD_FOLDER'])
        os.makedirs(upload_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        return filename
    return None

def delete_profile_image(filename):
    """Delete profile image file"""
    if filename and filename != 'default.png':
        file_path = os.path.join(current_app.root_path, current_app.config['PROFILE_UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

def calculate_plan_expiry(plan):
    """Calculate plan expiry date based on plan period"""
    if plan.period_type == 'YEARLY':
        return datetime.utcnow() + timedelta(days=365 * plan.period_value)
    elif plan.period_type == 'MONTHLY':
        return datetime.utcnow() + timedelta(days=30 * plan.period_value)
    else:  # CUSTOM (days)
        return datetime.utcnow() + timedelta(days=plan.period_value)

def log_activity(user_id, activity_type, description, metadata=None):
    """Log user activity"""
    from models import get_activities_collection
    
    activity = {
        'user_id': user_id,
        'activity_type': activity_type,
        'description': description,
        'metadata': metadata or {},
        'ip_address': None,  # Can be enhanced to capture IP
        'user_agent': None,  # Can be enhanced to capture user agent
        'created_at': datetime.utcnow()
    }
    
    get_activities_collection().insert_one(activity)

def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return ''
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_date(dt):
    """Format date for display"""
    if not dt:
        return ''
    return dt.strftime('%Y-%m-%d')

def paginate_query(collection, query, page, per_page):
    """Paginate MongoDB query results"""
    total = collection.count_documents(query)
    skip = (page - 1) * per_page
    items = list(collection.find(query).skip(skip).limit(per_page))
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }