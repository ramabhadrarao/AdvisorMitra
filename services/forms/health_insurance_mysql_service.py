# services/forms/health_insurance_mysql_service.py
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import uuid
import secrets
from models import get_users_collection
from utils.helpers import log_activity
import subprocess
import os
from flask import current_app
from bson import ObjectId

class HealthInsuranceFormService:
    def __init__(self):
        self.users = get_users_collection()  # MongoDB for users
        
    def get_db_connection(self):
        """Get MySQL database connection"""
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="fpdb",
                password="fpdb",
                database="fpdb"
            )
            return conn
        except Error as e:
            print(f"Database connection error: {e}")
            return None
    
    def create_form_link(self, agent_id, language='en', expires_days=30, usage_limit=None):
        """Create a form link for health insurance"""
        # Get agent details from MongoDB
        agent = self.users.find_one({'_id': ObjectId(agent_id)})
        if not agent:
            return None, "Agent not found"
        
        # Check if agent has active plan and PDF limit
        if not agent.get('plan_id') or agent.get('agent_pdf_generated', 0) >= agent.get('agent_pdf_limit', 0):
            return None, "Agent has reached PDF generation limit"
        
        conn = self.get_db_connection()
        if not conn:
            return None, "Database connection error"
        
        try:
            cursor = conn.cursor()
            link_id = str(uuid.uuid4())
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None
            
            query = """
            INSERT INTO form_links (
                id, token, form_type, agent_id, agent_name, agent_phone, 
                language, created_by, expires_at, usage_limit
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                link_id,
                token,
                'health_insurance',
                str(agent_id),
                agent.get('full_name', agent.get('username')),
                agent.get('phone', ''),
                language,
                str(agent_id),
                expires_at,
                usage_limit
            )
            
            cursor.execute(query, values)
            conn.commit()
            
            # Log activity
            log_activity(
                str(agent_id),
                'FORM_LINK_CREATED',
                f"Created health insurance form link",
                {'link_id': link_id, 'language': language}
            )
            
            return link_id, token
            
        except Error as e:
            print(f"Error creating form link: {e}")
            return None, str(e)
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_form_link(self, token):
        """Get form link by token"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM form_links WHERE token = %s"
            cursor.execute(query, (token,))
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"Error getting form link: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def submit_form(self, form_data, token):
        """Submit health insurance form"""
        # Validate token
        link = self.get_form_link(token)
        if not link:
            return None, "Invalid form link"
        
        # Check if link is valid
        if not link['is_active']:
            return None, "Link is not active"
        
        if link['expires_at'] and datetime.utcnow() > link['expires_at']:
            return None, "Link has expired"
        
        if link['usage_limit'] and link['usage_count'] >= link['usage_limit']:
            return None, "Link usage limit exceeded"
        
        # Check agent PDF limit
        agent = self.users.find_one({'_id': ObjectId(link['agent_id'])})
        if agent.get('agent_pdf_generated', 0) >= agent.get('agent_pdf_limit', 0):
            return None, "Agent has reached PDF generation limit"
        
        conn = self.get_db_connection()
        if not conn:
            return None, "Database connection error"
        
        try:
            cursor = conn.cursor()
            form_id = str(uuid.uuid4())
            
            # Calculate tier city
            tier1_cities = [
                'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 
                'Chennai', 'Kolkata', 'Pune', 'Ahmedabad'
            ]
            tier_city = 'Tier 1' if form_data.get('city_of_residence') in tier1_cities else 'Others'
            
            # Insert form data
            insert_query = """
            INSERT INTO health_insurance_form (
                id, form_link_id, agent_id, language, name, email, mobile,
                city_of_residence, age, number_of_members, eldest_member_age,
                pre_existing_diseases, major_surgery, existing_insurance,
                current_coverage, port_policy, tier_city
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                form_id,
                link['id'],
                link['agent_id'],
                form_data.get('language', link['language']),
                form_data.get('name'),
                form_data.get('email'),
                form_data.get('mobile'),
                form_data.get('city_of_residence'),
                form_data.get('age'),
                form_data.get('number_of_members'),
                form_data.get('eldest_member_age'),
                form_data.get('pre_existing_diseases'),
                form_data.get('major_surgery'),
                form_data.get('existing_insurance'),
                form_data.get('current_coverage', 0),
                form_data.get('port_policy', 'No'),
                tier_city
            )
            
            cursor.execute(insert_query, values)
            
            # Update link usage count
            update_query = "UPDATE form_links SET usage_count = usage_count + 1 WHERE id = %s"
            cursor.execute(update_query, (link['id'],))
            
            conn.commit()
            
            # Log activity
            log_activity(
                link['agent_id'],
                'FORM_SUBMITTED',
                f"Health insurance form submitted by {form_data.get('name')}",
                {'form_id': form_id}
            )
            
            return form_id, None
            
        except Error as e:
            conn.rollback()
            print(f"Error submitting form: {e}")
            return None, str(e)
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_form_by_id(self, form_id):
        """Get form by ID"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM health_insurance_form WHERE id = %s"
            cursor.execute(query, (form_id,))
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"Error getting form: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_agent_forms(self, agent_id, page=1, per_page=10):
        """Get all forms submitted via agent's links"""
        conn = self.get_db_connection()
        if not conn:
            return {'forms': [], 'total': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM health_insurance_form WHERE agent_id = %s"
            cursor.execute(count_query, (str(agent_id),))
            total = cursor.fetchone()['total']
            
            # Get paginated results
            offset = (page - 1) * per_page
            query = """
            SELECT * FROM health_insurance_form 
            WHERE agent_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (str(agent_id), per_page, offset))
            forms = cursor.fetchall()
            
            return {
                'forms': forms,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
            
        except Error as e:
            print(f"Error getting agent forms: {e}")
            return {'forms': [], 'total': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def generate_pdf(self, form_id, agent_id):
        """Generate PDF for health insurance form"""
        form = self.get_form_by_id(form_id)
        if not form:
            return None, "Form not found"
        
        # Verify agent owns this form
        if form['agent_id'] != str(agent_id):
            return None, "Unauthorized access"
        
        # Get agent details
        agent = self.users.find_one({'_id': ObjectId(agent_id)})
        if not agent:
            return None, "Agent not found"
        
        # Check PDF limit
        if agent.get('agent_pdf_generated', 0) >= agent.get('agent_pdf_limit', 0):
            return None, "PDF generation limit reached"
        
        # Check if PDF already generated
        if form['pdf_generated'] and form['pdf_filename']:
            pdf_path = os.path.join('/root/generated_pdfs', form['pdf_filename'])
            if os.path.exists(pdf_path):
                return form['pdf_filename'], None
        
        try:
            # Call PDF generator
            # The Python script expects email as the identifier to look up the form
            cmd = [
                'python3',
                '/root/AM-MF-HealthInsurance-en.py',  # Update this path as needed
                form['email'],
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
            conn = self.get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    update_query = """
                    UPDATE health_insurance_form 
                    SET pdf_generated = TRUE, 
                        pdf_generated_at = %s, 
                        pdf_filename = %s 
                    WHERE id = %s
                    """
                    cursor.execute(update_query, (datetime.utcnow(), pdf_filename, form_id))
                    conn.commit()
                finally:
                    if conn.is_connected():
                        cursor.close()
                        conn.close()
            
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
                str(agent_id),
                'PDF_GENERATED',
                f"Generated health insurance PDF for {form['name']}",
                {'form_id': form_id, 'pdf_filename': pdf_filename}
            )
            
            return pdf_filename, None
            
        except Exception as e:
            return None, f"PDF generation error: {str(e)}"
    
    def get_form_links(self, agent_id, page=1, per_page=10):
        """Get all form links created by agent"""
        conn = self.get_db_connection()
        if not conn:
            return {'links': [], 'total': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get total count
            count_query = """
            SELECT COUNT(*) as total FROM form_links 
            WHERE agent_id = %s AND form_type = 'health_insurance'
            """
            cursor.execute(count_query, (str(agent_id),))
            total = cursor.fetchone()['total']
            
            # Get paginated results
            offset = (page - 1) * per_page
            query = """
            SELECT * FROM form_links 
            WHERE agent_id = %s AND form_type = 'health_insurance'
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (str(agent_id), per_page, offset))
            links = cursor.fetchall()
            
            return {
                'links': links,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
            
        except Error as e:
            print(f"Error getting form links: {e}")
            return {'links': [], 'total': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def toggle_link_status(self, link_id, agent_id):
        """Toggle form link active status"""
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get link and verify ownership
            check_query = "SELECT * FROM form_links WHERE id = %s AND agent_id = %s"
            cursor.execute(check_query, (link_id, str(agent_id)))
            link = cursor.fetchone()
            
            if not link:
                return False
            
            # Toggle status
            new_status = not link['is_active']
            update_query = "UPDATE form_links SET is_active = %s WHERE id = %s"
            cursor.execute(update_query, (new_status, link_id))
            conn.commit()
            
            return True
            
        except Error as e:
            print(f"Error toggling link status: {e}")
            return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()