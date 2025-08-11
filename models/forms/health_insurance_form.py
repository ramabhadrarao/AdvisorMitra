# models/forms/health_insurance_form.py
from datetime import datetime
from bson import ObjectId

class HealthInsuranceForm:
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.form_link_id = data.get('form_link_id')  # Link used to generate this form
            self.agent_id = data.get('agent_id')
            self.language = data.get('language', 'en')
            
            # Form fields
            self.name = data.get('name')
            self.email = data.get('email')
            self.mobile = data.get('mobile')
            self.city_of_residence = data.get('city_of_residence')
            self.age = data.get('age')
            self.number_of_members = data.get('number_of_members')
            self.eldest_member_age = data.get('eldest_member_age')
            self.pre_existing_diseases = data.get('pre_existing_diseases')
            self.major_surgery = data.get('major_surgery')
            self.existing_insurance = data.get('existing_insurance')
            self.current_coverage = data.get('current_coverage')
            self.port_policy = data.get('port_policy')
            
            # NEW: Preferred report language
            self.report_language = data.get('report_language', 'en')
            
            # Tier city will be calculated based on city
            self.tier_city = data.get('tier_city')
            
            # Metadata
            self.form_timestamp = data.get('form_timestamp', datetime.utcnow())
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
            self.pdf_generated = data.get('pdf_generated', False)
            self.pdf_generated_at = data.get('pdf_generated_at')
            self.pdf_filename = data.get('pdf_filename')
    
    def to_dict(self):
        return {
            'form_link_id': self.form_link_id,
            'agent_id': self.agent_id,
            'language': self.language,
            'name': self.name,
            'email': self.email,
            'mobile': self.mobile,
            'city_of_residence': self.city_of_residence,
            'age': self.age,
            'number_of_members': self.number_of_members,
            'eldest_member_age': self.eldest_member_age,
            'pre_existing_diseases': self.pre_existing_diseases,
            'major_surgery': self.major_surgery,
            'existing_insurance': self.existing_insurance,
            'current_coverage': self.current_coverage,
            'port_policy': self.port_policy,
            'report_language': self.report_language,
            'tier_city': self.tier_city,
            'form_timestamp': self.form_timestamp,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'pdf_generated': self.pdf_generated,
            'pdf_generated_at': self.pdf_generated_at,
            'pdf_filename': self.pdf_filename
        }
    
    @property
    def id(self):
        return str(self._id) if self._id else None
    
    def calculate_tier_city(self):
        """Calculate tier city based on city of residence"""
        tier1_cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 
            'Chennai', 'Kolkata', 'Pune', 'Ahmedabad'
        ]
        
        if self.city_of_residence in tier1_cities:
            self.tier_city = 'Tier 1'
        else:
            self.tier_city = 'Others'
        
        return self.tier_city