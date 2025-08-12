# services/translation_service.py
# SIMPLIFIED - Static translations only (no Argos dependency)

import redis
import json
import logging
from flask import current_app
import hashlib

class TranslationService:
    def __init__(self):
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
        self._redis_initialized = False
        
        # Comprehensive static translations for all supported languages
        self._static_translations = {
            'en': {
                'title': 'HEALTH INSURANCE REQUIREMENT ANALYSIS',
                'subtitle': 'Comprehensive Coverage Assessment Report',
                'customer_info': 'CUSTOMER INFORMATION',
                'recommendation': 'RECOMMENDED HEALTH INSURANCE COVERAGE',
                'advisor': 'YOUR FINANCIAL ADVISOR',
                'report_generated': 'REPORT GENERATED',
                'confidential': 'Confidential Document',
                'specialist': 'Financial Planning Specialist',
                'fields': {
                    'full_name': 'Full Name',
                    'email': 'Email Address',
                    'mobile': 'Mobile Number',
                    'age': 'Age',
                    'city': 'City of Residence',
                    'family_members': 'Family Members',
                    'eldest_age': 'Eldest Member Age',
                    'pre_existing': 'Pre-existing Diseases',
                    'surgery': 'Major Surgery History',
                    'existing_insurance': 'Existing Health Insurance',
                    'current_coverage': 'Current Coverage Amount',
                    'port_policy': 'Port Existing Policy',
                    'report_language': 'Report Language'
                },
                'values': {
                    'years': 'Years',
                    'members': 'Members',
                    'yes': 'Yes',
                    'no': 'No'
                },
                'recommendations': {
                    'based_on': 'Based on your comprehensive profile analysis, we recommend a Health Insurance coverage of',
                    'protection_for': 'to ensure adequate protection for',
                    'you_and_family': 'you and your family',
                    'yourself': 'yourself',
                    'family_size': 'Family Size Consideration',
                    'family_adjustment': 'This recommendation includes an adjustment for your family size of',
                    'coverage_status': 'Coverage Status',
                    'adequate_coverage': 'Your current coverage appears adequate for your current needs.',
                    'coverage_gap': 'Coverage Gap Alert',
                    'current_coverage': 'Your current coverage of',
                    'shortfall': 'has a shortfall of',
                    'consider_increasing': 'Consider increasing your coverage.',
                    'coverage_enhancement': 'Coverage Enhancement',
                    'review_policy': 'You mentioned having existing insurance but no coverage amount was specified. Please review your current policy details.'
                }
            },
            'te': {
                'title': 'ఆరోగ్య బీమా అవసరాల విశ్లేషణ',
                'subtitle': 'సమగ్ర కవరేజ్ అంచనా నివేదిక',
                'customer_info': 'కస్టమర్ సమాచారం',
                'recommendation': 'సిఫార్సు చేసిన ఆరోగ్య బీమా కవరేజ్',
                'advisor': 'మీ ఆర్థిక సలహాదారు',
                'report_generated': 'నివేదిక తయారు చేయబడింది',
                'confidential': 'గోప్య పత్రం',
                'specialist': 'ఆర్థిక ప్రణాళిక నిపుణుడు',
                'fields': {
                    'full_name': 'పూర్తి పేరు',
                    'email': 'ఇమెయిల్ చిరునామా',
                    'mobile': 'మొబైల్ నంబర్',
                    'age': 'వయస్సు',
                    'city': 'నివాస నగరం',
                    'family_members': 'కుటుంబ సభ్యులు',
                    'eldest_age': 'పెద్ద సభ్యుని వయస్సు',
                    'pre_existing': 'ముందే ఉన్న వ్యాధులు',
                    'surgery': 'పెద్ద శస్త్రచికిత్స చరిత్ర',
                    'existing_insurance': 'ప్రస్తుత ఆరోగ్య బీమా',
                    'current_coverage': 'ప్రస్తుత కవరేజ్ మొత్తం',
                    'port_policy': 'ప్రస్తుత పాలసీ పోర్ట్',
                    'report_language': 'నివేదిక భాష'
                },
                'values': {
                    'years': 'సంవత్సరాలు',
                    'members': 'సభ్యులు',
                    'yes': 'అవును',
                    'no': 'లేదు'
                },
                'recommendations': {
                    'based_on': 'మీ సమగ్ర ప్రొఫైల్ విశ్లేషణ ఆధారంగా, మేము సిఫార్సు చేస్తున్న ఆరోగ్య బీమా కవరేజ్',
                    'protection_for': 'తగిన రక్షణను నిర్ధారించడానికి',
                    'you_and_family': 'మీరు మరియు మీ కుటుంబం',
                    'yourself': 'మీరు',
                    'family_size': 'కుటుంబ పరిమాణం పరిగణన',
                    'family_adjustment': 'ఈ సిఫార్సులో మీ కుటుంబ పరిమాణానికి సర్దుబాటు చేర్చబడింది',
                    'coverage_status': 'కవరేజ్ స్థితి',
                    'adequate_coverage': 'మీ ప్రస్తుత కవరేజ్ మీ ప్రస్తుత అవసరాలకు తగినట్లు కనిపిస్తుంది.',
                    'coverage_gap': 'కవరేజ్ గ్యాప్ హెచ్చరిక',
                    'current_coverage': 'మీ ప్రస్తుత కవరేజ్',
                    'shortfall': 'యొక్క లోటు ఉంది',
                    'consider_increasing': 'మీ కవరేజ్‌ను పెంచుకోవడాన్ని పరిగణించండి.',
                    'coverage_enhancement': 'కవరేజ్ మెరుగుదల',
                    'review_policy': 'మీరు ప్రస్తుత బీమా ఉన్నట్లు పేర్కొన్నారు కానీ కవరేజ్ మొత్తం పేర్కొనబడలేదు. దయచేసి మీ ప్రస్తుత పాలసీ వివరాలను సమీక్షించండి.'
                }
            },
            'hi': {
                'title': 'स्वास्थ्य बीमा आवश्यकता विश्लेषण',
                'subtitle': 'व्यापक कवरेज मूल्यांकन रिपोर्ट',
                'customer_info': 'ग्राहक जानकारी',
                'recommendation': 'अनुशंसित स्वास्थ्य बीमा कवरेज',
                'advisor': 'आपके वित्तीय सलाहकार',
                'report_generated': 'रिपोर्ट तैयार की गई',
                'confidential': 'गोपनीय दस्तावेज़',
                'specialist': 'वित्तीय योजना विशेषज्ञ',
                'fields': {
                    'full_name': 'पूरा नाम',
                    'email': 'ईमेल पता',
                    'mobile': 'मोबाइल नंबर',
                    'age': 'आयु',
                    'city': 'निवास शहर',
                    'family_members': 'परिवार के सदस्य',
                    'eldest_age': 'सबसे बड़े सदस्य की आयु',
                    'pre_existing': 'पहले से मौजूद बीमारियाँ',
                    'surgery': 'बड़ी सर्जरी का इतिहास',
                    'existing_insurance': 'मौजूदा स्वास्थ्य बीमा',
                    'current_coverage': 'वर्तमान कवरेज राशि',
                    'port_policy': 'मौजूदा पॉलिसी पोर्ट करें',
                    'report_language': 'रिपोर्ट भाषा'
                },
                'values': {
                    'years': 'वर्ष',
                    'members': 'सदस्य',
                    'yes': 'हाँ',
                    'no': 'नहीं'
                },
                'recommendations': {
                    'based_on': 'आपकी व्यापक प्रोफ़ाइल विश्लेषण के आधार पर, हम',
                    'protection_for': 'की स्वास्थ्य बीमा कवरेज की सिफारिश करते हैं ताकि',
                    'you_and_family': 'आप और आपके परिवार',
                    'yourself': 'आप',
                    'family_size': 'परिवार के आकार पर विचार',
                    'family_adjustment': 'इस सिफारिश में आपके परिवार के आकार के लिए समायोजन शामिल है',
                    'coverage_status': 'कवरेज स्थिति',
                    'adequate_coverage': 'आपका वर्तमान कवरेज आपकी वर्तमान आवश्यकताओं के लिए पर्याप्त प्रतीत होता है।',
                    'coverage_gap': 'कवरेज अंतर चेतावनी',
                    'current_coverage': 'आपका वर्तमान कवरेज',
                    'shortfall': 'की कमी है',
                    'consider_increasing': 'अपना कवरेज बढ़ाने पर विचार करें।',
                    'coverage_enhancement': 'कवरेज संवर्धन',
                    'review_policy': 'आपने मौजूदा बीमा होने का उल्लेख किया है लेकिन कोई कवरेज राशि निर्दिष्ट नहीं की गई है। कृपया अपनी वर्तमान पॉलिसी विवरण की समीक्षा करें।'
                }
            },
            'mr': {
                'title': 'आरोग्य विमा गरज विश्लेषण',
                'subtitle': 'सर्वसमावेशक कवरेज मूल्यांकन अहवाल',
                'customer_info': 'ग्राहक माहिती',
                'recommendation': 'शिफारस केलेले आरोग्य विमा कवरेज',
                'advisor': 'तुमचे आर्थिक सल्लागार',
                'report_generated': 'अहवाल तयार केला',
                'confidential': 'गोपनीय दस्तऐवज',
                'specialist': 'आर्थिक नियोजन तज्ञ',
                'fields': {
                    'full_name': 'पूर्ण नाव',
                    'email': 'ईमेल पत्ता',
                    'mobile': 'मोबाइल नंबर',
                    'age': 'वय',
                    'city': 'निवासाचे शहर',
                    'family_members': 'कुटुंबातील सदस्य',
                    'eldest_age': 'सर्वात वयस्क सदस्याचे वय',
                    'pre_existing': 'पूर्वीपासून असलेले आजार',
                    'surgery': 'मोठ्या शस्त्रक्रियेचा इतिहास',
                    'existing_insurance': 'सध्याचा आरोग्य विमा',
                    'current_coverage': 'सध्याची कवरेज रक्कम',
                    'port_policy': 'सध्याची पॉलिसी पोर्ट करा',
                    'report_language': 'अहवाल भाषा'
                },
                'values': {
                    'years': 'वर्षे',
                    'members': 'सदस्य',
                    'yes': 'होय',
                    'no': 'नाही'
                },
                'recommendations': {
                    'based_on': 'तुमच्या सर्वसमावेशक प्रोफाइल विश्लेषणाच्या आधारे, आम्ही',
                    'protection_for': 'च्या आरोग्य विमा कवरेजची शिफारस करतो जेणेकरून',
                    'you_and_family': 'तुम्ही आणि तुमचे कुटुंब',
                    'yourself': 'तुम्ही',
                    'family_size': 'कुटुंबाच्या आकाराचा विचार',
                    'family_adjustment': 'या शिफारसीमध्ये तुमच्या कुटुंबाच्या आकारासाठी समायोजन समाविष्ट आहे',
                    'coverage_status': 'कवरेज स्थिती',
                    'adequate_coverage': 'तुमचे सध्याचे कवरेज तुमच्या सध्याच्या गरजांसाठी पुरेसे वाटते.',
                    'coverage_gap': 'कवरेज अंतर सूचना',
                    'current_coverage': 'तुमचे सध्याचे कवरेज',
                    'shortfall': 'ची कमतरता आहे',
                    'consider_increasing': 'तुमचे कवरेज वाढवण्याचा विचार करा.',
                    'coverage_enhancement': 'कवरेज सुधारणा',
                    'review_policy': 'तुम्ही सध्याचा विमा असल्याचे नमूद केले आहे पण कवरेज रक्कम निर्दिष्ट केली नाही. कृपया तुमच्या सध्याच्या पॉलिसीचे तपशील तपासा.'
                }
            }
        }
        
        # Form-specific translations
        self._form_translations = {
            'en': {
                'title': 'Health Insurance Requirement Analysis',
                'subtitle': 'Please fill in your details',
                'mandatory_note': 'All fields marked with * are mandatory',
                'advisor_title': 'Your Financial Advisor',
                'privacy_title': 'Privacy Notice',
                'privacy_text': 'Your information will be used solely for generating your health insurance requirement analysis and will be shared only with your financial advisor.',
                'fields': {
                    'name': 'Full Name',
                    'email': 'Email Address',
                    'mobile': 'Mobile Number',
                    'mobile_hint': '10 digit mobile number',
                    'age': 'Your Age',
                    'city_of_residence': 'City of Residence',
                    'number_of_members': 'Number of Family Members',
                    'number_of_members_hint': 'Including yourself',
                    'eldest_member_age': 'Age of Eldest Family Member',
                    'pre_existing_diseases': 'Pre-existing Diseases?',
                    'major_surgery': 'History of Major Surgery?',
                    'existing_insurance': 'Do you have existing Health Insurance?',
                    'current_coverage': 'Current Coverage Amount (₹)',
                    'port_policy': 'Want to Port Existing Policy?',
                    'submit_button': 'Submit Form',
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
                    'advisor_title': 'Your Financial Advisor',
                    'contact': 'Contact',
                    'reference_id': 'Reference ID'
                }
            },
            'te': {
                'title': 'ఆరోగ్య బీమా అవసరాల విశ్లేషణ',
                'subtitle': 'దయచేసి మీ వివరాలను నమోదు చేయండి',
                'mandatory_note': '* గుర్తు ఉన్న అన్ని ఫీల్డ్‌లు తప్పనిసరి',
                'advisor_title': 'మీ ఆర్థిక సలహాదారు',
                'privacy_title': 'గోప్యతా నోటీసు',
                'privacy_text': 'మీ సమాచారం కేవలం మీ ఆరోగ్య బీమా అవసరాల విశ్లేషణను రూపొందించడానికి మాత్రమే ఉపయోగించబడుతుంది మరియు మీ ఆర్థిక సలహాదారుతో మాత్రమే పంచుకోబడుతుంది.',
                'fields': {
                    'name': 'పూర్తి పేరు',
                    'email': 'ఇమెయిల్ చిరునామా',
                    'mobile': 'మొబైల్ నంబర్',
                    'mobile_hint': '10 అంకెల మొబైల్ నంబర్',
                    'age': 'మీ వయస్సు',
                    'city_of_residence': 'నివాస నగరం',
                    'number_of_members': 'కుటుంబ సభ్యుల సంఖ్య',
                    'number_of_members_hint': 'మీతో సహా',
                    'eldest_member_age': 'పెద్ద కుటుంబ సభ్యుని వయస్సు',
                    'pre_existing_diseases': 'ముందే ఉన్న వ్యాధులు?',
                    'major_surgery': 'పెద్ద శస్త్రచికిత్స చరిత్ర?',
                    'existing_insurance': 'మీకు ప్రస్తుత ఆరోగ్య బీమా ఉందా?',
                    'current_coverage': 'ప్రస్తుత కవరేజ్ మొత్తం (₹)',
                    'port_policy': 'ప్రస్తుత పాలసీని పోర్ట్ చేయాలనుకుంటున్నారా?',
                    'submit_button': 'ఫారమ్ సమర్పించండి',
                    'report_language': 'నివేదిక భాష ప్రాధాన్యత',
                    'report_language_hint': 'మీ ఆరోగ్య బీమా నివేదిక ఈ భాషలో రూపొందించబడుతుంది'
                },
                'options': {
                    'select': 'ఎంచుకోండి',
                    'select_city': 'నగరాన్ని ఎంచుకోండి',
                    'yes': 'అవును',
                    'no': 'లేదు'
                },
                'success': {
                    'title': 'ధన్యవాదాలు!',
                    'message': 'మీ ఆరోగ్య బీమా అవసరాల వివరాలు విజయవంతంగా సమర్పించబడ్డాయి.',
                    'next_steps_title': 'తరువాత ఏమి జరుగుతుంది?',
                    'next_steps': [
                        'మీ ఆర్థిక సలహాదారు మీ అవసరాలను విశ్లేషిస్తారు',
                        'వ్యక్తిగతీకరించిన ఆరోగ్య బీమా సిఫార్సు నివేదిక తయారు చేయబడుతుంది',
                        'అనుకూల ఉత్తమ ఎంపికలతో మిమ్మల్ని సంప్రదిస్తారు'
                    ],
                    'advisor_title': 'మీ ఆర్థిక సలహాదారు',
                    'contact': 'సంప్రదించండి',
                    'reference_id': 'సూచన ID'
                }
            }
        }
    
    def _init_redis(self):
        """Initialize Redis connection for caching"""
        if self._redis_initialized:
            return
            
        try:
            if current_app:
                redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                self._redis_initialized = True
                self.logger.info("✅ Redis connected for translation caching")
        except Exception as e:
            self.logger.warning(f"Redis not available for caching: {e}")
            self.redis_client = None
            self._redis_initialized = False
    
    def get_cached_translation(self, text, target_lang='en', source_lang='auto'):
        """Get cached translation from Redis"""
        if not self._redis_initialized:
            self._init_redis()
        
        if not self.redis_client:
            return None
            
        try:
            # Create a simple hash for the text
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            cache_key = f"translation:{source_lang}:{target_lang}:{text_hash}"
            cached_value = self.redis_client.get(cache_key)
            
            if cached_value:
                self.logger.debug(f"✅ Cache hit for translation: {text[:50]}...")
                return cached_value
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Cache lookup failed: {e}")
            return None
    
    def cache_translation(self, text, target_lang, translated_text, source_lang='auto'):
        """Cache translation in Redis"""
        if not self.redis_client:
            return
            
        try:
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            cache_key = f"translation:{source_lang}:{target_lang}:{text_hash}"
            # Cache for 24 hours
            self.redis_client.setex(cache_key, 86400, translated_text)
            self.logger.debug(f"✅ Cached translation for: {text[:50]}...")
            
        except Exception as e:
            self.logger.warning(f"Failed to cache translation: {e}")
    
    def translate_text(self, text, target_lang='en', source_lang='auto'):
        """Translate text using static translations"""
        # Return immediately for English or empty text
        if not text or target_lang == 'en':
            return text
        
        # Check cache first
        cached = self.get_cached_translation(text, target_lang, source_lang)
        if cached:
            return cached
        
        # Check static PDF translations
        if target_lang in self._static_translations:
            translations = self._static_translations[target_lang]
            
            # Direct match
            if text in translations:
                self.cache_translation(text, target_lang, translations[text])
                return translations[text]
            
            # Check in nested dictionaries
            for category in ['fields', 'values', 'recommendations']:
                if category in translations and text in translations[category]:
                    result = translations[category][text]
                    self.cache_translation(text, target_lang, result)
                    return result
        
        # Check form translations
        if target_lang in self._form_translations:
            form_trans = self._form_translations[target_lang]
            
            # Direct match
            if text in form_trans:
                self.cache_translation(text, target_lang, form_trans[text])
                return form_trans[text]
            
            # Check in nested dictionaries
            for category in ['fields', 'options', 'success']:
                if category in form_trans and text in form_trans[category]:
                    result = form_trans[category][text]
                    self.cache_translation(text, target_lang, result)
                    return result
        
        # Return original text if no translation found
        self.logger.debug(f"No translation available for '{text[:50]}...' in {target_lang}")
        return text
    
    def get_form_translations(self, target_lang='en'):
        """Get all form field translations"""
        return self._form_translations.get(target_lang, self._form_translations['en'])
    
    def _get_translated_content(self, language):
        """Get translated content for PDF generation"""
        return self._static_translations.get(language, self._static_translations['en'])