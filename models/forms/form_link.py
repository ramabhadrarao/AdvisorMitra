# models/forms/form_link.py
from datetime import datetime
from bson import ObjectId
import secrets

class FormLink:
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.token = data.get('token')
            self.form_type = data.get('form_type')  # health_insurance, term_insurance, etc.
            self.agent_id = data.get('agent_id')
            self.agent_name = data.get('agent_name')
            self.agent_phone = data.get('agent_phone')
            self.language = data.get('language', 'en')
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.expires_at = data.get('expires_at')
            self.is_active = data.get('is_active', True)
            self.usage_count = data.get('usage_count', 0)
            self.usage_limit = data.get('usage_limit')  # None for unlimited
    
    def to_dict(self):
        return {
            'token': self.token,
            'form_type': self.form_type,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'agent_phone': self.agent_phone,
            'language': self.language,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'usage_limit': self.usage_limit
        }
    
    @property
    def id(self):
        return str(self._id) if self._id else None
    
    @staticmethod
    def generate_token():
        """Generate unique token for form link"""
        return secrets.token_urlsafe(32)
    
    def is_valid(self):
        """Check if form link is valid"""
        if not self.is_active:
            return False, "Link is not active"
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False, "Link has expired"
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False, "Link usage limit exceeded"
        
        return True, "Valid"