# services/forms/health_insurance_service.py
from datetime import datetime, timedelta
from bson import ObjectId
from models.forms import get_health_insurance_forms_collection, get_form_links_collection
from models.forms.health_insurance_form import HealthInsuranceForm
from models.forms.form_link import FormLink
from models import get_users_collection
from utils.helpers import log_activity
import subprocess
import os
from flask import current_app

class HealthInsuranceFormService:
    def __init__(self):
        self.forms = get_health_insurance_forms_collection()
        self.form_links = get_form_links_collection()
        self.users = get_users_collection()
    
    def create_form_link(self, agent_id, language='en', expires_days=30, usage_limit=None):
        """Create a form link for health insurance"""
        # Get agent details
        agent = self.users.find_one({'_id': ObjectId(agent_id)})
        if not agent:
            return None, "Agent not found"
        
        # Check if agent has active plan and PDF limit
        if not agent.get('plan_id') or agent.get('agent_pdf_generated', 0) >= agent.get('agent_pdf_limit', 0):
            return None, "Agent has reached PDF generation limit"
        
        # Create form link
        link_data = {
            'token': FormLink.generate_token(),
            'form_type': 'health_insurance',
            'agent_id': ObjectId(agent_id),
            'agent_name': agent.get('full_name', agent.get('username')),
            'agent_phone': agent.get('phone', ''),
            'language': language,
            'created_by': ObjectId(agent_id),
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(days=expires_days) if expires_days else None,
            'is_active': True,
            'usage_count': 0,
            'usage_limit': usage_limit
        }
        
        result = self.form_links.insert_one(link_data)
        
        # Log activity
        log_activity(
            agent_id,
            'FORM_LINK_CREATED',
            f"Created health insurance form link",
            {'link_id': str(result.inserted_id), 'language': language}
        )
        
        return str(result.inserted_id), link_data['token']
    
    def get_form_link(self, token):
        """Get form link by token"""
        link_data = self.form_links.find_one({'token': token})
        return FormLink(link_data) if link_data else None
    
    def submit_form(self, form_data, token):
        """Submit health insurance form"""
        # Validate token
        link = self.get_form_link(token)
        if not link:
            return None, "Invalid form link"
        
        # Check if link is valid
        is_valid, message = link.is_valid()
        if not is_valid:
            return None, message
        
        # Check agent PDF limit
        agent = self.users.find_one({'_id': link.agent_id})
        if agent.get('agent_pdf_generated', 0) >= agent.get('agent_pdf_limit', 0):
            return None, "Agent has reached PDF generation limit"
        
        # Add metadata to form data
        form_data['form_link_id'] = link._id
        form_data['agent_id'] = link.agent_id
        form_data['language'] = form_data.get('language', link.language)
        form_data['created_at'] = datetime.utcnow()
        form_data['updated_at'] = datetime.utcnow()
        
        # Calculate tier city
        form = HealthInsuranceForm(form_data)
        form.calculate_tier_city()
        form_data['tier_city'] = form.tier_city
        
        # Insert form
        result = self.forms.insert_one(form_data)
        
        # Update link usage count
        self.form_links.update_one(
            {'_id': link._id},
            {'$inc': {'usage_count': 1}}
        )
        
        # Log activity
        log_activity(
            str(link.agent_id),
            'FORM_SUBMITTED',
            f"Health insurance form submitted by {form_data.get('name')}",
            {'form_id': str(result.inserted_id)}
        )
        
        return str(result.inserted_id), None
    
    def get_form_by_id(self, form_id):
        """Get form by ID"""
        form_data = self.forms.find_one({'_id': ObjectId(form_id)})
        return HealthInsuranceForm(form_data) if form_data else None
    
    def get_agent_forms(self, agent_id, page=1, per_page=10):
        """Get all forms submitted via agent's links"""
        query = {'agent_id': ObjectId(agent_id)}
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total = self.forms.count_documents(query)
        
        # Get paginated results
        forms_data = self.forms.find(query).skip(skip).limit(per_page).sort('created_at', -1)
        forms = [HealthInsuranceForm(data) for data in forms_data]
        
        return {
            'forms': forms,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def toggle_link_status(self, link_id, agent_id):
        """Toggle form link active status"""
        # Get link and verify ownership
        link_data = self.form_links.find_one({
            '_id': ObjectId(link_id),
            'agent_id': ObjectId(agent_id)
        })
        
        if not link_data:
            return False
        
        # Toggle status
        new_status = not link_data.get('is_active', True)
        
        self.form_links.update_one(
            {'_id': ObjectId(link_id)},
            {'$set': {'is_active': new_status}}
        )
        
        return True
    
    def generate_pdf(self, form_id, agent_id):
        """Generate PDF for health insurance form"""
        form = self.get_form_by_id(form_id)
        if not form:
            return None, "Form not found"
        
        # Verify agent owns this form
        if str(form.agent_id) != str(agent_id):
            return None, "Unauthorized access"
        
        # Get agent details
        agent = self.users.find_one({'_id': ObjectId(agent_id)})
        if not agent:
            return None, "Agent not found"
        
        # Check PDF limit
        if agent.get('agent_pdf_generated', 0) >= agent.get('agent_pdf_limit', 0):
            return None, "PDF generation limit reached"
        
        # Check if PDF already generated
        if form.pdf_generated and form.pdf_filename:
            pdf_path = os.path.join('/root/generated_pdfs', form.pdf_filename)
            if os.path.exists(pdf_path):
                return form.pdf_filename, None
        
        try:
            # Prepare data for PDF generation
            # Note: You'll need to adapt the PDF generator script to accept form data
            # For now, we'll use the email as the identifier
            
            # Call PDF generator
            cmd = [
                'python3',
                '/path/to/AM-MF-HealthInsurance-en.py',  # Update this path
                form.email,
                agent.get('full_name', 'Agent'),
                agent.get('phone', '')
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return None, f"PDF generation failed: {result.stderr}"
            
            # Extract filename from output
            output_lines = result.stdout.strip().split('\n')
            pdf_filename = None
            
            for line in output_lines:
                if line.startswith('PDF_FILENAME='):
                    pdf_filename = line.split('=')[1]
                    break
            
            if not pdf_filename:
                return None, "PDF filename not found in output"
            
            # Update form with PDF info
            self.forms.update_one(
                {'_id': ObjectId(form_id)},
                {
                    '$set': {
                        'pdf_generated': True,
                        'pdf_generated_at': datetime.utcnow(),
                        'pdf_filename': pdf_filename,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Increment agent's PDF count
            self.users.update_one(
                {'_id': ObjectId(agent_id)},
                {'$inc': {'agent_pdf_generated': 1}}
            )
            
            # Update partner's PDF count
            if agent.get('partner_id'):
                self.users.update_one(
                    {'_id': agent['partner_id']},
                    {'$inc': {'pdf_generated': 1}}
                )
            
            # Log activity
            log_activity(
                agent_id,
                'PDF_GENERATED',
                f"Generated health insurance PDF for {form.name}",
                {'form_id': form_id, 'pdf_filename': pdf_filename}
            )
            
            return pdf_filename, None
            
        except Exception as e:
            return None, f"PDF generation error: {str(e)}"
    
    def get_form_links(self, agent_id, page=1, per_page=10):
        """Get all form links created by agent"""
        query = {'agent_id': ObjectId(agent_id), 'form_type': 'health_insurance'}
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total = self.form_links.count_documents(query)
        
        # Get paginated results
        links_data = self.form_links.find(query).skip(skip).limit(per_page).sort('created_at', -1)
        links = [FormLink(data) for data in links_data]
        
        return {
            'links': links,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }