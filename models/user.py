from datetime import datetime
from bson import ObjectId
import bcrypt

class User:
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.username = data.get('username')
            self.email = data.get('email')
            self.password = data.get('password')
            self.full_name = data.get('full_name')
            self.phone = data.get('phone')
            self.role = data.get('role', 'AGENT')  # OWNER, ADMIN, AGENT
            self.profile_image = data.get('profile_image')
            self.is_active = data.get('is_active', True)
            self.plan_id = data.get('plan_id')  # For agents
            self.plan_start_date = data.get('plan_start_date')
            self.plan_expiry_date = data.get('plan_expiry_date')
            self.pdf_generated = data.get('pdf_generated', 0)
            self.pdf_limit = data.get('pdf_limit', 0)
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
            self.last_login = data.get('last_login')
            self.created_by = data.get('created_by')
    
    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'password': self.password,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role,
            'profile_image': self.profile_image,
            'is_active': self.is_active,
            'plan_id': self.plan_id,
            'plan_start_date': self.plan_start_date,
            'plan_expiry_date': self.plan_expiry_date,
            'pdf_generated': self.pdf_generated,
            'pdf_limit': self.pdf_limit,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_login': self.last_login,
            'created_by': self.created_by
        }
    
    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    @staticmethod
    def verify_password(password, hashed):
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    @property
    def id(self):
        return str(self._id) if self._id else None
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self._id)
    
    def has_role(self, role):
        return self.role == role
    
    def is_owner(self):
        return self.role == 'OWNER'
    
    def is_admin(self):
        return self.role in ['OWNER', 'ADMIN']
    
    def is_agent(self):
        return self.role == 'AGENT'