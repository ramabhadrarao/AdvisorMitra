# services/user_service.py
# User service with approval workflow and partner management

from datetime import datetime
from bson import ObjectId
from models import get_users_collection, get_plans_collection, get_registration_links_collection
from models.user import User
from models.plan import Plan
from utils.helpers import log_activity, calculate_plan_expiry, generate_registration_link
import secrets

class UserService:
    def __init__(self):
        self.users = get_users_collection()
        self.plans = get_plans_collection()
        self.registration_links = get_registration_links_collection()
    
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
    
    def create_partner(self, partner_data, created_by_id):
        """Create new partner (called by super admin)"""
        # Check if username or email already exists
        existing = self.users.find_one({
            '$or': [
                {'username': partner_data['username']},
                {'email': partner_data['email']}
            ]
        })
        
        if existing:
            return None, "Username or email already exists"
        
        # Hash password
        partner_data['password'] = User.hash_password(partner_data['password'])
        
        # Set partner-specific fields
        partner_data['role'] = 'PARTNER'
        partner_data['created_at'] = datetime.utcnow()
        partner_data['updated_at'] = datetime.utcnow()
        partner_data['created_by'] = ObjectId(created_by_id)
        partner_data['approval_status'] = 'APPROVED' if not partner_data.get('requires_double_approval') else 'PENDING'
        
        # Handle approval
        if not partner_data.get('requires_double_approval'):
            partner_data['super_admin_approved'] = True
            partner_data['super_admin_approved_at'] = datetime.utcnow()
            partner_data['super_admin_approved_by'] = ObjectId(created_by_id)
        
        # Convert plan and coupon IDs to ObjectId
        if partner_data.get('assigned_plans'):
            partner_data['assigned_plans'] = [ObjectId(pid) for pid in partner_data['assigned_plans']]
        
        if partner_data.get('assigned_coupons'):
            partner_data['assigned_coupons'] = [ObjectId(cid) for cid in partner_data['assigned_coupons']]
        
        # Insert partner
        result = self.users.insert_one(partner_data)
        
        # Log activity
        log_activity(
            created_by_id,
            'PARTNER_CREATED',
            f"Created partner: {partner_data['username']}",
            {'new_partner_id': str(result.inserted_id)}
        )
        
        return str(result.inserted_id), None
    
    def create_agent_registration_link(self, partner_id, created_by_id, created_by_role):
        """Create registration link for agent"""
        # Generate unique token
        token = secrets.token_urlsafe(32)
        
        link_data = {
            'token': token,
            'partner_id': ObjectId(partner_id),
            'created_by': ObjectId(created_by_id),
            'created_by_role': created_by_role,
            'created_at': datetime.utcnow(),
            'used': False,
            'used_by': None,
            'used_at': None
        }
        
        self.registration_links.insert_one(link_data)
        
        # Log activity
        log_activity(
            created_by_id,
            'REGISTRATION_LINK_CREATED',
            f"Created agent registration link",
            {'partner_id': partner_id, 'token': token}
        )
        
        return token
    
    def register_agent_via_link(self, agent_data, token):
        """Register agent using registration link"""
        # Validate token
        link = self.registration_links.find_one({'token': token, 'used': False})
        
        if not link:
            return None, "Invalid or expired registration link"
        
        # Check if username or email already exists
        existing = self.users.find_one({
            '$or': [
                {'username': agent_data['username']},
                {'email': agent_data['email']}
            ]
        })
        
        if existing:
            return None, "Username or email already exists"
        
        # Hash password
        agent_data['password'] = User.hash_password(agent_data['password'])
        
        # Set agent-specific fields
        agent_data['role'] = 'AGENT'
        agent_data['partner_id'] = link['partner_id']
        agent_data['created_at'] = datetime.utcnow()
        agent_data['updated_at'] = datetime.utcnow()
        agent_data['approval_status'] = 'PENDING'
        agent_data['registered_via_link'] = token
        agent_data['registration_link_sent_by'] = link['created_by']
        
        # Check if double approval is required
        partner = self.users.find_one({'_id': link['partner_id']})
        if partner:
            agent_data['requires_double_approval'] = partner.get('requires_double_approval', True)
        
        # Insert agent
        result = self.users.insert_one(agent_data)
        
        # Mark link as used
        self.registration_links.update_one(
            {'token': token},
            {
                '$set': {
                    'used': True,
                    'used_by': result.inserted_id,
                    'used_at': datetime.utcnow()
                }
            }
        )
        
        # Log activity
        log_activity(
            str(result.inserted_id),
            'AGENT_REGISTERED',
            f"Agent {agent_data['username']} registered via link",
            {'partner_id': str(link['partner_id'])}
        )
        
        return str(result.inserted_id), None
    
    def approve_user(self, user_id, approver_id, approver_role):
        """Approve user (partner approves agent, super admin approves partner/agent)"""
        user_data = self.users.find_one({'_id': ObjectId(user_id)})
        if not user_data:
            return False, "User not found"
        
        user = User(user_data)
        update_data = {'updated_at': datetime.utcnow()}
        
        # Partner approving agent
        if approver_role == 'PARTNER' and user.role == 'AGENT':
            if str(user.partner_id) != approver_id:
                return False, "You can only approve your own agents"
            
            update_data['partner_approved'] = True
            update_data['partner_approved_at'] = datetime.utcnow()
            update_data['partner_approved_by'] = ObjectId(approver_id)
            
            if not user.requires_double_approval:
                update_data['approval_status'] = 'APPROVED'
            else:
                update_data['approval_status'] = 'PARTNER_APPROVED'
        
        # Super admin approving partner or agent
        elif approver_role == 'SUPER_ADMIN':
            update_data['super_admin_approved'] = True
            update_data['super_admin_approved_at'] = datetime.utcnow()
            update_data['super_admin_approved_by'] = ObjectId(approver_id)
            
            if user.role == 'PARTNER' or (user.role == 'AGENT' and user.partner_approved):
                update_data['approval_status'] = 'APPROVED'
            elif user.role == 'AGENT' and not user.requires_double_approval:
                update_data['approval_status'] = 'APPROVED'
        
        else:
            return False, "Invalid approval combination"
        
        # Update user
        self.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        # Log activity
        log_activity(
            approver_id,
            'USER_APPROVED',
            f"{approver_role} approved {user.role} {user.username}",
            {'approved_user_id': user_id}
        )
        
        return True, "User approved successfully"
    
    def reject_user(self, user_id, rejector_id, rejector_role, reason):
        """Reject user"""
        user_data = self.users.find_one({'_id': ObjectId(user_id)})
        if not user_data:
            return False, "User not found"
        
        user = User(user_data)
        
        # Check permissions
        if rejector_role == 'PARTNER' and user.role == 'AGENT':
            if str(user.partner_id) != rejector_id:
                return False, "You can only reject your own agents"
        elif rejector_role != 'SUPER_ADMIN':
            return False, "Insufficient permissions"
        
        # Update user
        self.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'approval_status': 'REJECTED',
                    'rejection_reason': reason,
                    'updated_at': datetime.utcnow(),
                    'is_active': False
                }
            }
        )
        
        # Log activity
        log_activity(
            rejector_id,
            'USER_REJECTED',
            f"{rejector_role} rejected {user.role} {user.username}: {reason}",
            {'rejected_user_id': user_id}
        )
        
        return True, "User rejected"
    
    def get_partner_agents(self, partner_id, filters=None, page=1, per_page=10):
        """Get agents belonging to a partner"""
        query = {'role': 'AGENT', 'partner_id': ObjectId(partner_id)}
        if filters:
            query.update(filters)
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total = self.users.count_documents(query)
        
        # Get paginated results
        users_data = self.users.find(query).skip(skip).limit(per_page).sort('created_at', -1)
        users = [User(data) for data in users_data]
        
        # Get plan details for agents
        for user in users:
            if user.plan_id:
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
    
    def get_all_users_with_partners(self, filters=None, page=1, per_page=10):
        """Get all users with partner information (for super admin)"""
        query = filters or {}
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total = self.users.count_documents(query)
        
        # Get paginated results
        users_data = self.users.find(query).skip(skip).limit(per_page).sort('created_at', -1)
        users = []
        
        for data in users_data:
            user = User(data)
            
            # Get partner info for agents
            if user.role == 'AGENT' and user.partner_id:
                partner_data = self.users.find_one({'_id': user.partner_id})
                if partner_data:
                    user.partner = User(partner_data)
            
            # Get plan details for agents
            if user.role == 'AGENT' and user.plan_id:
                plan_data = self.plans.find_one({'_id': user.plan_id})
                if plan_data:
                    user.plan = Plan(plan_data)
            
            users.append(user)
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def update_partner_limits(self, partner_id, pdf_limit, updated_by_id):
        """Update partner PDF limits"""
        result = self.users.update_one(
            {'_id': ObjectId(partner_id), 'role': 'PARTNER'},
            {
                '$set': {
                    'pdf_limit': pdf_limit,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            log_activity(
                updated_by_id,
                'PARTNER_LIMITS_UPDATED',
                f"Updated partner PDF limit to {pdf_limit}",
                {'partner_id': partner_id}
            )
            return True, "Partner limits updated successfully"
        
        return False, "Failed to update partner limits"
    
    def get_partner_statistics(self, partner_id):
        """Get statistics for a partner"""
        # Get partner data
        partner = self.users.find_one({'_id': ObjectId(partner_id), 'role': 'PARTNER'})
        if not partner:
            return None
        
        # Count agents
        total_agents = self.users.count_documents({'partner_id': ObjectId(partner_id), 'role': 'AGENT'})
        active_agents = self.users.count_documents({
            'partner_id': ObjectId(partner_id), 
            'role': 'AGENT',
            'is_active': True,
            'approval_status': 'APPROVED'
        })
        pending_agents = self.users.count_documents({
            'partner_id': ObjectId(partner_id), 
            'role': 'AGENT',
            'approval_status': {'$in': ['PENDING', 'PARTNER_APPROVED']}
        })
        
        # Calculate PDF usage
        agents = self.users.find({'partner_id': ObjectId(partner_id), 'role': 'AGENT'})
        total_pdfs_generated = sum(agent.get('agent_pdf_generated', 0) for agent in agents)
        
        return {
            'total_agents': total_agents,
            'active_agents': active_agents,
            'pending_agents': pending_agents,
            'pdf_limit': partner.get('pdf_limit', 0),
            'pdf_generated': total_pdfs_generated,
            'pdf_remaining': max(0, partner.get('pdf_limit', 0) - total_pdfs_generated)
        }