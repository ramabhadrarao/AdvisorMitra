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
    
    def create_coupon(self, coupon_data, created_by_id):
        """Create coupon with partner limits"""
        return self.create_coupon_with_limits(coupon_data, created_by_id)
    
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
    
    def update_coupon(self, coupon_id, update_data, updated_by_id):
        """Update coupon details including partner limits"""
        # Remove fields that shouldn't be updated
        update_data.pop('_id', None)
        update_data.pop('code', None)
        update_data.pop('created_at', None)
        update_data.pop('created_by', None)
        update_data.pop('used_count', None)
        
        # Convert dates if provided as strings
        if update_data.get('valid_from'):
            update_data['valid_from'] = datetime.fromisoformat(update_data['valid_from'])
        
        if update_data.get('valid_until'):
            update_data['valid_until'] = datetime.fromisoformat(update_data['valid_until'])
        
        # Convert plan IDs to ObjectId
        if update_data.get('applicable_plans'):
            update_data['applicable_plans'] = [ObjectId(pid) for pid in update_data['applicable_plans'] if pid]
        
        # Handle partner limits from form data
        from models import get_users_collection
        users = get_users_collection()
        partners = users.find({'role': 'PARTNER'})
        
        partner_limits = {}
        for partner in partners:
            partner_id = str(partner['_id'])
            limit_key = f'partner_limit_{partner_id}'
            
            # Check if limit was provided in form
            if limit_key in update_data:
                limit_value = update_data.pop(limit_key)
                if limit_value:
                    # Get existing usage count
                    existing_coupon = self.coupons.find_one({'_id': ObjectId(coupon_id)})
                    existing_usage = 0
                    if existing_coupon and existing_coupon.get('partner_limits'):
                        existing_usage = existing_coupon['partner_limits'].get(partner_id, {}).get('used', 0)
                    
                    partner_limits[partner_id] = {
                        'limit': int(limit_value),
                        'used': existing_usage
                    }
        
        if partner_limits:
            update_data['partner_limits'] = partner_limits
        
        # Set updated timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Update coupon
        result = self.coupons.update_one(
            {'_id': ObjectId(coupon_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Log activity
            log_activity(
                updated_by_id,
                'COUPON_UPDATED',
                f"Updated coupon details",
                {'coupon_id': coupon_id}
            )
            return True, "Coupon updated successfully"
        
        return True, "No changes made"
    
    def toggle_coupon_status(self, coupon_id, updated_by_id):
        """Toggle coupon active status"""
        coupon_data = self.coupons.find_one({'_id': ObjectId(coupon_id)})
        if not coupon_data:
            return False, "Coupon not found"
        
        new_status = not coupon_data.get('is_active', True)
        
        self.coupons.update_one(
            {'_id': ObjectId(coupon_id)},
            {'$set': {
                'is_active': new_status,
                'updated_at': datetime.utcnow()
            }}
        )
        
        # Log activity
        status_text = "activated" if new_status else "deactivated"
        log_activity(
            updated_by_id,
            'COUPON_STATUS_CHANGE',
            f"Coupon {status_text}",
            {'coupon_id': coupon_id, 'new_status': new_status}
        )
        
        return True, f"Coupon {status_text} successfully"
    
    def get_all_coupons(self, filters=None, page=1, per_page=10):
        """Get all coupons with pagination"""
        query = filters or {}
        
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
    
    def validate_and_apply_coupon(self, code, amount, plan_id=None):
        """Public method for coupon validation - redirects to partner method"""
        # For backward compatibility
        return self.validate_and_apply_coupon_for_partner(code, amount, plan_id, None)
    
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
        if partner_id:
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
        if partner_id and hasattr(coupon, 'partner_limits') and coupon.partner_limits and str(partner_id) in coupon.partner_limits:
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