from datetime import datetime
from bson import ObjectId
from models import get_users_collection, get_plans_collection
from models.user import User
from models.plan import Plan
from utils.helpers import log_activity, calculate_plan_expiry

class UserService:
    def __init__(self):
        self.users = get_users_collection()
        self.plans = get_plans_collection()
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        user_data = self.users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None
    
    def get_user_by_username(self, username):
        """Get user by username"""
        user_data = self.users.find_one({'username': username})
        return User(user_data) if user_data else None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        user_data = self.users.find_one({'email': email})
        return User(user_data) if user_data else None
    
    def create_user(self, user_data, created_by_id):
        """Create new user"""
        # Check if username or email already exists
        existing = self.users.find_one({
            '$or': [
                {'username': user_data['username']},
                {'email': user_data['email']}
            ]
        })
        
        if existing:
            return None, "Username or email already exists"
        
        # Hash password
        user_data['password'] = User.hash_password(user_data['password'])
        
        # Set timestamps and creator
        user_data['created_at'] = datetime.utcnow()
        user_data['updated_at'] = datetime.utcnow()
        user_data['created_by'] = ObjectId(created_by_id)
        
        # Handle plan assignment for agents
        if user_data.get('role') == 'AGENT' and user_data.get('plan_id'):
            plan_data = self.plans.find_one({'_id': ObjectId(user_data['plan_id'])})
            if plan_data:
                plan = Plan(plan_data)
                user_data['plan_start_date'] = datetime.utcnow()
                user_data['plan_expiry_date'] = calculate_plan_expiry(plan)
                user_data['pdf_limit'] = plan.pdf_limit
                user_data['pdf_generated'] = 0
        
        # Insert user
        result = self.users.insert_one(user_data)
        
        # Log activity
        log_activity(
            created_by_id,
            'USER_CREATED',
            f"Created user: {user_data['username']} ({user_data['role']})",
            {'new_user_id': str(result.inserted_id)}
        )
        
        return str(result.inserted_id), None
    
    def update_user(self, user_id, update_data, updated_by_id):
        """Update user details"""
        # Remove fields that shouldn't be updated directly
        update_data.pop('_id', None)
        update_data.pop('password', None)
        update_data.pop('created_at', None)
        update_data.pop('created_by', None)
        
        # Check if username or email already exists (if being changed)
        if 'username' in update_data or 'email' in update_data:
            existing = self.users.find_one({
                '$and': [
                    {'_id': {'$ne': ObjectId(user_id)}},
                    {'$or': [
                        {'username': update_data.get('username')},
                        {'email': update_data.get('email')}
                    ]}
                ]
            })
            
            if existing:
                return False, "Username or email already exists"
        
        # Set updated timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Update user
        result = self.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Log activity
            log_activity(
                updated_by_id,
                'USER_UPDATED',
                f"Updated user profile",
                {'updated_user_id': user_id}
            )
            return True, "User updated successfully"
        
        return False, "No changes made"
    
    def update_profile_image(self, user_id, filename):
        """Update user profile image"""
        self.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'profile_image': filename,
                'updated_at': datetime.utcnow()
            }}
        )
    
    def assign_plan_to_agent(self, agent_id, plan_id, assigned_by_id):
        """Assign or update plan for an agent"""
        plan_data = self.plans.find_one({'_id': ObjectId(plan_id)})
        if not plan_data:
            return False, "Plan not found"
        
        plan = Plan(plan_data)
        
        update_data = {
            'plan_id': ObjectId(plan_id),
            'plan_start_date': datetime.utcnow(),
            'plan_expiry_date': calculate_plan_expiry(plan),
            'pdf_limit': plan.pdf_limit,
            'pdf_generated': 0,  # Reset counter
            'updated_at': datetime.utcnow()
        }
        
        result = self.users.update_one(
            {'_id': ObjectId(agent_id), 'role': 'AGENT'},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Log activity
            log_activity(
                assigned_by_id,
                'PLAN_ASSIGNED',
                f"Assigned plan '{plan.name}' to agent",
                {'agent_id': agent_id, 'plan_id': plan_id}
            )
            return True, "Plan assigned successfully"
        
        return False, "Failed to assign plan"
    
    def get_all_users(self, filters=None, page=1, per_page=10):
        """Get all users with pagination"""
        query = filters or {}
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total = self.users.count_documents(query)
        
        # Get paginated results
        users_data = self.users.find(query).skip(skip).limit(per_page).sort('created_at', -1)
        users = [User(data) for data in users_data]
        
        # Get plan details for agents
        for user in users:
            if user.role == 'AGENT' and user.plan_id:
                plan_data = self.plans.find_one({'_id': user.plan_id})
                if plan_data:
                    user.plan = Plan(plan_data)
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def get_agents_by_owner(self, owner_id, page=1, per_page=10):
        """Get agents created by a specific owner"""
        return self.get_all_users(
            filters={'role': 'AGENT', 'created_by': ObjectId(owner_id)},
            page=page,
            per_page=per_page
        )
    
    def toggle_user_status(self, user_id, updated_by_id):
        """Toggle user active status"""
        user_data = self.users.find_one({'_id': ObjectId(user_id)})
        if not user_data:
            return False, "User not found"
        
        new_status = not user_data.get('is_active', True)
        
        self.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'is_active': new_status,
                'updated_at': datetime.utcnow()
            }}
        )
        
        # Log activity
        status_text = "activated" if new_status else "deactivated"
        log_activity(
            updated_by_id,
            'USER_STATUS_CHANGE',
            f"User {status_text}",
            {'user_id': user_id, 'new_status': new_status}
        )
        
        return True, f"User {status_text} successfully"