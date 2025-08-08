from pymongo import MongoClient
from flask import current_app, g

def get_db():
    """Get MongoDB database instance"""
    if 'db' not in g:
        client = MongoClient(current_app.config['MONGO_URI'])
        db_name = current_app.config['MONGO_URI'].split('/')[-1]
        g.db = client[db_name]
    return g.db

# Collections
def get_users_collection():
    return get_db()['users']

def get_plans_collection():
    return get_db()['plans']

def get_coupons_collection():
    return get_db()['coupons']

def get_activities_collection():
    return get_db()['activities']