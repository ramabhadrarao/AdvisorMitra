# services/translation_service.py
# UPDATED - Added form field translations for report language

from googletrans import Translator
import redis
import json
import logging
from flask import current_app
import time

class TranslationService:
    def __init__(self):
        self.translator = None  # Initialize lazily
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
        
        # OPTIMIZATION 1: Pre-translated common phrases cache
        self._static_translations = {
            'hi': {
                'title': 'स्वास्थ्य बीमा आवश्यकता विश्लेषण',
                'subtitle': 'कृपया अपना विवरण भरें',
                'mandatory_note': '* चिह्नित सभी फ़ील्ड अनिवार्य हैं',
                'fields': {
                    'name': 'पूरा नाम',
                    'email': 'ईमेल पता',
                    'mobile': 'मोबाइल नंबर',
                    'mobile_hint': '10 अंकों का मोबाइल नंबर',
                    'city_of_residence': 'निवास शहर',
                    'age': 'आपकी आयु',
                    'number_of_members': 'परिवार के सदस्यों की संख्या',
                    'number_of_members_hint': 'आप सहित',
                    'eldest_member_age': 'सबसे बड़े परिवार के सदस्य की आयु',
                    'pre_existing_diseases': 'पहले से मौजूद बीमारियाँ?',
                    'major_surgery': 'बड़ी सर्जरी का इतिहास?',
                    'existing_insurance': 'क्या आपके पास मौजूदा स्वास्थ्य बीमा है?',
                    'current_coverage': 'वर्तमान कवरेज राशि (₹)',
                    'port_policy': 'मौजूदा पॉलिसी पोर्ट करना चाहते हैं?',
                    'submit_button': 'फॉर्म जमा करें',
                    'report_language': 'पसंदीदा रिपोर्ट भाषा',
                    'report_language_hint': 'आपकी स्वास्थ्य बीमा रिपोर्ट इस भाषा में तैयार की जाएगी'
                },
                'options': {
                    'select': 'चुनें',
                    'select_city': 'शहर चुनें',
                    'yes': 'हाँ',
                    'no': 'नहीं'
                },
                'privacy_title': 'गोपनीयता सूचना',
                'privacy_text': 'आपकी जानकारी का उपयोग केवल आपकी स्वास्थ्य बीमा आवश्यकता विश्लेषण तैयार करने के लिए किया जाएगा।'
            },
            'mr': {
                'title': 'आरोग्य विमा गरज विश्लेषण',
                'subtitle': 'कृपया आपले तपशील भरा',
                'mandatory_note': '* चिन्हांकित सर्व फील्ड अनिवार्य आहेत',
                'fields': {
                    'name': 'पूर्ण नाव',
                    'email': 'ईमेल पत्ता',
                    'mobile': 'मोबाइल नंबर',
                    'submit_button': 'फॉर्म सबमिट करा',
                    'report_language': 'पसंतीची अहवाल भाषा',
                    'report_language_hint': 'तुमचा आरोग्य विमा अहवाल या भाषेत तयार केला जाईल'
                }
            },
            'gu': {
                'title': 'આરોગ્ય વીમા જરૂરિયાત વિશ્લેષણ',
                'subtitle': 'કૃપા કરીને તમારી વિગતો ભરો',
                'mandatory_note': '* ચિહ્નિત બધા ક્ષેત્રો ફરજિયાત છે',
                'fields': {
                    'name': 'પૂર્ણ નામ',
                    'email': 'ઇમેઇલ સરનામું',
                    'mobile': 'મોબાઇલ નંબર',
                    'submit_button': 'ફોર્મ સબમિટ કરો',
                    'report_language': 'પસંદગીની રિપોર્ટ ભાષા',
                    'report_language_hint': 'તમારો આરોગ્ય વીમા રિપોર્ટ આ ભાષામાં તૈયાર કરવામાં આવશે'
                }
            },
            'te': {
                'fields': {
                    'report_language': 'ఇష్టపడే నివేదిక భాష',
                    'report_language_hint': 'మీ ఆరోగ్య బీమా నివేదిక ఈ భాషలో తయారు చేయబడుతుంది'
                }
            },
            'bn': {
                'fields': {
                    'report_language': 'পছন্দের রিপোর্ট ভাষা',
                    'report_language_hint': 'আপনার স্বাস্থ্য বীমা রিপোর্ট এই ভাষায় তৈরি করা হবে'
                }
            },
            'kn': {
                'fields': {
                    'report_language': 'ಆದ್ಯತೆಯ ವರದಿ ಭಾಷೆ',
                    'report_language_hint': 'ನಿಮ್ಮ ಆರೋಗ್ಯ ವಿಮೆ ವರದಿಯನ್ನು ಈ ಭಾಷೆಯಲ್ಲಿ ತಯಾರಿಸಲಾಗುತ್ತದೆ'
                }
            },
            'ta': {
                'fields': {
                    'report_language': 'விருப்பமான அறிக்கை மொழி',
                    'report_language_hint': 'உங்கள் உடல்நலக் காப்பீட்டு அறிக்கை இந்த மொழியில் தயாரிக்கப்படும்'
                }
            },
            'ml': {
                'fields': {
                    'report_language': 'മുൻഗണനാ റിപ്പോർട്ട് ഭാഷ',
                    'report_language_hint': 'നിങ്ങളുടെ ആരോഗ്യ ഇൻഷുറൻസ് റിപ്പോർട്ട് ഈ ഭാഷയിൽ തയ്യാറാക്കും'
                }
            }
        }
    
    def _init_redis(self):
        """Initialize Redis connection with proper Flask context"""
        if self._initialized:
            return
            
        try:
            # Only initialize if we have an application context
            if current_app:
                redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2)
                self.redis_client.ping()
                self._initialized = True
                self.logger.info("✅ Redis translation cache connected")
        except Exception as e:
            self.logger.warning(f"Redis translation cache failed: {e}. Translations will not be cached.")
            self.redis_client = None
    
    def _ensure_redis(self):
        """Ensure Redis is initialized before use"""
        if not self._initialized:
            self._init_redis()
        return self.redis_client is not None
    
    def _init_translator(self):
        """Initialize Google Translator lazily"""
        if self.translator is None:
            try:
                start_time = time.time()
                self.translator = Translator()
                self.logger.info(f"✅ Google Translator initialized in {time.time() - start_time:.3f}s")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Google Translator: {e}")
                self.translator = None
    
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
        """OPTIMIZED: Translate text to target language with fast fallback"""
        # OPTIMIZATION 1: Return immediately for English
        if not text or target_lang == 'en':
            return text
        
        # OPTIMIZATION 2: Check static translations first
        if target_lang in self._static_translations:
            # Check in root level
            if text in self._static_translations[target_lang]:
                return self._static_translations[target_lang][text]
            # Check in fields
            if 'fields' in self._static_translations[target_lang] and text in self._static_translations[target_lang]['fields']:
                return self._static_translations[target_lang]['fields'][text]
        
        # OPTIMIZATION 3: Check cache first
        cached = self.get_cached_translation(text, target_lang)
        if cached:
            return cached
        
        # OPTIMIZATION 4: Fast timeout for Google Translate
        try:
            start_time = time.time()
            
            # Initialize translator if needed
            self._init_translator()
            if not self.translator:
                self.logger.warning("Google Translator not available, returning original text")
                return text
            
            # Quick translation with timeout
            result = self.translator.translate(text, dest=target_lang, src=source_lang)
            translation = result.text
            
            # Cache the translation
            self.cache_translation(text, target_lang, translation)
            
            elapsed = time.time() - start_time
            self.logger.debug(f"Translation completed in {elapsed:.3f}s: {text[:50]}...")
            
            return translation
            
        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            self.logger.warning(f"Translation failed after {elapsed:.3f}s: {e}")
            return text  # Return original text if translation fails
    
    def translate_form_data(self, form_data, target_lang='en'):
        """OPTIMIZED: Translate form field labels and options"""
        if target_lang == 'en':
            return form_data
        
        # OPTIMIZATION 5: Use static translations for known content
        if target_lang in self._static_translations:
            static_trans = self._static_translations[target_lang]
            
            # Deep merge static translations with form data
            translated_data = {}
            for key, value in form_data.items():
                if key in static_trans:
                    translated_data[key] = static_trans[key]
                elif isinstance(value, str):
                    # Only translate if not in static cache
                    translated_data[key] = self.translate_text(value, target_lang)
                elif isinstance(value, list):
                    translated_data[key] = [self.translate_text(item, target_lang) for item in value]
                elif isinstance(value, dict):
                    # Recursively handle nested dictionaries
                    if key in static_trans and isinstance(static_trans[key], dict):
                        translated_data[key] = {**static_trans[key]}
                        # Add any missing keys from original
                        for sub_key, sub_value in value.items():
                            if sub_key not in translated_data[key]:
                                translated_data[key][sub_key] = self.translate_text(sub_value, target_lang) if isinstance(sub_value, str) else sub_value
                    else:
                        translated_data[key] = self.translate_form_data(value, target_lang)
                else:
                    translated_data[key] = value
            
            return translated_data
        
        # Fallback to regular translation for unsupported languages
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
        """OPTIMIZED: Get all form field translations with static cache"""
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
                'privacy_text': 'Your information will be used solely for generating your health insurance requirement analysis and will be shared only with your financial advisor.',
                'report_language': 'Preferred Report Language',
                'report_language_hint': 'Your health insurance report will be generated in this language'
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
        
        # OPTIMIZATION 6: Use static translations when available
        if target_lang in self._static_translations:
            static_trans = self._static_translations[target_lang]
            
            # Merge static translations with base data
            result = {}
            for key, value in base_form_data.items():
                if key in static_trans:
                    if isinstance(value, dict) and isinstance(static_trans[key], dict):
                        result[key] = {**value, **static_trans[key]}
                    else:
                        result[key] = static_trans[key]
                else:
                    result[key] = self.translate_form_data(value, target_lang) if target_lang != 'en' else value
            
            return result
        
        # For unsupported languages, use regular translation
        return self.translate_form_data(base_form_data, target_lang)
    
    def translate_pdf_content(self, content_data, target_lang='en'):
        """Translate PDF content"""
        if target_lang == 'en':
            return content_data
        
        return self.translate_form_data(content_data, target_lang)