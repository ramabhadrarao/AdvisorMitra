# services/email_service.py
# Email service for sending registration links and notifications

from flask import current_app, render_template_string
from flask_mail import Message
import logging

class EmailService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_agent_registration_link(self, recipient_email, recipient_name, registration_url, partner_name):
        """Send registration link via email to agent"""
        try:
            # Import mail here to avoid circular import
            from app import mail
            
            subject = f"Agent Registration Invitation from {partner_name}"
            
            # HTML email template
            html_body = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background-color: #f4f4f4; }
                    .button { display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                    .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Agent Registration Invitation</h1>
                    </div>
                    <div class="content">
                        <p>Dear {{ recipient_name }},</p>
                        
                        <p>You have been invited by <strong>{{ partner_name }}</strong> to register as an agent in our Financial Planning System.</p>
                        
                        <p>Please click the button below to complete your registration:</p>
                        
                        <center>
                            <a href="{{ registration_url }}" class="button">Complete Registration</a>
                        </center>
                        
                        <p>Or copy and paste this link in your browser:</p>
                        <p style="word-break: break-all; background: #fff; padding: 10px; border: 1px solid #ddd;">
                            {{ registration_url }}
                        </p>
                        
                        <p><strong>Note:</strong> This registration link is unique to you. Please do not share it with others.</p>
                        
                        <p>If you have any questions, please contact your partner or our support team.</p>
                        
                        <p>Best regards,<br>
                        Financial Planning System Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply to this message.</p>
                        <p>&copy; 2024 Financial Planning System. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Render template with variables
            html_content = render_template_string(html_body, 
                recipient_name=recipient_name,
                partner_name=partner_name,
                registration_url=registration_url
            )
            
            # Text version
            text_body = f"""
Dear {recipient_name},

You have been invited by {partner_name} to register as an agent in our Financial Planning System.

Please click the following link to complete your registration:
{registration_url}

Note: This registration link is unique to you. Please do not share it with others.

If you have any questions, please contact your partner or our support team.

Best regards,
Financial Planning System Team
            """
            
            msg = Message(
                subject=subject,
                recipients=[recipient_email],
                body=text_body,
                html=html_content
            )
            
            mail.send(msg)
            self.logger.info(f"Registration link email sent to {recipient_email}")
            return True, "Email sent successfully"
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return False, f"Failed to send email: {str(e)}"
    
    def get_whatsapp_message(self, recipient_name, registration_url, partner_name):
        """Generate WhatsApp message with registration link"""
        message = f"""Hello {recipient_name},

You have been invited by *{partner_name}* to register as an agent in our Financial Planning System.

Please click the link below to complete your registration:
{registration_url}

*Note:* This registration link is unique to you. Please do not share it with others.

If you have any questions, please contact your partner.

Regards,
Financial Planning System Team"""
        
        return message