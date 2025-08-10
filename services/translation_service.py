# services/translation_service.py
# Google Translate service for multi-language support - FIXED for Flask context

from googletrans import Translator
import redis
import json
import logging
from flask import current_app

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        
        # Language mapping
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'mr': 'Marathi', 
            'gu': 'Gujarati',
            'te': 'Telugu',
            'bn': 'Bengali',
            'kn': 'Kannada',
            'ta': 'Tamil',
            'ml': 'Malayalam'
        }
    
    def _init_redis(self):
        """Initialize Redis connection with proper Flask context"""
        if self._initialized:
            return
            
        try:
            # Only initialize if we have an application context
            if current_app:
                redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self._initialized = True
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}. Translations will not be cached.")
            self.redis_client = None
    
    def _ensure_redis(self):
        """Ensure Redis is initialized before use"""
        if not self._initialized:
            self._init_redis()
        return self.redis_client is not None
    
    def get_cache_key(self, text, target_lang):
        """Generate cache key for translation"""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"translation:{text_hash}:{target_lang}"
    
    def get_cached_translation(self, text, target_lang):
        """Get translation from cache"""
        if not self._ensure_redis():
            return None
        
        try:
            cache_key = self.get_cache_key(text, target_lang)
            cached = self.redis_client.get(cache_key)
            if cached:
                return cached.decode('utf-8')
        except Exception as e:
            self.logger.error(f"Redis get error: {e}")
        
        return None
    
    def cache_translation(self, text, target_lang, translation):
        """Cache translation"""
        if not self._ensure_redis():
            return
        
        try:
            cache_key = self.get_cache_key(text, target_lang)
            # Cache for 24 hours
            self.redis_client.setex(cache_key, 86400, translation)
        except Exception as e:
            self.logger.error(f"Redis set error: {e}")
    
    def translate_text(self, text, target_lang='en', source_lang='auto'):
        """Translate text to target language"""
        if not text or target_lang == 'en':
            return text
        
        # Check cache first
        cached = self.get_cached_translation(text, target_lang)
        if cached:
            return cached
        
        try:
            result = self.translator.translate(text, dest=target_lang, src=source_lang)
            translation = result.text
            
            # Cache the translation
            self.cache_translation(text, target_lang, translation)
            
            return translation
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def translate_form_data(self, form_data, target_lang='en'):
        """Translate form field labels and options"""
        if target_lang == 'en':
            return form_data
        
        translated_data = {}
        
        for key, value in form_data.items():
            if isinstance(value, str):
                translated_data[key] = self.translate_text(value, target_lang)
            elif isinstance(value, list):
                translated_data[key] = [self.translate_text(item, target_lang) for item in value]
            elif isinstance(value, dict):
                translated_data[key] = self.translate_form_data(value, target_lang)
            else:
                translated_data[key] = value
        
        return translated_data
    
    def get_form_translations(self, target_lang='en'):
        """Get all form field translations"""
        base_form_data = {
            'title': 'Health Insurance Requirement Analysis',
            'subtitle': 'Please fill in your details',
            'mandatory_note': 'All fields marked with * are mandatory',
            'fields': {
                'name': 'Full Name',
                'email': 'Email Address',
                'mobile': 'Mobile Number',
                'mobile_hint': '10 digit mobile number',
                'city_of_residence': 'City of Residence',
                'age': 'Your Age',
                'number_of_members': 'Number of Family Members',
                'number_of_members_hint': 'Including yourself',
                'eldest_member_age': 'Age of Eldest Family Member',
                'pre_existing_diseases': 'Pre-existing Diseases?',
                'major_surgery': 'History of Major Surgery?',
                'existing_insurance': 'Do you have existing Health Insurance?',
                'current_coverage': 'Current Coverage Amount (₹)',
                'port_policy': 'Want to Port Existing Policy?',
                'submit_button': 'Submit Form',
                'privacy_title': 'Privacy Notice',
                'privacy_text': 'Your information will be used solely for generating your health insurance requirement analysis and will be shared only with your financial advisor.'
            },
            'options': {
                'select': 'Select',
                'select_city': 'Select City',
                'yes': 'Yes',
                'no': 'No'
            },
            'success': {
                'title': 'Thank You!',
                'message': 'Your health insurance requirement details have been submitted successfully.',
                'next_steps_title': 'What happens next?',
                'next_steps': [
                    'Your financial advisor will analyze your requirements',
                    'A personalized health insurance recommendation report will be prepared',
                    'You will be contacted with the best suitable options'
                ],
                'advisor_title': 'Your Financial Advisor'
            }
        }
        
        return self.translate_form_data(base_form_data, target_lang)
    
    def translate_pdf_content(self, content_data, target_lang='en'):
        """Translate PDF content"""
        if target_lang == 'en':
            return content_data
        
        return self.translate_form_data(content_data, target_lang)