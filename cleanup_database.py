# cleanup_database.py
# Script to clean all data except super admin

import os
import sys
from pymongo import MongoClient

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config

def cleanup_database():
    """Remove all data except super admin"""
    print("Starting database cleanup...")
    
    # Connect to MongoDB
    config_name = os.getenv('FLASK_ENV', 'development')
    app_config = config[config_name]
    client = MongoClient(app_config.MONGO_URI)
    db_name = app_config.MONGO_URI.split('/')[-1]
    db = client[db_name]
    
    # Clear all users except super admin
    result = db.users.delete_many({'role': {'$ne': 'SUPER_ADMIN'}})
    print(f"  Deleted {result.deleted_count} users (kept super admin)")
    
    # Clear all plans
    result = db.plans.delete_many({})
    print(f"  Deleted {result.deleted_count} plans")
    
    # Clear all coupons
    result = db.coupons.delete_many({})
    print(f"  Deleted {result.deleted_count} coupons")
    
    # Clear all activities
    result = db.activities.delete_many({})
    print(f"  Deleted {result.deleted_count} activities")
    
    # Clear all registration links
    result = db.registration_links.delete_many({})
    print(f"  Deleted {result.deleted_count} registration links")
    
    print("\nDatabase cleanup completed!")
    print("Only super admin account remains: superadmin / superadmin123")
    
    client.close()

if __name__ == '__main__':
    confirm = input("Are you sure you want to clean the database? This will remove all data except super admin. (yes/no): ")
    if confirm.lower() == 'yes':
        cleanup_database()
    else:
        print("Cleanup cancelled.")