# services/auth_service.py
# Authentication service with enhanced approval workflow

from datetime import datetime
from models import get_users_collection
from models.user import User
from utils.helpers import log_activity
from bson import ObjectId

class AuthService:
    def __init__(self):
        self.users = get_users_collection()
    
    def authenticate_user(self, username, password):
        """Authenticate user with username/email and password"""
        # Find user by username or email
        user_data = self.users.find_one({
            '$or': [
                {'username': username},
                {'email': username}
            ]
        })
        
        if not user_data:
            return None, "Invalid username or password"
        
        user = User(user_data)
        
        # Verify password
        if not User.verify_password(password, user.password):
            return None, "Invalid username or password"
        
        # Check if user can login based on approval status
        if not user.can_login():
            if user.approval_status == 'REJECTED':
                return None, f"Account rejected: {user.rejection_reason or 'Contact administrator'}"
            elif user.approval_status == 'PENDING':
                return None, "Account pending approval"
            elif user.approval_status == 'PARTNER_APPROVED':
                return None, "Account awaiting super admin approval"
            else:
                return None, "Account not active"
        
        # Update last login
        self.users.update_one(
            {'_id': user_data['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        # Log activity
        log_activity(
            user.id,
            'LOGIN',
            f'User {user.username} logged in',
            {'ip': None}  # Can be enhanced to capture IP
        )
        
        return user, None
    
    def change_password(self, user_id, old_password, new_password):
        """Change user password"""
        user_data = self.users.find_one({'_id': ObjectId(user_id)})
        
        if not user_data:
            return False, "User not found"
        
        user = User(user_data)
        
        # Verify old password
        if not User.verify_password(old_password, user.password):
            return False, "Current password is incorrect"
        
        # Hash new password
        hashed_password = User.hash_password(new_password)
        
        # Update password
        self.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'password': hashed_password,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        # Log activity
        log_activity(
            user_id,
            'PASSWORD_CHANGE',
            'Password changed successfully'
        )
        
        return True, "Password changed successfully"
    
    def create_initial_super_admin(self):
        """Create initial super admin account if none exists"""
        super_admin = self.users.find_one({'role': 'SUPER_ADMIN'})
        
        if not super_admin:
            super_admin_data = {
                'username': 'superadmin',
                'email': 'superadmin@example.com',
                'password': User.hash_password('superadmin123'),
                'full_name': 'Super Administrator',
                'role': 'SUPER_ADMIN',
                'is_active': True,
                'approval_status': 'APPROVED',
                'requires_double_approval': False,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            self.users.insert_one(super_admin_data)
            print("Initial super admin account created: superadmin/superadmin123")