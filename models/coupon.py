from datetime import datetime
from bson import ObjectId
import string
import random

class Coupon:
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.code = data.get('code')
            self.name = data.get('name')
            self.description = data.get('description')
            self.discount_type = data.get('discount_type', 'PERCENTAGE')  # PERCENTAGE, FIXED
            self.discount_value = data.get('discount_value', 0)
            self.min_purchase_amount = data.get('min_purchase_amount', 0)
            self.max_discount_amount = data.get('max_discount_amount')  # For percentage discounts
            self.usage_limit = data.get('usage_limit')  # None for unlimited
            self.used_count = data.get('used_count', 0)
            self.valid_from = data.get('valid_from', datetime.utcnow())
            self.valid_until = data.get('valid_until')
            self.is_active = data.get('is_active', True)
            self.applicable_plans = data.get('applicable_plans', [])  # Empty means all plans
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
            self.created_by = data.get('created_by')
    
    def to_dict(self):
        return {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'min_purchase_amount': self.min_purchase_amount,
            'max_discount_amount': self.max_discount_amount,
            'usage_limit': self.usage_limit,
            'used_count': self.used_count,
            'valid_from': self.valid_from,
            'valid_until': self.valid_until,
            'is_active': self.is_active,
            'applicable_plans': self.applicable_plans,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by
        }
    
    @property
    def id(self):
        return str(self._id) if self._id else None
    
    @staticmethod
    def generate_code(length=8):
        """Generate a random coupon code"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def is_valid(self):
        """Check if coupon is currently valid"""
        now = datetime.utcnow()
        
        if not self.is_active:
            return False, "Coupon is not active"
        
        if self.valid_from and now < self.valid_from:
            return False, "Coupon is not yet valid"
        
        if self.valid_until and now > self.valid_until:
            return False, "Coupon has expired"
        
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit exceeded"
        
        return True, "Valid"
    
    def calculate_discount(self, amount, plan_id=None):
        """Calculate discount amount"""
        if plan_id and self.applicable_plans and str(plan_id) not in self.applicable_plans:
            return 0
        
        if amount < self.min_purchase_amount:
            return 0
        
        if self.discount_type == 'PERCENTAGE':
            discount = amount * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        else:
            return min(self.discount_value, amount)