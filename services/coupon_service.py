from datetime import datetime
from bson import ObjectId
from models import get_coupons_collection
from models.coupon import Coupon
from utils.helpers import log_activity

class CouponService:
    def __init__(self):
        self.coupons = get_coupons_collection()
    
    def get_coupon_by_id(self, coupon_id):
        """Get coupon by ID"""
        coupon_data = self.coupons.find_one({'_id': ObjectId(coupon_id)})
        return Coupon(coupon_data) if coupon_data else None
    
    def get_coupon_by_code(self, code):
        """Get coupon by code"""
        coupon_data = self.coupons.find_one({'code': code.upper()})
        return Coupon(coupon_data) if coupon_data else None
    
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
    
    def create_coupon(self, coupon_data, created_by_id):
        """Create new coupon"""
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
        """Update coupon details"""
        # Remove fields that shouldn't be updated directly
        update_data.pop('_id', None)
        update_data.pop('code', None)  # Code shouldn't be changed
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
            update_data['applicable_plans'] = [ObjectId(pid) for pid in update_data['applicable_plans']]
        
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
        
        return False, "No changes made"
    
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
    
    def validate_and_apply_coupon(self, code, amount, plan_id=None):
        """Validate and apply coupon"""
        coupon = self.get_coupon_by_code(code)
        
        if not coupon:
            return False, "Invalid coupon code", 0
        
        # Check if coupon is valid
        is_valid, message = coupon.is_valid()
        if not is_valid:
            return False, message, 0
        
        # Calculate discount
        discount = coupon.calculate_discount(amount, plan_id)
        
        if discount == 0:
            return False, "Coupon not applicable for this purchase", 0
        
        # Increment usage count
        self.coupons.update_one(
            {'_id': coupon._id},
            {'$inc': {'used_count': 1}}
        )
        
        return True, "Coupon applied successfully", discount
    
    def get_active_coupons(self):
        """Get all active and valid coupons"""
        now = datetime.utcnow()
        
        coupons_data = self.coupons.find({
            'is_active': True,
            '$or': [
                {'valid_from': {'$lte': now}},
                {'valid_from': None}
            ],
            '$or': [
                {'valid_until': {'$gte': now}},
                {'valid_until': None}
            ]
        }).sort('discount_value', -1)
        
        return [Coupon(data) for data in coupons_data]