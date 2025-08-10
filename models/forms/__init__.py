# models/forms/__init__.py
from pymongo import MongoClient
from flask import current_app, g

def get_health_insurance_forms_collection():
    return get_db()['health_insurance_forms']

def get_term_insurance_forms_collection():
    return get_db()['term_insurance_forms']

def get_child_education_forms_collection():
    return get_db()['child_education_forms']

def get_child_wedding_forms_collection():
    return get_db()['child_wedding_forms']

def get_financial_planning_forms_collection():
    return get_db()['financial_planning_forms']

def get_customer_forms_collection():
    return get_db()['customer_forms']

def get_form_links_collection():
    return get_db()['form_links']

def get_db():
    """Get MongoDB database instance"""
    if 'db' not in g:
        client = MongoClient(current_app.config['MONGO_URI'])
        db_name = current_app.config['MONGO_URI'].split('/')[-1]
        g.db = client[db_name]
    return g.db