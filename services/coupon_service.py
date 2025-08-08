# services/coupon_service.py
# Enhanced coupon service with partner restrictions

from datetime import datetime
from bson import ObjectId
from models import get_coupons_collection, get_users_collection
from models.coupon import Coupon
from models.user import User
from utils.helpers import log_activity

class CouponService:
    def __init__(self):
        self.coupons = get_coupons_collection()
        self.users = get_users_collection()
    
    def get_coupon_by_id(self, coupon_id):
        """Get coupon by ID"""
        coupon_data = self.coupons.find_one({'_id': ObjectId(coupon_id)})
        return Coupon(coupon_data) if coupon_data else None
    
    def get_coupon_by_code(self, code):
        """Get coupon by code"""
        coupon_data = self.coupons.find_one({'code': code.upper()})
        return Coupon(coupon_data) if coupon_data else None
    
    def get_partner_coupons(self, partner_id, page=1, per_page=10):
        """Get coupons assigned to a partner"""
        # Get partner data to find assigned coupons
        partner = self.users.find_one({'_id': ObjectId(partner_id), 'role': 'PARTNER'})
        if not partner or not partner.get('assigned_coupons'):
            return {
                'coupons': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            }
        
        query = {'_id': {'$in': partner['assigned_coupons']}}
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total = self.coupons.count_documents(query)
        
        # Get paginated results
        coupons_data = self.coupons.find(query).skip(skip).limit(per_page).sort('created_at', -1)
        coupons = [Coupon(data) for data in coupons_data]
        
        return {
            'coupons': coupons,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def create_coupon_with_limits(self, coupon_data, created_by_id):
        """Create coupon with usage limits per partner"""
        # Generate code if not provided
        if not coupon_data.get('code'):
            coupon_data['code'] = Coupon.generate_code()
        else:
            coupon_data['code'] = coupon_data['code'].upper()
        
        # Check if code already exists
        existing = self.coupons.find_one({'code': coupon_data['code']})
        
        if existing:
            return None, "Coupon code already exists"
        
        # Convert dates if provided as strings
        if coupon_data.get('valid_from'):
            coupon_data['valid_from'] = datetime.fromisoformat(coupon_data['valid_from'])
        else:
            coupon_data['valid_from'] = datetime.utcnow()
        
        if coupon_data.get('valid_until'):
            coupon_data['valid_until'] = datetime.fromisoformat(coupon_data['valid_until'])
        
        # Set defaults
        coupon_data['used_count'] = 0
        coupon_data['created_at'] = datetime.utcnow()
        coupon_data['updated_at'] = datetime.utcnow()
        coupon_data['created_by'] = ObjectId(created_by_id)
        
        # Partner usage limits
        if coupon_data.get('partner_limits'):
            # Convert partner IDs to ObjectId
            partner_limits = {}
            for partner_id, limit in coupon_data['partner_limits'].items():
                partner_limits[str(ObjectId(partner_id))] = {
                    'limit': limit,
                    'used': 0
                }
            coupon_data['partner_limits'] = partner_limits
        
        # Convert plan IDs to ObjectId
        if coupon_data.get('applicable_plans'):
            coupon_data['applicable_plans'] = [ObjectId(pid) for pid in coupon_data['applicable_plans']]
        
        # Insert coupon
        result = self.coupons.insert_one(coupon_data)
        
        # Log activity
        log_activity(
            created_by_id,
            'COUPON_CREATED',
            f"Created coupon: {coupon_data['code']} ({coupon_data['name']})",
            {'coupon_id': str(result.inserted_id)}
        )
        
        return str(result.inserted_id), None
    
    def validate_and_apply_coupon_for_partner(self, code, amount, plan_id, partner_id):
        """Validate and apply coupon with partner restrictions"""
        coupon = self.get_coupon_by_code(code)
        
        if not coupon:
            return False, "Invalid coupon code", 0
        
        # Check if coupon is valid
        is_valid, message = coupon.is_valid()
        if not is_valid:
            return False, message, 0
        
        # Check if partner can use this coupon
        partner = self.users.find_one({'_id': ObjectId(partner_id), 'role': 'PARTNER'})
        if partner and partner.get('assigned_coupons'):
            if coupon._id not in partner['assigned_coupons']:
                return False, "This coupon is not available for your account", 0
        
        # Check partner-specific usage limits
        if hasattr(coupon, 'partner_limits') and coupon.partner_limits:
            partner_limit_data = coupon.partner_limits.get(str(partner_id))
            if partner_limit_data:
                if partner_limit_data['used'] >= partner_limit_data['limit']:
                    return False, "Partner usage limit exceeded for this coupon", 0
        
        # Calculate discount
        discount = coupon.calculate_discount(amount, plan_id)
        
        if discount == 0:
            return False, "Coupon not applicable for this purchase", 0
        
        # Increment usage counts
        update_data = {'$inc': {'used_count': 1}}
        
        # Update partner-specific usage
        if hasattr(coupon, 'partner_limits') and coupon.partner_limits and str(partner_id) in coupon.partner_limits:
            update_data['$inc'][f'partner_limits.{partner_id}.used'] = 1
        
        self.coupons.update_one({'_id': coupon._id}, update_data)
        
        return True, "Coupon applied successfully", discount
    
    def get_coupon_usage_by_partner(self, coupon_id):
        """Get usage statistics by partner for a coupon"""
        coupon = self.get_coupon_by_id(coupon_id)
        if not coupon or not hasattr(coupon, 'partner_limits'):
            return []
        
        usage_stats = []
        for partner_id, limit_data in coupon.partner_limits.items():
            partner = self.users.find_one({'_id': ObjectId(partner_id)})
            if partner:
                usage_stats.append({
                    'partner_id': partner_id,
                    'partner_name': partner['full_name'] or partner['username'],
                    'limit': limit_data['limit'],
                    'used': limit_data['used'],
                    'remaining': limit_data['limit'] - limit_data['used']
                })
        
        return usage_stats