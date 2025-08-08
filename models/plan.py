from datetime import datetime
from bson import ObjectId

class Plan:
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.name = data.get('name')
            self.description = data.get('description')
            self.period_type = data.get('period_type', 'YEARLY')  # YEARLY, MONTHLY, CUSTOM
            self.period_value = data.get('period_value', 1)  # Number of months/years
            self.price = data.get('price', 0)
            self.pdf_limit = data.get('pdf_limit', 0)
            self.features = data.get('features', [])
            self.is_active = data.get('is_active', True)
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
            self.created_by = data.get('created_by')
    
    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'period_type': self.period_type,
            'period_value': self.period_value,
            'price': self.price,
            'pdf_limit': self.pdf_limit,
            'features': self.features,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by
        }
    
    @property
    def id(self):
        return str(self._id) if self._id else None
    
    def get_period_display(self):
        if self.period_type == 'YEARLY':
            return f"{self.period_value} Year{'s' if self.period_value > 1 else ''}"
        elif self.period_type == 'MONTHLY':
            return f"{self.period_value} Month{'s' if self.period_value > 1 else ''}"
        else:
            return f"Custom ({self.period_value} days)"