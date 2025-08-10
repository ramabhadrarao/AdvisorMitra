#!/usr/bin/env python3
# services/forms/pdf_generators/health_insurance_pdf.py
# MongoDB-based PDF generator for health insurance forms

import sys
import os
import asyncio
from datetime import datetime
import locale
from pyppeteer import launch
import pytz
from pymongo import MongoClient
from bson import ObjectId

# Set locale to Indian format
locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')

def get_mongodb_connection():
    """Get MongoDB connection"""
    # Update with your MongoDB URI
    client = MongoClient('mongodb://localhost:27017/advisormitra')
    return client.advisormitra

def mask_email(email):
    """Masks an email address for privacy."""
    if not email or "@" not in str(email):
        return "N/A"
    username, domain = str(email).split('@')
    return f"{username[:2]}****{username[-2:]}@{domain}" if len(username) > 4 else f"{username[0]}****@{domain}"

def format_currency_html(value):
    """Formats a numeric value into Indian currency format."""
    try:
        if not value or value == 0:
            return "N/A"
        val = float(value)
        actual = f"₹{locale.format_string('%.0f', val, grouping=True)}"

        if val >= 10000000:
            summary = f"₹{val / 10000000:.1f} Crores"
        elif val >= 100000:
            summary = f"₹{val / 100000:.1f} Lakhs"
        elif val >= 1000:
            summary = f"₹{val / 1000:.1f} Thousands"
        else:
            summary = f"₹{val:.1f}"

        return f"{actual} ({summary})"
    except (ValueError, TypeError):
        return str(value)

def get_age_group(age):
    """Determine age group based on age."""
    if age <= 35:
        return "25-35"
    elif age <= 45:
        return "36-45"
    else:
        return "45+"

def fetch_data_from_mongodb(form_id):
    """Fetch health insurance data for a given form ID from MongoDB."""
    try:
        db = get_mongodb_connection()
        
        # Fetch form data
        form = db.health_insurance_forms.find_one({'_id': ObjectId(form_id)})
        
        if form:
            user_data = {
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
                'form_timestamp': form.get('form_timestamp', form.get('created_at')),
                'tier_city': form.get('tier_city', 'Others')
            }
            
            return user_data
        else:
            print(f"No data found for form ID {form_id}")
            return None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def get_recommended_coverage(user_data):
    """Get recommended coverage from insurance_recommendations collection."""
    try:
        db = get_mongodb_connection()
        
        # Determine parameters for recommendation
        age_group = get_age_group(user_data['eldest_member_age'])
        city_tier = user_data['tier_city']
        pre_existing = 'Yes' if user_data['pre_existing_diseases'] == 'Yes' else 'No'
        
        # Fetch recommendation from MongoDB
        recommendation = db.insurance_recommendations.find_one({
            'age_group': age_group,
            'city_tier': city_tier,
            'pre_existing_condition': pre_existing
        })
        
        if recommendation:
            base_coverage = recommendation['recommendation_amount'] * 100000  # Convert lakhs to rupees
            
            # Adjust for family size
            family_members = user_data.get('number_of_members', 1)
            if family_members > 4:
                base_coverage *= 1.5
            elif family_members > 2:
                base_coverage *= 1.25
            
            return round(base_coverage / 100000) * 100000  # Round to nearest lakh
        
        # Default recommendation if not found
        return 1000000  # 10 lakhs default

    except Exception as e:
        print(f"Database error: {e}")
        return 1000000  # 10 lakhs default

def generate_full_html(user_data, recommended_coverage, agent_name, agent_phone):
    """Generates the full HTML content following the correct PDF format."""
    css = """
/* Global styles */
@font-face {
    font-family: 'DejaVu Sans';
    src: url('file:////usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
}
@font-face {
    font-family: 'DejaVu Sans';
    src: url('file:////usr/share/fonts/truetype/dejavu//DejaVuSans-Bold.ttf') format('truetype');
    font-weight: bold;
    font-style: normal;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'DejaVu Sans', sans-serif;
  font-size: 1.2em;
}

.page {
  width: 100%;
  min-height: calc(100vh - 2cm);
  border: 0.2cm solid #000;
  padding: 0.5cm;
  padding-bottom: 120px;
  box-sizing: border-box;
  margin: 0.5cm;
  position: relative;
}

.header {
  text-align: center;
  margin-bottom: 20px;
}
.header h1 {
  white-space: nowrap;
  font-size: 1.6em;
  margin: 0;
}
.header h2 {
  margin: 0;
  font-size: 1.4em;
}
.header p {
  margin: 5px 0;
  text-align: center;
}

.details h3 {
  text-align: center;
  margin-bottom: 10px;
  font-size: 1.2em;
}
.details table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.details table th {
  width: 65%;
  border: 1px solid #000;
  padding: 4px 2px;
  font-size: .9em;
  text-align: left;
  white-space: nowrap;
}
.details table td {
  width: 35%;
  border: 1px solid #000;
  padding: 4px 2px;
  font-size: .9em;
  text-align: left;
  white-space: nowrap;
}

.analysis h3 {
  text-align: left;
  margin-bottom: 10px;
  font-size: 1.2em;
}
.analysis p {
  text-align: left;
  font-size: 1.1em;
  color: green;
}

.footer {
  border-top: 1px solid #000;
  padding: 5px;
  font-size: 0.9em;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.footer-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.footer-left {
  flex: 1;
  text-align: left;
  font-weight: bold;
}
.footer-right {
  flex: 1;
  text-align: right;
}
.footer-right .advisor {
  font-size: 1.2em;
  font-weight: bold;
}
.footer-right .title {
  font-size: 1em;
}
.footer-bottom {
  text-align: center;
  font-size: 0.9em;
}
.page-break {
    page-break-before: always;
}
@media print {
  @page {
    size: A4;
    margin: 0.5cm;
  }
  .page {
    margin: 0;
    padding: 0.5cm;
    border: 0.2cm solid #000;
  }
  p {
    text-align: justify;
    margin: 0 0 1em;
  }
  img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
  }
}
"""

    # Format timestamp
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    generated_time = now_ist.strftime("%d-%b-%y %I:%M %p")
    form_timestamp = user_data.get('form_timestamp')
    
    if form_timestamp:
        if isinstance(form_timestamp, datetime):
            form_date = form_timestamp.strftime('%d-%b-%y')
        else:
            form_date = str(form_timestamp)
        timestamp_text = f"Report generated based on data provided on {form_date}"
    else:
        timestamp_text = "Report generated: Timestamp not available"

    # User Details Table
    details_list = [
        ("Name", user_data.get('name', 'N/A').title()),
        ("Email", mask_email(user_data.get('email', 'N/A'))),
        ("Mobile", f"{str(user_data.get('mobile', 'N/A'))[:2]}****{str(user_data.get('mobile', 'N/A'))[-2:]}"),
        ("Age", f"{user_data.get('age', 'N/A')} Years"),
        ("City of Residence",
         f"{user_data.get('city_of_residence', 'N/A').title()} ({user_data.get('tier_city', 'N/A')})"),
        ("Number of Family Members", user_data.get('number_of_members', 'N/A')),
        ("Eldest Member Age", f"{user_data.get('eldest_member_age', 'N/A')} Years"),
        ("Pre-existing Diseases", user_data.get('pre_existing_diseases', 'N/A').title()),
        ("History of Major Surgery", user_data.get('major_surgery', 'N/A').title()),
        ("Existing Health Insurance", user_data.get('existing_insurance', 'N/A').title()),
        ("Current Coverage", format_currency_html(user_data.get('current_coverage', 0))),
        ("Port Existing Policy", user_data.get('port_policy', 'N/A').title())
    ]
    
    details_html = "<table class='section'>"
    for label, value in details_list:
        details_html += f"<tr><th>{label}</th><td>{value}</td></tr>"
    details_html += "</table>"

    # Analysis Comment
    analysis_comment = (
        f"Based on the above details provided a comprehensive Health Insurance cover of Rs <strong>{format_currency_html(recommended_coverage)}</strong>  "
        f"is highly recommended . "
    )

    if user_data.get('existing_insurance', 'No').lower() == 'yes':
        current_cov = user_data.get('current_coverage', 0)
        if current_cov and current_cov > 0:
            if current_cov >= recommended_coverage:
                analysis_comment += (
                    f"<br><br>Your current coverage of {format_currency_html(current_cov)} appears adequate."
                )
            else:
                gap = recommended_coverage - current_cov
                analysis_comment += (
                    f"<br><br>Your current coverage of {format_currency_html(current_cov)} has a "
                    f"gap of {format_currency_html(gap)}. Consider increasing your coverage."
                )

    # Add note about family size adjustment
    if int(user_data.get('number_of_members', 1)) > 1:
        analysis_comment += (
            f"<br><br>Note: The recommendation includes an adjustment for your family size "
            f"({user_data.get('number_of_members', 'N/A')} members)."
        )

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Health Insurance Requirement Analysis</title>
    <style>
    {css}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <h1>Health Insurance Requirement Analysis</h1>
      <p>{timestamp_text}</p>
    </div>
    <div class="section details">
      <h3>Details</h3>
      {details_html}
    </div>
    <div class="section analysis">
      <h3>Recommended Health Insurance Coverage</h3>
      <p>{analysis_comment}</p>
    </div>
    <div class="footer">
      <div class="footer-top">
          <div class="footer-left">
              <strong>+91 {agent_phone}</strong>
          </div>
          <div class="footer-right">
              <div class="advisor">{agent_name}</div>
              <div class="title">Financial Advisor</div>
          </div>
      </div>
      <div class="footer-bottom">
              Generated on {generated_time}
      </div>
    </div>
  </div>
</body>
</html>
"""
    return full_html

def main():
    """Main function to generate the health insurance needs PDF."""
    try:
        if len(sys.argv) < 4:
            print("Error: Insufficient command-line arguments.")
            print("Usage: python health_insurance_pdf.py <form_id> <agent_name> <agent_phone>")
            return

        form_id = sys.argv[1]  # MongoDB ObjectId
        agent_name = sys.argv[2]  # Get agent name
        agent_phone = sys.argv[3]  # Get agent phone

        # Fetch data from MongoDB
        user_data = fetch_data_from_mongodb(form_id)
        if user_data is None:
            print("Failed to fetch user data from database.")
            return

        # Get recommended coverage
        recommended_coverage = get_recommended_coverage(user_data)
        if recommended_coverage is None:
            print("Failed to get insurance recommendation from database.")
            return

        # Generate full HTML content
        full_html = generate_full_html(user_data, recommended_coverage, agent_name, agent_phone)

        # Save HTML file
        html_output_folder = r"/root/generated_pdfs"
        os.makedirs(html_output_folder, exist_ok=True)
        html_file_name = f"{user_data['name'].title()}_Health Insurance Requirement Analysis.html"
        html_file_path = os.path.join(html_output_folder, html_file_name)
        
        # Handle duplicate filenames
        counter = 1
        while os.path.exists(html_file_path):
            html_file_name = f"{user_data['name'].title()}_Health Insurance Requirement Analysis_{counter}.html"
            html_file_path = os.path.join(html_output_folder, html_file_name)
            counter += 1
            
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"HTML file generated: {html_file_path}")

        # Define PDF output folder and file name
        pdf_output_folder = r"/root/generated_pdfs"
        os.makedirs(pdf_output_folder, exist_ok=True)
        pdf_file_name = os.path.basename(html_file_path).replace('.html', '.pdf')
        pdf_file_path = os.path.join(pdf_output_folder, pdf_file_name)
        print(f"PDF_FILENAME={pdf_file_name}")
        print(f"PDF_FILEPATH={pdf_file_path}")

        # Convert HTML to PDF using Pyppeteer
        async def html_to_pdf(html_file, pdf_file):
            executable_path = r"/usr/bin/google-chrome"
            browser = await launch(
                headless=True,
                args=['--no-sandbox'],
                executablePath=executable_path
            )
            page = await browser.newPage()
            abs_html = os.path.abspath(html_file)
            file_url = f'file:///{abs_html.replace(os.sep, "/")}'
            await page.goto(file_url, {'waitUntil': 'networkidle0'})
            await page.pdf({
                'path': pdf_file,
                'printBackground': True,
                'displayHeaderFooter': False,
            })
            await browser.close()

        asyncio.run(html_to_pdf(html_file_path, pdf_file_path))
        print(f"PDF generated: {pdf_file_path}")

    except Exception as e:
        print(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()