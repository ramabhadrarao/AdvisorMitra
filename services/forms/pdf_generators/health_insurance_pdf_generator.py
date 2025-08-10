# services/forms/pdf_generators/health_insurance_pdf_generator.py
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from pymongo import MongoClient
from bson import ObjectId
from flask import current_app
import pytz
from services.translation_service import TranslationService

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
        self.output_folder = os.path.join(os.getcwd(), 'static', 'generated_pdfs')
        self._ensure_output_folder()
        self.translation_service = TranslationService()
        
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
    
    def _ensure_output_folder(self):
        """Ensure output folder exists"""
        os.makedirs(self.output_folder, exist_ok=True)
    
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
                    'language': form.get('language', 'en')
                }
            return None
        except Exception as e:
            print(f"Database error: {e}")
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
            print(f"Database error: {e}")
            return 1000000
    
    def _get_translated_content(self, language):
        """Get translated content for PDF"""
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
                'port_policy': 'Port Existing Policy'
            },
            'values': {
                'years': 'Years',
                'members': 'Members'
            }
        }
        
        if language != 'en':
            # Translate all content
            for key, value in content.items():
                if isinstance(value, str):
                    content[key] = self.translation_service.translate_text(value, language)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        content[key][sub_key] = self.translation_service.translate_text(sub_value, language)
        
        return content

    def _create_header(self, language='en'):
        """Create document header with translation"""
        translated_content = self._get_translated_content(language)
        
        header_data = [
            [translated_content['title']],
            [translated_content['subtitle']]
        ]
        
        header_table = Table(header_data, colWidths=[16*cm])
        header_table.setStyle(TableStyle([
            # Title row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['white']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 16),
            
            # Subtitle row styling
            ('BACKGROUND', (0, 1), (-1, 1), self.colors['secondary']),
            ('TEXTCOLOR', (0, 1), (-1, 1), self.colors['primary']),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            
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
        """Create customer details section with translation"""
        translated_content = self._get_translated_content(language)
        
        # Section header
        section_header = Table([[translated_content['customer_info']]], colWidths=[16*cm])
        section_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.colors['white']),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 13),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, self.colors['primary']),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Details table
        details_data = [
            ['FIELD', 'DETAILS'],
            [translated_content['fields']['full_name'], user_data.get('name', 'N/A').title()],
            [translated_content['fields']['email'], self._mask_email(user_data.get('email', 'N/A'))],
            [translated_content['fields']['mobile'], self._mask_mobile(user_data.get('mobile', 'N/A'))],
            [translated_content['fields']['age'], f"{user_data.get('age', 'N/A')} {translated_content['values']['years']}"],
            [translated_content['fields']['city'], f"{user_data.get('city_of_residence', 'N/A').title()} ({user_data.get('tier_city', 'N/A')})"],
            [translated_content['fields']['family_members'], f"{user_data.get('number_of_members', 'N/A')} {translated_content['values']['members']}"],
            [translated_content['fields']['eldest_age'], f"{user_data.get('eldest_member_age', 'N/A')} {translated_content['values']['years']}"],
            [translated_content['fields']['pre_existing'], user_data.get('pre_existing_diseases', 'N/A').title()],
            [translated_content['fields']['surgery'], user_data.get('major_surgery', 'N/A').title()],
            [translated_content['fields']['existing_insurance'], user_data.get('existing_insurance', 'N/A').title()],
            [translated_content['fields']['current_coverage'], self._format_currency(user_data.get('current_coverage', 0))],
            [translated_content['fields']['port_policy'], user_data.get('port_policy', 'N/A').title()]
        ]
        
        details_table = Table(details_data, colWidths=[8*cm, 8*cm])
        details_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['text_dark']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            
            # Field column
            ('BACKGROUND', (0, 1), (0, -1), self.colors['bg_light']),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.colors['text_dark']),
            
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
        """Create recommendation section with translation"""
        translated_content = self._get_translated_content(language)
        
        # Section header
        section_header = Table([[translated_content['recommendation']]], colWidths=[16*cm])
        section_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['success']),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.colors['white']),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 13),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, self.colors['success']),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Build recommendation content
        family_members = int(user_data.get('number_of_members', 1))
        protection_text = self.translation_service.translate_text("you and your family" if family_members > 1 else "yourself", language)
        
        recommendation_content = []
        
        # Main recommendation
        main_text = self.translation_service.translate_text(
            f"Based on your comprehensive profile analysis, we recommend a Health Insurance coverage of {self._format_currency(recommended_coverage)} to ensure adequate protection for {protection_text}.",
            language
        )
        recommendation_content.append([main_text])
        
        # Family size consideration
        if family_members > 1:
            family_text = self.translation_service.translate_text(
                f"Family Size Consideration: This recommendation includes an adjustment for your family size of {family_members} members.",
                language
            )
            recommendation_content.append([family_text])
        
        # Coverage analysis
        if user_data.get('existing_insurance', 'No').lower() == 'yes':
            current_cov = user_data.get('current_coverage', 0)
            
            if current_cov and current_cov > 0:
                if current_cov >= recommended_coverage:
                    coverage_text = self.translation_service.translate_text(
                        f"Coverage Status: Your current coverage of {self._format_currency(current_cov)} appears adequate for your current needs.",
                        language
                    )
                else:
                    gap = recommended_coverage - current_cov
                    coverage_text = self.translation_service.translate_text(
                        f"Coverage Gap Alert: Your current coverage of {self._format_currency(current_cov)} has a shortfall of {self._format_currency(gap)}. Consider increasing your coverage.",
                        language
                    )
            else:
                coverage_text = self.translation_service.translate_text(
                    "Coverage Enhancement: You mentioned having existing insurance but no coverage amount was specified. Please review your current policy details.",
                    language
                )
            
            recommendation_content.append([coverage_text])
        
        # Create recommendation table
        recommendation_table = Table(recommendation_content, colWidths=[15*cm])
        
        # Build table style
        table_style = [
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FFFE')),
            ('BOX', (0, 0), (-1, -1), 2, self.colors['success']),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]
        
        # Style each row
        for i in range(len(recommendation_content)):
            if i == 0:  # Main recommendation - bold and larger
                table_style.extend([
                    ('FONTNAME', (0, i), (0, i), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, i), (0, i), 13),
                    ('TEXTCOLOR', (0, i), (0, i), self.colors['text_dark']),
                ])
            else:  # Other rows
                table_style.extend([
                    ('FONTSIZE', (0, i), (0, i), 11),
                    ('TEXTCOLOR', (0, i), (0, i), self.colors['text_muted']),
                ])
        
        recommendation_table.setStyle(TableStyle(table_style))
        
        return [section_header, recommendation_table]

    def _create_footer(self, agent_info, language='en'):
        """Create footer with agent details and translation"""
        translated_content = self._get_translated_content(language)
        
        # Get timestamp
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        generated_time = now_ist.strftime("%d-%b-%Y %I:%M %p")
        
        footer_data = [
            [translated_content['advisor'], translated_content['report_generated']],
            [f"{agent_info['name']}", f"{generated_time}"],
            [f"+91 {agent_info['phone']}", "AdvisorMitra"],
            [translated_content['specialist'], translated_content['confidential']]
        ]
        
        footer_table = Table(footer_data, colWidths=[8*cm, 8*cm])
        footer_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['white']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
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

    def generate_pdf(self, form_id, agent_info, language='en'):
        """Generate PDF with multi-language support"""
        try:
            # Fetch data
            user_data = self._fetch_form_data(form_id)
            if not user_data:
                raise Exception("Form data not found")
            
            # Use the language from user data if available
            pdf_language = user_data.get('language', language)
            
            recommended_coverage = self._get_recommended_coverage(user_data)
            
            # Generate filename
            pdf_filename = f"{user_data['name'].replace(' ', '_')}_Health_Insurance_Analysis_{pdf_language}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(self.output_folder, pdf_filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                pdf_path,
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
            
            return pdf_filename
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            raise e