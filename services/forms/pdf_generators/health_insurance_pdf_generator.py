# services/forms/pdf_generators/health_insurance_pdf_generator.py
# FIXED - Proper multi-language font support without external dependencies

import os
import sys
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepInFrame
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from pymongo import MongoClient
from bson import ObjectId
from flask import current_app
import pytz
from services.translation_service import TranslationService
import logging

# Set up logging
logger = logging.getLogger(__name__)
# Get the absolute path to the root directory
def get_font_directory():
    """Get the absolute path to the font directory"""
    # Try different methods to find the font directory
    possible_paths = [
        # Absolute path from root
        "/root/notofonts.github.io/fonts/",
        # Relative to current working directory
        os.path.join(os.getcwd(), "notofonts.github.io/fonts/"),
        # Relative to the script location
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../notofonts.github.io/fonts/"),
        # Relative to app root (if running from app.py)
        os.path.join(os.path.dirname(sys.argv[0]), "notofonts.github.io/fonts/"),
        # Direct path if running from /root
        "/notofonts.github.io/fonts/",
        # Current directory
        "./notofonts.github.io/fonts/"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found font directory at: {path}")
            return path
    
    print(f"❌ Font directory not found. Tried paths: {possible_paths}")
    return None

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page numbers and decorative elements to all pages"""
        num_pages = len(self._saved_page_states)
        for (page_num, state) in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self.draw_page_decorations(page_num + 1, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_num, num_pages):
        """Draw page decorations and numbers"""
        width, height = A4
        
        # Draw decorative border
        self.setStrokeColor(colors.HexColor('#0D4F8C'))
        self.setLineWidth(2)
        self.rect(15*mm, 15*mm, width-30*mm, height-30*mm)
        
        # Inner border
        self.setStrokeColor(colors.HexColor('#FF8F00'))
        self.setLineWidth(0.5)
        self.rect(18*mm, 18*mm, width-36*mm, height-36*mm)
        
        # Page number
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor('#424242'))
        self.drawCentredText(width/2, 20*mm, f"Page {page_num} of {num_pages}")
        
        # Corner decorations
        self.setFillColor(colors.HexColor('#FF8F00'))
        corners = [(20*mm, height-20*mm), (width-20*mm, height-20*mm), 
                  (20*mm, 20*mm), (width-20*mm, 20*mm)]
        for x, y in corners:
            self.circle(x, y, 2*mm, fill=1, stroke=0)

class HealthInsurancePDFGenerator:
    def __init__(self):
        self.translation_service = TranslationService()
        self._register_fonts()
        
        # Professional color scheme
        self.colors = {
            'primary': colors.HexColor('#0D4F8C'),      # Navy Blue
            'secondary': colors.HexColor('#E3F2FD'),    # Light Blue
            'accent': colors.HexColor('#FF8F00'),       # Orange
            'success': colors.HexColor('#2E7D32'),      # Green
            'warning': colors.HexColor('#F57C00'),      # Orange
            'danger': colors.HexColor('#D32F2F'),       # Red
            'text_dark': colors.HexColor('#1A1A1A'),    # Almost Black
            'text_light': colors.HexColor('#424242'),   # Dark Gray
            'text_muted': colors.HexColor('#757575'),   # Light Gray
            'border': colors.HexColor('#90A4AE'),       # Blue Gray
            'bg_light': colors.HexColor('#FAFAFA'),     # Very Light Gray
            'white': colors.white
        }
    
    def _register_fonts(self):
        """Register fonts for multi-language support - FIXED VERSION with proper path resolution"""
        try:
            # Get the font directory dynamically
            font_dir = get_font_directory()
            
            if not font_dir:
                logger.error("Font directory not found!")
                return
            
            # List contents of font directory for debugging
            print(f"📁 Font directory contents:")
            try:
                for item in os.listdir(font_dir):
                    print(f"  - {item}")
            except Exception as e:
                print(f"  Error listing directory: {e}")
            
            # Define font mappings
            font_mappings = {
                'NotoSans': {
                    'regular': "NotoSans/full/ttf/NotoSans-Regular.ttf",
                    'bold': "NotoSans/full/ttf/NotoSans-Bold.ttf",
                    'italic': "NotoSans/full/ttf/NotoSans-Italic.ttf",
                    'boldItalic': "NotoSans/full/ttf/NotoSans-BoldItalic.ttf"
                },
                'NotoSansDevanagari': {
                    'regular': "NotoSansDevanagari/full/ttf/NotoSansDevanagari-Regular.ttf",
                    'bold': "NotoSansDevanagari/full/ttf/NotoSansDevanagari-Bold.ttf"
                },
                'NotoSansGujarati': {
                    'regular': "NotoSansGujarati/full/ttf/NotoSansGujarati-Regular.ttf",
                    'bold': "NotoSansGujarati/full/ttf/NotoSansGujarati-Bold.ttf"
                },
                'NotoSansBengali': {
                    'regular': "NotoSansBengali/full/ttf/NotoSansBengali-Regular.ttf",
                    'bold': "NotoSansBengali/full/ttf/NotoSansBengali-Bold.ttf"
                },
                'NotoSansTelugu': {
                    'regular': "NotoSansTelugu/full/ttf/NotoSansTelugu-Regular.ttf",
                    'bold': "NotoSansTelugu/full/ttf/NotoSansTelugu-Bold.ttf"
                },
                'NotoSansTamil': {
                    'regular': "NotoSansTamil/full/ttf/NotoSansTamil-Regular.ttf",
                    'bold': "NotoSansTamil/full/ttf/NotoSansTamil-Bold.ttf"
                },
                'NotoSansKannada': {
                    'regular': "NotoSansKannada/full/ttf/NotoSansKannada-Regular.ttf",
                    'bold': "NotoSansKannada/full/ttf/NotoSansKannada-Bold.ttf"
                },
                'NotoSansMalayalam': {
                    'regular': "NotoSansMalayalam/full/ttf/NotoSansMalayalam-Regular.ttf",
                    'bold': "NotoSansMalayalam/full/ttf/NotoSansMalayalam-Bold.ttf"
                },
                # Using Gurmukhi for Punjabi
                'NotoSansGurmukhi': {
                    'regular': "NotoSansGurmukhi/full/ttf/NotoSansGurmukhi-Regular.ttf",
                    'bold': "NotoSansGurmukhi/full/ttf/NotoSansGurmukhi-Bold.ttf"
                },
                # Using Oriya for Odia
                'NotoSansOriya': {
                    'regular': "NotoSansOriya/full/ttf/NotoSansOriya-Regular.ttf",
                    'bold': "NotoSansOriya/full/ttf/NotoSansOriya-Bold.ttf"
                }
            }
            
            # Track which fonts were successfully registered
            self.registered_fonts = {}
            
            # Try to register each font
            for font_family, font_files in font_mappings.items():
                family_registered = False
                
                for style, filename in font_files.items():
                    full_path = os.path.join(font_dir, filename)
                    
                    # Debug: Check if file exists
                    if os.path.exists(full_path):
                        try:
                            # Check file size
                            file_size = os.path.getsize(full_path)
                            print(f"📄 Found {filename} ({file_size} bytes)")
                            
                            if file_size > 0:
                                font_name = f"{font_family}-{style}"
                                pdfmetrics.registerFont(TTFont(font_name, full_path))
                                self.registered_fonts[font_name] = True
                                family_registered = True
                                logger.info(f"✅ Registered font: {font_name} from {full_path}")
                            else:
                                logger.warning(f"⚠️ Font file is empty: {full_path}")
                        except Exception as e:
                            logger.error(f"❌ Failed to register {font_name}: {e}")
                    else:
                        logger.warning(f"⚠️ Font file not found: {full_path}")
                
                # Register font family if at least regular was registered
                if family_registered and f"{font_family}-regular" in self.registered_fonts:
                    try:
                        registerFontFamily(
                            font_family,
                            normal=f"{font_family}-regular",
                            bold=f"{font_family}-bold" if f"{font_family}-bold" in self.registered_fonts else f"{font_family}-regular",
                            italic=f"{font_family}-italic" if f"{font_family}-italic" in self.registered_fonts else f"{font_family}-regular",
                            boldItalic=f"{font_family}-boldItalic" if f"{font_family}-boldItalic" in self.registered_fonts else f"{font_family}-regular"
                        )
                        logger.info(f"✅ Registered font family: {font_family}")
                    except Exception as e:
                        logger.warning(f"Failed to register font family {font_family}: {e}")
            
            # Print summary
            print(f"\n📊 Font Registration Summary:")
            print(f"   Total fonts registered: {len(self.registered_fonts)}")
            for font_name in sorted(self.registered_fonts.keys()):
                print(f"   ✅ {font_name}")
            
            if not self.registered_fonts:
                logger.error("❌ No fonts were registered! PDF generation may fail.")
                print("\n🔍 Debugging tips:")
                print("1. Check if font files exist in the directory")
                print("2. Verify font files are not empty (0 bytes)")
                print("3. Check file permissions (should be readable)")
                print(f"4. Current working directory: {os.getcwd()}")
                
        except Exception as e:
            logger.error(f"❌ Font registration error: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_font_for_language(self, language, style='regular'):
        """Get appropriate font for language - ENHANCED VERSION"""
        # Map languages to appropriate fonts
        font_map = {
            'hi': 'NotoSansDevanagari',  # Hindi
            'mr': 'NotoSansDevanagari',  # Marathi (uses Devanagari script)
            'gu': 'NotoSansGujarati',    # Gujarati
            'te': 'NotoSansTelugu',       # Telugu
            'bn': 'NotoSansBengali',      # Bengali
            'kn': 'NotoSansKannada',      # Kannada
            'ta': 'NotoSansTamil',        # Tamil
            'ml': 'NotoSansMalayalam',    # Malayalam
            'pa': 'NotoSansGurmukhi',     # Punjabi
            'or': 'NotoSansOriya',        # Odia
            'en': 'NotoSans'              # English
        }
        
        base_font = font_map.get(language, 'NotoSans')
        font_name = f"{base_font}-{style}"
        
        # Check if font is registered
        if font_name in self.registered_fonts:
            print(f"✅ Using registered font: {font_name} for language: {language}")
            return font_name
        elif f"{base_font}-regular" in self.registered_fonts:
            print(f"⚠️ Style '{style}' not found, using regular for: {base_font}")
            return f"{base_font}-regular"
        else:
            # Fallback to Helvetica (built-in font)
            print(f"⚠️ No registered font for {language}, using Helvetica fallback")
            if style == 'bold':
                return 'Helvetica-Bold'
            elif style == 'italic':
                return 'Helvetica-Oblique'
            elif style == 'boldItalic':
                return 'Helvetica-BoldOblique'
            else:
                return 'Helvetica'
    
    def _create_paragraph_style(self, name, language='en', **kwargs):
        """Create a paragraph style with appropriate font for language"""
        font_name = self._get_font_for_language(language)
        
        default_style = {
            'fontName': font_name,
            'fontSize': 10,
            'leading': 12,
            'textColor': self.colors['text_dark']
        }
        
        # Merge with provided kwargs
        default_style.update(kwargs)
        
        return ParagraphStyle(name, **default_style)
    
    def _safe_paragraph(self, text, style, language='en'):
        """Create a paragraph with safe text handling for different languages"""
        try:
            # Ensure text is string and handle None values
            if text is None:
                text = ""
            else:
                text = str(text)
            
            # For non-English languages, we might need to handle the text differently
            if language != 'en' and language in ['hi', 'mr', 'gu', 'te', 'bn', 'kn', 'ta', 'ml']:
                # For complex scripts, we might need to use a different approach
                # For now, we'll create a simple text paragraph
                return Paragraph(text, style)
            else:
                return Paragraph(text, style)
                
        except Exception as e:
            logger.error(f"Error creating paragraph: {e}")
            # Fallback to simple text
            return Paragraph(str(text), style)
    
    def _get_mongodb_connection(self):
        """Get MongoDB connection"""
        mongo_uri = current_app.config.get('MONGO_URI', 'mongodb://localhost:27017/advisormitra')
        client = MongoClient(mongo_uri)
        db_name = mongo_uri.split('/')[-1]
        return client[db_name]
    
    def _mask_email(self, email):
        """Masks an email address for privacy"""
        if not email or "@" not in str(email):
            return "N/A"
        username, domain = str(email).split('@')
        if len(username) > 4:
            return f"{username[:2]}****{username[-2:]}@{domain}"
        else:
            return f"{username[0]}****@{domain}"
    
    def _mask_mobile(self, mobile):
        """Masks mobile number for privacy"""
        mobile_str = str(mobile) if mobile else "N/A"
        if len(mobile_str) >= 4:
            return f"{mobile_str[:2]}****{mobile_str[-2:]}"
        return mobile_str
    
    def _format_currency(self, value):
        """Formats numeric value into Indian currency format"""
        try:
            if not value or value == 0:
                return "N/A"
            val = float(value)
            
            # Format summary
            if val >= 10000000:
                summary = f"₹{val / 10000000:.1f} Crores"
            elif val >= 100000:
                summary = f"₹{val / 100000:.1f} Lakhs"
            elif val >= 1000:
                summary = f"₹{val / 1000:.1f} Thousands"
            else:
                summary = f"₹{val:.0f}"
            
            # Format actual value with Indian numbering
            if val >= 1000:
                s = str(int(val))
                if len(s) > 3:
                    result = s[-3:]
                    s = s[:-3]
                    while len(s) > 2:
                        result = s[-2:] + ',' + result
                        s = s[:-2]
                    if s:
                        result = s + ',' + result
                    actual = f"₹{result}"
                else:
                    actual = f"₹{val:.0f}"
            else:
                actual = f"₹{val:.0f}"
            
            return f"{actual} ({summary})"
        except (ValueError, TypeError):
            return str(value)
    
    def _get_age_group(self, age):
        """Determine age group based on age"""
        if age <= 35:
            return "25-35"
        elif age <= 45:
            return "36-45"
        else:
            return "45+"
    
    def _fetch_form_data(self, form_id):
        """Fetch health insurance data from MongoDB"""
        try:
            db = self._get_mongodb_connection()
            form = db.health_insurance_forms.find_one({'_id': ObjectId(form_id)})
            
            if form:
                return {
                    'name': form.get('name'),
                    'email': form.get('email'),
                    'mobile': form.get('mobile'),
                    'city_of_residence': form.get('city_of_residence'),
                    'age': form.get('age'),
                    'number_of_members': form.get('number_of_members'),
                    'eldest_member_age': form.get('eldest_member_age'),
                    'pre_existing_diseases': form.get('pre_existing_diseases'),
                    'major_surgery': form.get('major_surgery'),
                    'existing_insurance': form.get('existing_insurance'),
                    'current_coverage': form.get('current_coverage', 0),
                    'port_policy': form.get('port_policy', 'No'),
                    'form_timestamp': form.get('created_at'),
                    'tier_city': form.get('tier_city', 'Others'),
                    'language': form.get('language', 'en'),
                    'report_language': form.get('report_language', 'en')
                }
            return None
        except Exception as e:
            logger.error(f"Database error: {e}")
            return None
    
    def _get_recommended_coverage(self, user_data):
        """Get recommended coverage from database"""
        try:
            db = self._get_mongodb_connection()
            
            age_group = self._get_age_group(user_data['eldest_member_age'])
            city_tier = user_data['tier_city']
            pre_existing = 'Yes' if user_data['pre_existing_diseases'] == 'Yes' else 'No'
            
            recommendation = db.insurance_recommendations.find_one({
                'age_group': age_group,
                'city_tier': city_tier,
                'pre_existing_condition': pre_existing
            })
            
            if recommendation:
                base_coverage = recommendation['recommendation_amount'] * 100000
                
                # Adjust for family size
                family_members = user_data.get('number_of_members', 1)
                if family_members > 4:
                    base_coverage *= 1.5
                elif family_members > 2:
                    base_coverage *= 1.25
                
                return round(base_coverage / 100000) * 100000
            
            return 1000000  # Default 10 lakhs
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            return 1000000
    
    def _get_translated_content(self, language):
        """Get translated content for PDF"""
        # Base content in English
        content = {
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
        }
        
        # Hindi translations
        if language == 'hi':
            content = {
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
            }
        
        # Marathi translations
        elif language == 'mr':
            content = {
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
        
        # For other languages, use translation service for dynamic translation
        elif language != 'en':
            try:
                # Only translate if translation service is available
                if hasattr(self, 'translation_service') and self.translation_service:
                    def translate_dict(d, target_lang):
                        translated = {}
                        for key, value in d.items():
                            if isinstance(value, str):
                                translated[key] = self.translation_service.translate_text(value, target_lang)
                            elif isinstance(value, dict):
                                translated[key] = translate_dict(value, target_lang)
                            else:
                                translated[key] = value
                        return translated
                    
                    content = translate_dict(content, language)
            except Exception as e:
                logger.warning(f"Translation failed for language {language}: {e}")
                # Return English content as fallback
        
        return content

    def _create_header(self, language='en'):
        """Create document header with proper font support"""
        translated_content = self._get_translated_content(language)
        
        # Create styles with language-specific fonts
        title_style = self._create_paragraph_style(
            'HeaderTitle',
            language=language,
            fontSize=16,
            fontName=self._get_font_for_language(language, 'bold'),
            textColor=self.colors['white'],
            alignment=TA_CENTER
        )
        
        subtitle_style = self._create_paragraph_style(
            'HeaderSubtitle',
            language=language,
            fontSize=11,
            fontName=self._get_font_for_language(language, 'bold'),
            textColor=self.colors['primary'],
            alignment=TA_CENTER
        )
        
        # Create paragraphs with safe text handling
        title_para = self._safe_paragraph(translated_content['title'], title_style, language)
        subtitle_para = self._safe_paragraph(translated_content['subtitle'], subtitle_style, language)
        
        header_data = [[title_para], [subtitle_para]]
        
        header_table = Table(header_data, colWidths=[16*cm])
        header_table.setStyle(TableStyle([
            # Title row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['white']),
            
            # Subtitle row styling
            ('BACKGROUND', (0, 1), (-1, 1), self.colors['secondary']),
            ('TEXTCOLOR', (0, 1), (-1, 1), self.colors['primary']),
            
            # General styling
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 2, self.colors['primary']),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.colors['border']),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        return header_table

    def _create_customer_details(self, user_data, language='en'):
        """Create customer details section with proper font support"""
        translated_content = self._get_translated_content(language)
        
        # Section header style
        section_header_style = self._create_paragraph_style(
            'SectionHeader',
            language=language,
            fontSize=13,
            fontName=self._get_font_for_language(language, 'bold'),
            textColor=self.colors['white'],
            alignment=TA_CENTER
        )
        
        # Create section header
        section_header_para = self._safe_paragraph(translated_content['customer_info'], section_header_style, language)
        section_header = Table([[section_header_para]], colWidths=[16*cm])
        section_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['primary']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, self.colors['primary']),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Get language names
        language_names = {
            'en': 'English',
            'hi': 'हिंदी (Hindi)',
            'mr': 'मराठी (Marathi)',
            'gu': 'ગુજરાતી (Gujarati)',
            'te': 'తెలుగు (Telugu)',
            'bn': 'বাংলা (Bengali)',
            'kn': 'ಕನ್ನಡ (Kannada)',
            'ta': 'தமிழ் (Tamil)',
            'ml': 'മലയാളം (Malayalam)'
        }
        
        # Create styles for table content
        field_style = self._create_paragraph_style(
            'FieldName',
            language=language,
            fontSize=10,
            fontName=self._get_font_for_language(language, 'bold')
        )
        
        value_style = self._create_paragraph_style(
            'FieldValue',
            language=language,
            fontSize=10,
            fontName=self._get_font_for_language(language)
        )
        
        # Helper function to translate Yes/No
        def translate_yes_no(value, lang):
            if value.lower() == 'yes':
                return translated_content.get('values', {}).get('yes', 'Yes')
            elif value.lower() == 'no':
                return translated_content.get('values', {}).get('no', 'No')
            return value
        
        # Details table with paragraphs
        details_data = [
            [Paragraph('FIELD', field_style), Paragraph('DETAILS', field_style)],
            [Paragraph(translated_content['fields']['full_name'], field_style), 
            Paragraph(user_data.get('name', 'N/A').title(), value_style)],
            [Paragraph(translated_content['fields']['email'], field_style), 
            Paragraph(self._mask_email(user_data.get('email', 'N/A')), value_style)],
            [Paragraph(translated_content['fields']['mobile'], field_style), 
            Paragraph(self._mask_mobile(user_data.get('mobile', 'N/A')), value_style)],
            [Paragraph(translated_content['fields']['age'], field_style), 
            Paragraph(f"{user_data.get('age', 'N/A')} {translated_content['values']['years']}", value_style)],
            [Paragraph(translated_content['fields']['city'], field_style), 
            Paragraph(f"{user_data.get('city_of_residence', 'N/A').title()} ({user_data.get('tier_city', 'N/A')})", value_style)],
            [Paragraph(translated_content['fields']['family_members'], field_style), 
            Paragraph(f"{user_data.get('number_of_members', 'N/A')} {translated_content['values']['members']}", value_style)],
            [Paragraph(translated_content['fields']['eldest_age'], field_style), 
            Paragraph(f"{user_data.get('eldest_member_age', 'N/A')} {translated_content['values']['years']}", value_style)],
            [Paragraph(translated_content['fields']['pre_existing'], field_style), 
            Paragraph(translate_yes_no(str(user_data.get('pre_existing_diseases', 'N/A')), language), value_style)],
            [Paragraph(translated_content['fields']['surgery'], field_style), 
            Paragraph(translate_yes_no(str(user_data.get('major_surgery', 'N/A')), language), value_style)],
            [Paragraph(translated_content['fields']['existing_insurance'], field_style), 
            Paragraph(translate_yes_no(str(user_data.get('existing_insurance', 'N/A')), language), value_style)],
            [Paragraph(translated_content['fields']['current_coverage'], field_style), 
            Paragraph(self._format_currency(user_data.get('current_coverage', 0)), value_style)],
            [Paragraph(translated_content['fields']['port_policy'], field_style), 
            Paragraph(translate_yes_no(str(user_data.get('port_policy', 'N/A')), language), value_style)],
            [Paragraph(translated_content['fields']['report_language'], field_style), 
            Paragraph(language_names.get(user_data.get('report_language', 'en'), 'English'), value_style)]
        ]
        
        details_table = Table(details_data, colWidths=[8*cm, 8*cm])
        details_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['text_dark']),
            
            # Field column
            ('BACKGROUND', (0, 1), (0, -1), self.colors['bg_light']),
            
            # Alternating rows for data column
            ('ROWBACKGROUNDS', (1, 1), (1, -1), [self.colors['white'], colors.HexColor('#F1F2F6')]),
            
            # General styling
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['border']),
            ('BOX', (0, 0), (-1, -1), 1, self.colors['primary']),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return [section_header, details_table]

    def _create_recommendation(self, user_data, recommended_coverage, language='en'):
        """Create recommendation section with proper text wrapping and font support"""
        translated_content = self._get_translated_content(language)
        
        # Section header style
        section_header_style = self._create_paragraph_style(
            'RecommendationHeader',
            language=language,
            fontSize=13,
            fontName=self._get_font_for_language(language, 'bold'),
            textColor=self.colors['white'],
            alignment=TA_CENTER
        )
        
        # Create section header
        section_header_para = self._safe_paragraph(translated_content['recommendation'], section_header_style, language)
        section_header = Table([[section_header_para]], colWidths=[16*cm])
        section_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['success']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, self.colors['success']),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Create custom styles for recommendations
        main_style = self._create_paragraph_style(
            'MainRecommendation',
            language=language,
            fontSize=13,
            fontName=self._get_font_for_language(language, 'bold'),
            textColor=self.colors['text_dark'],
            spaceAfter=12,
            leading=16
        )
        
        sub_style = self._create_paragraph_style(
            'SubRecommendation',
            language=language,
            fontSize=11,
            fontName=self._get_font_for_language(language),
            textColor=self.colors['text_muted'],
            spaceAfter=10,
            leading=14
        )
        
        recommendation_content = []
        
        # Main recommendation
        family_members = int(user_data.get('number_of_members', 1))
        protection_text = translated_content['recommendations']['you_and_family'] if family_members > 1 else translated_content['recommendations']['yourself']
        
        main_text = f"{translated_content['recommendations']['based_on']} {self._format_currency(recommended_coverage)} {translated_content['recommendations']['protection_for']} {protection_text}."
        recommendation_content.append(self._safe_paragraph(main_text, main_style, language))
        
        # Family size consideration
        if family_members > 1:
            family_text = f"{translated_content['recommendations']['family_size']}: {translated_content['recommendations']['family_adjustment']} {family_members} {translated_content['values']['members']}."
            recommendation_content.append(self._safe_paragraph(family_text, sub_style, language))
        
        # Coverage analysis
        if user_data.get('existing_insurance', 'No').lower() == 'yes':
            current_cov = user_data.get('current_coverage', 0)
            
            if current_cov and current_cov > 0:
                if current_cov >= recommended_coverage:
                    coverage_text = f"{translated_content['recommendations']['coverage_status']}: {translated_content['recommendations']['adequate_coverage']}"
                else:
                    gap = recommended_coverage - current_cov
                    coverage_text = f"{translated_content['recommendations']['coverage_gap']}: {translated_content['recommendations']['current_coverage']} {self._format_currency(current_cov)} {translated_content['recommendations']['shortfall']} {self._format_currency(gap)}. {translated_content['recommendations']['consider_increasing']}"
            else:
                coverage_text = f"{translated_content['recommendations']['coverage_enhancement']}: {translated_content['recommendations']['review_policy']}"
            
            recommendation_content.append(self._safe_paragraph(coverage_text, sub_style, language))
        
        # Create a frame to contain the recommendation content
        frame_width = 15*cm
        frame_height = 10*cm  # Adjust height as needed
        
        # Create a KeepInFrame to prevent overflow
        framed_content = KeepInFrame(
            maxWidth=frame_width,
            maxHeight=frame_height,
            content=recommendation_content,
            hAlign='LEFT'
        )
        
        # Create the recommendation box
        recommendation_data = [[framed_content]]
        recommendation_table = Table(recommendation_data, colWidths=[frame_width])
        
        recommendation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FFFE')),
            ('BOX', (0, 0), (-1, -1), 2, self.colors['success']),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return [section_header, recommendation_table]

    def _create_footer(self, agent_info, language='en'):
        """Create footer with agent details and proper font support"""
        translated_content = self._get_translated_content(language)
        
        # Get timestamp
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        generated_time = now_ist.strftime("%d-%b-%Y %I:%M %p")
        
        # Create styles
        header_style = self._create_paragraph_style(
            'FooterHeader',
            language=language,
            fontSize=10,
            fontName=self._get_font_for_language(language, 'bold'),
            textColor=self.colors['white'],
            alignment=TA_CENTER
        )
        
        data_style = self._create_paragraph_style(
            'FooterData',
            language=language,
            fontSize=9,
            fontName=self._get_font_for_language(language),
            textColor=self.colors['text_dark'],
            alignment=TA_CENTER
        )
        
        # Create footer data with paragraphs
        footer_data = [
            [self._safe_paragraph(translated_content['advisor'], header_style, language), 
             self._safe_paragraph(translated_content['report_generated'], header_style, language)],
            [Paragraph(f"{agent_info['name']}", data_style), 
             Paragraph(f"{generated_time}", data_style)],
            [Paragraph(f"+91 {agent_info['phone']}", data_style), 
             Paragraph("AdvisorMitra", data_style)],
            [self._safe_paragraph(translated_content['specialist'], data_style, language), 
             self._safe_paragraph(translated_content['confidential'], data_style, language)]
        ]
        
        footer_table = Table(footer_data, colWidths=[8*cm, 8*cm])
        footer_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['white']),
            
            # Data rows
            ('TEXTCOLOR', (0, 1), (-1, -1), self.colors['text_dark']),
            
            # Styling
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['border']),
            ('BOX', (0, 0), (-1, -1), 1, self.colors['primary']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return footer_table

    def generate_pdf_stream(self, form_id, agent_info, language='en'):
        """Generate PDF to memory stream with proper language support"""
        try:
            # Fetch data
            user_data = self._fetch_form_data(form_id)
            if not user_data:
                raise Exception("Form data not found")
            
            # Use the report language specified by customer
            pdf_language = user_data.get('report_language', language)
            
            recommended_coverage = self._get_recommended_coverage(user_data)
            
            # Create PDF in memory
            pdf_buffer = io.BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                rightMargin=25*mm,
                leftMargin=25*mm,
                topMargin=25*mm,
                bottomMargin=30*mm,
                canvasmaker=NumberedCanvas
            )
            
            # Build content
            elements = []
            
            # Add header
            elements.append(self._create_header(pdf_language))
            elements.append(Spacer(1, 8*mm))
            
            # Add customer details
            customer_sections = self._create_customer_details(user_data, pdf_language)
            elements.extend(customer_sections)
            elements.append(Spacer(1, 8*mm))
            
            # Add recommendation
            recommendation_sections = self._create_recommendation(user_data, recommended_coverage, pdf_language)
            elements.extend(recommendation_sections)
            elements.append(Spacer(1, 10*mm))
            
            # Add footer
            elements.append(self._create_footer(agent_info, pdf_language))
            
            # Build PDF
            doc.build(elements)
            
            # Get the value of the BytesIO buffer
            pdf_buffer.seek(0)
            
            return pdf_buffer
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise e