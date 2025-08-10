# services/forms/pdf_generators/health_insurance_pdf_generator.py
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from pymongo import MongoClient
from bson import ObjectId
from flask import current_app
import pytz

class HealthInsurancePDFGenerator:
    def __init__(self):
        self.output_folder = os.path.join(os.getcwd(), 'static', 'generated_pdfs')
        self._ensure_output_folder()
    
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
        """Masks an email address for privacy."""
        if not email or "@" not in str(email):
            return "N/A"
        username, domain = str(email).split('@')
        return f"{username[:2]}****{username[-2:]}@{domain}" if len(username) > 4 else f"{username[0]}****@{domain}"
    
    def _format_currency(self, value):
        """Formats a numeric value into Indian currency format."""
        try:
            if not value or value == 0:
                return "N/A"
            val = float(value)
            
            # Format in Indian style
            if val >= 10000000:
                summary = f"₹{val / 10000000:.1f} Crores"
            elif val >= 100000:
                summary = f"₹{val / 100000:.1f} Lakhs"
            elif val >= 1000:
                summary = f"₹{val / 1000:.1f} Thousands"
            else:
                summary = f"₹{val:.0f}"
            
            # Format the actual value with Indian numbering
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
        """Determine age group based on age."""
        if age <= 35:
            return "25-35"
        elif age <= 45:
            return "36-45"
        else:
            return "45+"
    
    def _fetch_form_data(self, form_id):
        """Fetch health insurance data for a given form ID from MongoDB."""
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
                    'tier_city': form.get('tier_city', 'Others')
                }
            return None
        except Exception as e:
            print(f"Database error: {e}")
            return None
    
    def _get_recommended_coverage(self, user_data):
        """Get recommended coverage from insurance_recommendations collection."""
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
            
            return 1000000  # 10 lakhs default
            
        except Exception as e:
            print(f"Database error: {e}")
            return 1000000
    
    def generate_pdf(self, form_id, agent_info):
        """Generate PDF using ReportLab"""
        try:
            # Fetch form data
            user_data = self._fetch_form_data(form_id)
            if not user_data:
                raise Exception("Form data not found")
            
            # Get recommended coverage
            recommended_coverage = self._get_recommended_coverage(user_data)
            
            # Generate filename
            pdf_filename = f"{user_data['name'].replace(' ', '_')}_Health_Insurance_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(self.output_folder, pdf_filename)
            
            # Create PDF
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Container for the 'Flowable' objects
            elements = []
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#2c5f2d'),
                spaceAfter=12,
                spaceBefore=20
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=12,
                leading=18,
                alignment=TA_JUSTIFY
            )
            
            # Title
            elements.append(Paragraph("Health Insurance Requirement Analysis", title_style))
            
            # Timestamp
            ist = pytz.timezone('Asia/Kolkata')
            form_timestamp = user_data.get('form_timestamp')
            if form_timestamp:
                if isinstance(form_timestamp, datetime):
                    form_date = form_timestamp.strftime('%d-%b-%Y')
                else:
                    form_date = str(form_timestamp)
                timestamp_text = f"Report generated based on data provided on {form_date}"
            else:
                timestamp_text = "Report generated"
            
            elements.append(Paragraph(timestamp_text, styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Customer Details Section
            elements.append(Paragraph("Customer Details", heading_style))
            
            # Create details table
            details_data = [
                ["Name", user_data.get('name', 'N/A').title()],
                ["Email", self._mask_email(user_data.get('email', 'N/A'))],
                ["Mobile", f"{str(user_data.get('mobile', 'N/A'))[:2]}****{str(user_data.get('mobile', 'N/A'))[-2:]}"],
                ["Age", f"{user_data.get('age', 'N/A')} Years"],
                ["City of Residence", f"{user_data.get('city_of_residence', 'N/A').title()} ({user_data.get('tier_city', 'N/A')})"],
                ["Number of Family Members", str(user_data.get('number_of_members', 'N/A'))],
                ["Eldest Member Age", f"{user_data.get('eldest_member_age', 'N/A')} Years"],
                ["Pre-existing Diseases", user_data.get('pre_existing_diseases', 'N/A').title()],
                ["History of Major Surgery", user_data.get('major_surgery', 'N/A').title()],
                ["Existing Health Insurance", user_data.get('existing_insurance', 'N/A').title()],
                ["Current Coverage", self._format_currency(user_data.get('current_coverage', 0))],
                ["Port Existing Policy", user_data.get('port_policy', 'N/A').title()]
            ]
            
            # Create table
            details_table = Table(details_data, colWidths=[6*cm, 10*cm])
            details_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(details_table)
            elements.append(Spacer(1, 30))
            
            # Recommendation Section
            elements.append(Paragraph("Recommended Health Insurance Coverage", heading_style))
            
            # Recommendation text
            recommendation_text = f"Based on the above details provided, a comprehensive Health Insurance cover of <b>{self._format_currency(recommended_coverage)}</b> is highly recommended."
            
            if user_data.get('existing_insurance', 'No').lower() == 'yes':
                current_cov = user_data.get('current_coverage', 0)
                if current_cov and current_cov > 0:
                    if current_cov >= recommended_coverage:
                        recommendation_text += f"<br/><br/>Your current coverage of {self._format_currency(current_cov)} appears adequate."
                    else:
                        gap = recommended_coverage - current_cov
                        recommendation_text += f"<br/><br/>Your current coverage of {self._format_currency(current_cov)} has a gap of {self._format_currency(gap)}. Consider increasing your coverage."
            
            if int(user_data.get('number_of_members', 1)) > 1:
                recommendation_text += f"<br/><br/>Note: The recommendation includes an adjustment for your family size ({user_data.get('number_of_members', 'N/A')} members)."
            
            elements.append(Paragraph(recommendation_text, body_style))
            elements.append(Spacer(1, 40))
            
            # Footer Section
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            
            # Agent Details
            agent_details = f"<b>{agent_info['name']}</b><br/>Financial Advisor<br/>+91 {agent_info['phone']}"
            elements.append(Paragraph(agent_details, footer_style))
            
            # Generation timestamp
            now_ist = datetime.now(ist)
            generated_time = now_ist.strftime("%d-%b-%Y %I:%M %p")
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"Generated on {generated_time}", footer_style))
            
            # Build PDF
            doc.build(elements)
            
            return pdf_filename
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            raise e