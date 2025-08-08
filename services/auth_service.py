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
            ],
            'is_active': True
        })
        
        if not user_data:
            return None, "Invalid username or password"
        
        user = User(user_data)
        
        # Verify password
        if not User.verify_password(password, user.password):
            return None, "Invalid username or password"
        
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
    
    def create_initial_owner(self):
        """Create initial owner account if none exists"""
        owner = self.users.find_one({'role': 'OWNER'})
        
        if not owner:
            owner_data = {
                'username': 'admin',
                'email': 'admin@example.com',
                'password': User.hash_password('admin123'),
                'full_name': 'System Administrator',
                'role': 'OWNER',
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            self.users.insert_one(owner_data)
            print("Initial owner account created: admin/admin123")