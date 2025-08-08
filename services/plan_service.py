from datetime import datetime
from bson import ObjectId
from models import get_plans_collection
from models.plan import Plan
from utils.helpers import log_activity

class PlanService:
    def __init__(self):
        self.plans = get_plans_collection()
    
    def get_plan_by_id(self, plan_id):
        """Get plan by ID"""
        plan_data = self.plans.find_one({'_id': ObjectId(plan_id)})
        return Plan(plan_data) if plan_data else None
    
    def get_all_plans(self, filters=None, page=1, per_page=10):
        """Get all plans with pagination"""
        query = filters or {}
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total = self.plans.count_documents(query)
        
        # Get paginated results
        plans_data = self.plans.find(query).skip(skip).limit(per_page).sort('created_at', -1)
        plans = [Plan(data) for data in plans_data]
        
        return {
            'plans': plans,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def get_active_plans(self):
        """Get all active plans"""
        plans_data = self.plans.find({'is_active': True}).sort('price', 1)
        return [Plan(data) for data in plans_data]
    
    def create_plan(self, plan_data, created_by_id):
        """Create new plan"""
        # Check if plan name already exists
        existing = self.plans.find_one({'name': plan_data['name']})
        
        if existing:
            return None, "Plan name already exists"
        
        # Set timestamps and creator
        plan_data['created_at'] = datetime.utcnow()
        plan_data['updated_at'] = datetime.utcnow()
        plan_data['created_by'] = ObjectId(created_by_id)
        
        # Insert plan
        result = self.plans.insert_one(plan_data)
        
        # Log activity
        log_activity(
            created_by_id,
            'PLAN_CREATED',
            f"Created plan: {plan_data['name']}",
            {'plan_id': str(result.inserted_id)}
        )
        
        return str(result.inserted_id), None
    
    def update_plan(self, plan_id, update_data, updated_by_id):
        """Update plan details"""
        # Remove fields that shouldn't be updated directly
        update_data.pop('_id', None)
        update_data.pop('created_at', None)
        update_data.pop('created_by', None)
        
        # Check if plan name already exists (if being changed)
        if 'name' in update_data:
            existing = self.plans.find_one({
                '$and': [
                    {'_id': {'$ne': ObjectId(plan_id)}},
                    {'name': update_data['name']}
                ]
            })
            
            if existing:
                return False, "Plan name already exists"
        
        # Set updated timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        # Update plan
        result = self.plans.update_one(
            {'_id': ObjectId(plan_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Log activity
            log_activity(
                updated_by_id,
                'PLAN_UPDATED',
                f"Updated plan details",
                {'plan_id': plan_id}
            )
            return True, "Plan updated successfully"
        
        return False, "No changes made"
    
    def toggle_plan_status(self, plan_id, updated_by_id):
        """Toggle plan active status"""
        plan_data = self.plans.find_one({'_id': ObjectId(plan_id)})
        if not plan_data:
            return False, "Plan not found"
        
        new_status = not plan_data.get('is_active', True)
        
        self.plans.update_one(
            {'_id': ObjectId(plan_id)},
            {'$set': {
                'is_active': new_status,
                'updated_at': datetime.utcnow()
            }}
        )
        
        # Log activity
        status_text = "activated" if new_status else "deactivated"
        log_activity(
            updated_by_id,
            'PLAN_STATUS_CHANGE',
            f"Plan {status_text}",
            {'plan_id': plan_id, 'new_status': new_status}
        )
        
        return True, f"Plan {status_text} successfully"
    
    def delete_plan(self, plan_id, deleted_by_id):
        """Delete plan (soft delete by marking inactive)"""
        # Check if plan is assigned to any users
        from models import get_users_collection
        users = get_users_collection()
        
        assigned_users = users.count_documents({'plan_id': ObjectId(plan_id)})
        if assigned_users > 0:
            return False, f"Cannot delete plan. It is assigned to {assigned_users} user(s)."
        
        # Soft delete by marking inactive
        result = self.plans.update_one(
            {'_id': ObjectId(plan_id)},
            {'$set': {
                'is_active': False,
                'updated_at': datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            # Log activity
            log_activity(
                deleted_by_id,
                'PLAN_DELETED',
                f"Deleted plan",
                {'plan_id': plan_id}
            )
            return True, "Plan deleted successfully"
        
        return False, "Failed to delete plan"