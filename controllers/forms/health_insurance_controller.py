# controllers/forms/health_insurance_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from services.forms.health_insurance_service import HealthInsuranceFormService
from utils.decorators import login_required
import os
from datetime import timedelta, datetime

health_insurance_bp = Blueprint('health_insurance', __name__)

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'हिंदी',
    'mr': 'मराठी', 
    'gu': 'ગુજરાતી',
    'te': 'తెలుగు',
    'bn': 'বাংলা',
    'kn': 'ಕನ್ನಡ',
    'ta': 'தமிழ்',
    'ml': 'മലയാളം'
}

@health_insurance_bp.route('/')
@login_required
def index():
    """List all health insurance forms for agent"""
    if not current_user.is_agent():
        flash('Only agents can access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    service = HealthInsuranceFormService()
    result = service.get_agent_forms(current_user.id, page)
    
    # Convert form dicts to objects for template
    class FormObject:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
        
        @property
        def id(self):
            return str(self._id) if hasattr(self, '_id') else str(getattr(self, 'id', ''))
    
    forms = [FormObject(form) for form in result['forms']]
    result['forms'] = forms
    
    return render_template('forms/health_insurance/list.html', **result)

@health_insurance_bp.route('/links')
@login_required
def links():
    """List all form links created by agent"""
    if not current_user.is_agent():
        flash('Only agents can access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    service = HealthInsuranceFormService()
    result = service.get_form_links(current_user.id, page)
    
    # Convert link dicts to objects for template
    class LinkObject:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
        
        @property
        def id(self):
            return str(self._id) if hasattr(self, '_id') else str(getattr(self, 'id', ''))
    
    links = [LinkObject(link) for link in result['links']]
    result['links'] = links
    
    return render_template('forms/health_insurance/links.html', **result)

@health_insurance_bp.route('/create-link', methods=['GET', 'POST'])
@login_required
def create_link():
    """Create new form link"""
    if not current_user.is_agent():
        flash('Only agents can create form links.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Check PDF limit
    if current_user.agent_pdf_generated >= current_user.agent_pdf_limit:
        flash('You have reached your PDF generation limit.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    if request.method == 'POST':
        language = request.form.get('language', 'en')
        expires_days = int(request.form.get('expires_days', 30))
        usage_limit = request.form.get('usage_limit')
        usage_limit = int(usage_limit) if usage_limit else None
        
        service = HealthInsuranceFormService()
        link_id, token = service.create_form_link(
            current_user.id,
            language,
            expires_days,
            usage_limit
        )
        
        if link_id:
            # Generate full URL
            form_url = url_for('health_insurance.public_form', token=token, _external=True)
            return render_template('forms/health_insurance/link_created.html', 
                                 form_url=form_url,
                                 token=token,
                                 language=SUPPORTED_LANGUAGES[language])
        else:
            flash(token, 'danger')  # token contains error message in case of failure
    
    return render_template('forms/health_insurance/create_link.html',
                         languages=SUPPORTED_LANGUAGES,
                         pdf_remaining=current_user.agent_pdf_limit - current_user.agent_pdf_generated)

@health_insurance_bp.route('/form/<token>', methods=['GET', 'POST'])
def public_form(token):
    """Public form for customers to fill"""
    service = HealthInsuranceFormService()
    link = service.get_form_link(token)
    
    if not link:
        return render_template('forms/error.html', 
                             message="Invalid or expired form link"), 404
    
    # Check if link is valid
    is_valid, message = link.is_valid()
    if not is_valid:
        return render_template('forms/error.html', message=message), 400
    
    if request.method == 'POST':
        form_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'mobile': request.form.get('mobile'),
            'city_of_residence': request.form.get('city_of_residence'),
            'age': int(request.form.get('age', 0)),
            'number_of_members': int(request.form.get('number_of_members', 1)),
            'eldest_member_age': int(request.form.get('eldest_member_age', 0)),
            'pre_existing_diseases': request.form.get('pre_existing_diseases'),
            'major_surgery': request.form.get('major_surgery'),
            'existing_insurance': request.form.get('existing_insurance'),
            'current_coverage': float(request.form.get('current_coverage', 0)),
            'port_policy': request.form.get('port_policy'),
            'language': link.language
        }
        
        form_id, error = service.submit_form(form_data, token)
        
        if form_id:
            return render_template('forms/health_insurance/success.html',
                                 form_id=form_id,
                                 agent_name=link.agent_name,
                                 agent_phone=link.agent_phone,
                                 language=link.language)
        else:
            flash(error, 'danger')
    
    # Cities list
    cities = [
        'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata',
        'Pune', 'Ahmedabad', 'Jaipur', 'Surat', 'Lucknow', 'Kanpur',
        'Nagpur', 'Indore', 'Bhopal', 'Visakhapatnam', 'Patna', 'Vadodara',
        'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik', 'Faridabad', 'Meerut',
        'Rajkot', 'Varanasi', 'Srinagar', 'Aurangabad', 'Dhanbad', 'Amritsar',
        'Others'
    ]
    
    return render_template(f'forms/health_insurance/form_{link.language}.html',
                         token=token,
                         cities=cities,
                         agent_name=link.agent_name,
                         agent_phone=link.agent_phone)

@health_insurance_bp.route('/<form_id>/view')
@login_required
def view_form(form_id):
    """View submitted form details"""
    if not current_user.is_agent():
        flash('Only agents can view form details.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    service = HealthInsuranceFormService()
    form_data = service.get_form_by_id(form_id)
    
    if not form_data:
        flash('Form not found.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    # Verify agent owns this form
    if form_data['agent_id'] != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    # Convert dict to object-like structure for template
    class FormObject:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
        
        @property
        def id(self):
            return str(self._id) if hasattr(self, '_id') else str(getattr(self, 'id', ''))
    
    form = FormObject(form_data)
    
    return render_template('forms/health_insurance/view.html', form=form)

@health_insurance_bp.route('/<form_id>/generate-pdf', methods=['POST'])
@login_required
def generate_pdf(form_id):
    """Generate PDF for form"""
    if not current_user.is_agent():
        return jsonify({'error': 'Only agents can generate PDFs'}), 403
    
    service = HealthInsuranceFormService()
    pdf_filename, error = service.generate_pdf(form_id, current_user.id)
    
    if pdf_filename:
        return jsonify({
            'success': True,
            'pdf_filename': pdf_filename,
            'download_url': url_for('health_insurance.download_pdf', 
                                  form_id=form_id, 
                                  filename=pdf_filename)
        })
    else:
        return jsonify({'success': False, 'error': error}), 400

@health_insurance_bp.route('/<form_id>/download/<filename>')
@login_required
def download_pdf(form_id, filename):
    """Download generated PDF"""
    if not current_user.is_agent():
        flash('Only agents can download PDFs.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    service = HealthInsuranceFormService()
    form_data = service.get_form_by_id(form_id)
    
    if not form_data or form_data['agent_id'] != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    if form_data.get('pdf_filename') != filename:
        flash('Invalid file.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    pdf_path = os.path.join('/root/generated_pdfs', filename)
    
    if not os.path.exists(pdf_path):
        flash('PDF file not found.', 'danger')
        return redirect(url_for('health_insurance.view_form', form_id=form_id))
    
    return send_file(pdf_path, as_attachment=True, download_name=filename)

# API endpoints for AJAX operations
@health_insurance_bp.route('/api/link/<link_id>/toggle-status', methods=['POST'])
@login_required
def toggle_link_status(link_id):
    """Toggle form link active status"""
    if not current_user.is_agent():
        return jsonify({'error': 'Unauthorized'}), 403
    
    service = HealthInsuranceFormService()
    success = service.toggle_link_status(link_id, current_user.id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to update status'}), 400