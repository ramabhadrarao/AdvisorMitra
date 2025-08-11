# controllers/forms/health_insurance_controller.py
# UPDATED - Added report language field and fixed usage limit functionality

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from services.forms.health_insurance_service import HealthInsuranceFormService
from services.translation_service import TranslationService
from services.live_progress_service import progress_service
from utils.decorators import login_required
import os
from datetime import timedelta, datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

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

# OPTIMIZATION 1: Cache translation service
_translation_service = None

def get_translation_service():
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service

# OPTIMIZATION 2: Cache cities list to avoid repeated processing
_cached_cities = None

def get_cities_list(language='en'):
    global _cached_cities
    if _cached_cities is None:
        _cached_cities = {
            'en': [
                'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata',
                'Pune', 'Ahmedabad', 'Jaipur', 'Surat', 'Lucknow', 'Kanpur',
                'Nagpur', 'Indore', 'Bhopal', 'Visakhapatnam', 'Patna', 'Vadodara',
                'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik', 'Faridabad', 'Meerut',
                'Rajkot', 'Varanasi', 'Srinagar', 'Aurangabad', 'Dhanbad', 'Amritsar',
                'Others'
            ]
        }
    
    # Return cached English list for non-English languages to avoid translation delays
    if language == 'en' or language not in SUPPORTED_LANGUAGES:
        return _cached_cities['en']
    
    # For other languages, return English list (city names typically don't need translation)
    return _cached_cities['en']

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
    """UPDATED: Public form for customers to fill - Dynamic translation with report language"""
    start_time = datetime.now()
    logger.info(f"🚀 Form request started for token: {token}")
    
    try:
        # OPTIMIZATION 3: Get service instance once
        service = HealthInsuranceFormService()
        
        # OPTIMIZATION 4: Fast link validation
        link = service.get_form_link(token)
        if not link:
            logger.warning(f"❌ Invalid token: {token}")
            return render_template('forms/error.html', 
                                 message="Invalid or expired form link"), 404
        
        # OPTIMIZATION 5: Quick validity check with usage limit
        is_valid, message = link.is_valid()
        if not is_valid:
            logger.warning(f"❌ Invalid link: {message}")
            return render_template('forms/error.html', message=message), 400
        
        # OPTIMIZATION 6: Handle form submission with minimal processing
        if request.method == 'POST':
            logger.info(f"📝 Processing form submission for token: {token}")
            
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
                'report_language': request.form.get('report_language', link.language),
                'language': link.language
            }
            
            form_id, error = service.submit_form(form_data, token)
            
            if form_id:
                # Mark form as completed in progress tracker
                progress_service.complete_form_session(token)
                
                # Get cached translation service
                translation_service = get_translation_service()
                form_translations = translation_service.get_form_translations(link.language)
                
                logger.info(f"✅ Form submitted successfully: {form_id}")
                return render_template('forms/health_insurance/success.html',
                                     form_id=form_id,
                                     agent_name=link.agent_name,
                                     agent_phone=link.agent_phone,
                                     translations=form_translations['success'])
            else:
                flash(error, 'danger')
        
        # OPTIMIZATION 7: Start progress tracking early (async-like)
        agent_id = str(link.agent_id) if hasattr(link, 'agent_id') and link.agent_id else None
        
        # Try multiple ways to get agent_id efficiently
        if not agent_id:
            try:
                from models.forms import get_form_links_collection
                form_links = get_form_links_collection()
                link_data = form_links.find_one({'token': token}, {'agent_id': 1})  # Only get agent_id field
                if link_data and link_data.get('agent_id'):
                    agent_id = str(link_data['agent_id'])
                    logger.info(f"🎯 Found agent_id from DB lookup: {agent_id}")
            except Exception as e:
                logger.error(f"❌ Error getting agent_id from DB: {e}")
        
        # Start progress tracking
        if agent_id:
            try:
                progress_service.start_form_session(token, agent_id)
                logger.info(f"✅ Started form session for token: {token} with agent_id: {agent_id}")
            except Exception as e:
                logger.error(f"❌ Error starting progress session: {e}")
        else:
            logger.warning(f"⚠️ No agent_id found for token: {token}")
        
        # OPTIMIZATION 8: Get cached cities without translation
        cities = get_cities_list(link.language)
        
        # OPTIMIZATION 9: Get translations efficiently (cache if possible)
        translation_service = get_translation_service()
        form_translations = translation_service.get_form_translations(link.language)
        
        # Add report language fields to translations
        if 'fields' not in form_translations:
            form_translations['fields'] = {}
        
        form_translations['fields']['report_language'] = translation_service.translate_text('Preferred Report Language', link.language)
        form_translations['fields']['report_language_hint'] = translation_service.translate_text('Your health insurance report will be generated in this language', link.language)
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"🏁 Form rendering completed in {elapsed_time:.3f}s for token: {token}")
        
        return render_template('forms/health_insurance/dynamic_form.html',
                             token=token,
                             cities=cities,
                             agent_name=link.agent_name,
                             agent_phone=link.agent_phone,
                             language=link.language,
                             translations=form_translations)
    
    except Exception as e:
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error processing form request after {elapsed_time:.3f}s: {e}")
        return render_template('forms/error.html', 
                             message="An error occurred while loading the form"), 500

@health_insurance_bp.route('/api/translate', methods=['POST'])
def api_translate():
    """OPTIMIZED: API endpoint for real-time translation"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_lang = data.get('target_lang', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Use cached translation service
        translation_service = get_translation_service()
        translated_text = translation_service.translate_text(text, target_lang)
        
        return jsonify({
            'success': True,
            'original_text': text,
            'translated_text': translated_text,
            'target_language': target_lang
        })
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({'error': 'Translation failed'}), 500

@health_insurance_bp.route('/api/form-progress/<token>')
def api_form_progress(token):
    """Get current form progress"""
    try:
        progress_data = progress_service.get_form_progress(token)
        return jsonify({
            'success': True,
            'progress': progress_data
        })
    except Exception as e:
        logger.error(f"Error getting form progress: {e}")
        return jsonify({'error': 'Failed to get progress'}), 500

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

@health_insurance_bp.route('/<form_id>/generate-pdf')
@login_required
def generate_pdf_direct(form_id):
    """Generate and download PDF directly (no server storage)"""
    if not current_user.is_agent():
        flash('Only agents can generate PDFs.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    service = HealthInsuranceFormService()
    
    # Get form data to check report language
    form = service.get_form_by_id(form_id)
    if not form:
        flash('Form not found.', 'danger')
        return redirect(url_for('health_insurance.index'))
    
    # Use the customer's preferred report language
    report_language = form.report_language if hasattr(form, 'report_language') else 'en'
    
    pdf_stream, error, filename = service.generate_pdf_stream(form_id, current_user.id, report_language)
    
    if pdf_stream:
        # Send the PDF directly to browser for download
        from flask import send_file
        return send_file(
            pdf_stream,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    else:
        flash(error, 'danger')
        return redirect(url_for('health_insurance.view_form', form_id=form_id))

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