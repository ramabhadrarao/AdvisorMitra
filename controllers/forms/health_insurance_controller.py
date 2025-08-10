# controllers/forms/health_insurance_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from services.forms.health_insurance_service import HealthInsuranceFormService
from services.translation_service import TranslationService
from services.live_progress_service import progress_service
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
    
    return render_template('forms/health_insurance/list.html', **result)

@health_insurance_bp.route('/live-progress')
@login_required
def live_progress():
    """Live progress tracking page for agents"""
    if not current_user.is_agent():
        flash('Only agents can access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    return render_template('forms/health_insurance/live_progress.html')

@health_insurance_bp.route('/api/active-forms')
@login_required
def api_active_forms():
    """Get active forms for current agent"""
    if not current_user.is_agent():
        return jsonify({'error': 'Unauthorized'}), 403
    
    active_forms = progress_service.get_agent_active_forms(current_user.id)
    return jsonify({'success': True, 'forms': active_forms})

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
        
        # Default to 1 usage for single customer, allow override
        if not usage_limit:
            usage_limit = 1
        else:
            usage_limit = int(usage_limit)
        
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
    """Public form for customers to fill - Dynamic translation"""
    service = HealthInsuranceFormService()
    link = service.get_form_link(token)
    
    if not link:
        return render_template('forms/error.html', 
                             message="Invalid or expired form link"), 404
    
    # Check if link is valid
    is_valid, message = link.is_valid()
    if not is_valid:
        return render_template('forms/error.html', message=message), 400
    
    # Initialize translation service
    translation_service = TranslationService()
    
    # Get form translations for the specified language
    form_translations = translation_service.get_form_translations(link.language)
    
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
            'port_policy': request.form.get('port_policy', 'No'),
            'language': link.language
        }
        
        form_id, error = service.submit_form(form_data, token)
        
        if form_id:
            # Mark form as completed in progress tracker
            progress_service.complete_form_session(token)
            
            return render_template('forms/health_insurance/success.html',
                                 form_id=form_id,
                                 agent_name=link.agent_name,
                                 agent_phone=link.agent_phone,
                                 translations=form_translations['success'])
        else:
            flash(error, 'danger')
    
    # Start form session for progress tracking
    progress_service.start_form_session(token, link.agent_id)
    
    # Cities list (will be translated)
    cities = [
        'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata',
        'Pune', 'Ahmedabad', 'Jaipur', 'Surat', 'Lucknow', 'Kanpur',
        'Nagpur', 'Indore', 'Bhopal', 'Visakhapatnam', 'Patna', 'Vadodara',
        'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik', 'Faridabad', 'Meerut',
        'Rajkot', 'Varanasi', 'Srinagar', 'Aurangabad', 'Dhanbad', 'Amritsar',
        'Others'
    ]
    
    # Translate cities if needed
    if link.language != 'en':
        translated_cities = []
        for city in cities:
            if city == 'Others':
                translated_cities.append(translation_service.translate_text('Others', link.language))
            else:
                translated_cities.append(city)  # Keep city names in original
        cities = translated_cities
    
    return render_template('forms/health_insurance/dynamic_form.html',
                         token=token,
                         cities=cities,
                         agent_name=link.agent_name,
                         agent_phone=link.agent_phone,
                         language=link.language,
                         translations=form_translations)

@health_insurance_bp.route('/api/translate', methods=['POST'])
def api_translate():
    """API endpoint for real-time translation"""
    data = request.get_json()
    text = data.get('text', '')
    target_lang = data.get('target_lang', 'en')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    translation_service = TranslationService()
    translated_text = translation_service.translate_text(text, target_lang)
    
    return jsonify({
        'success': True,
        'original_text': text,
        'translated_text': translated_text,
        'target_language': target_lang
    })

@health_insurance_bp.route('/api/form-progress/<token>')
def api_form_progress(token):
    """Get current form progress"""
    progress_data = progress_service.get_form_progress(token)
    return jsonify({
        'success': True,
        'progress': progress_data
    })

@health_insurance_bp.route('/<form_id>/view')
@login_required
def view_form(form_id):
    """View submitted form details"""
    if not current_user.is_agent():
        flash('Only agents can view form details.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    service = HealthInsuranceFormService()
    form = service.get_form_by_id(form_id)
    
    if not form:
        flash('Form not found.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    # Verify agent owns this form
    if str(form.agent_id) != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
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
    form = service.get_form_by_id(form_id)
    
    if not form or str(form.agent_id) != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    if form.pdf_filename != filename:
        flash('Invalid file.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    pdf_path = os.path.join(os.getcwd(), 'static', 'generated_pdfs', filename)
    
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