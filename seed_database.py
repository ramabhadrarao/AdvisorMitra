# seed_database.py
# Database seeder script to populate test data

import os
import sys
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import MongoClient

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from models.user import User
from models.plan import Plan
from models.coupon import Coupon
from utils.helpers import calculate_plan_expiry

def clear_existing_data(db):
    """Clear all existing data except super admin"""
    print("Clearing existing data...")
    
    # Clear all users except super admin
    db.users.delete_many({'role': {'$ne': 'SUPER_ADMIN'}})
    
    # Clear all other collections
    db.plans.delete_many({})
    db.coupons.delete_many({})
    db.activities.delete_many({})
    db.registration_links.delete_many({})
    
    print("Existing data cleared (super admin preserved)")

def create_plans(db):
    """Create sample plans"""
    print("Creating plans...")
    
    plans = [
        {
            'name': 'Basic Plan',
            'description': 'Perfect for individual agents just starting out',
            'period_type': 'MONTHLY',
            'period_value': 1,
            'price': 999.00,
            'pdf_limit': 50,
            'features': [
                'Generate up to 50 PDFs per month',
                'Basic financial planning tools',
                'Email support',
                'Access to standard templates'
            ],
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': 'Professional Plan',
            'description': 'Ideal for growing agencies with multiple clients',
            'period_type': 'MONTHLY',
            'period_value': 1,
            'price': 2499.00,
            'pdf_limit': 200,
            'features': [
                'Generate up to 200 PDFs per month',
                'Advanced financial planning tools',
                'Priority email & phone support',
                'Access to premium templates',
                'Client management dashboard'
            ],
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': 'Enterprise Plan',
            'description': 'Comprehensive solution for large agencies',
            'period_type': 'YEARLY',
            'period_value': 1,
            'price': 49999.00,
            'pdf_limit': 5000,
            'features': [
                'Generate up to 5000 PDFs per year',
                'All advanced features included',
                '24/7 dedicated support',
                'Custom templates and branding',
                'API access',
                'Training sessions included'
            ],
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': 'Starter Plan',
            'description': 'Free trial plan for new users',
            'period_type': 'MONTHLY',
            'period_value': 1,
            'price': 0.00,
            'pdf_limit': 10,
            'features': [
                'Generate up to 10 PDFs per month',
                'Basic features only',
                'Community support',
                'Limited templates'
            ],
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]
    
    plan_ids = []
    for plan_data in plans:
        result = db.plans.insert_one(plan_data)
        plan_ids.append(result.inserted_id)
        print(f"  Created plan: {plan_data['name']}")
    
    return plan_ids

def create_coupons(db):
    """Create sample coupons"""
    print("Creating coupons...")
    
    coupons = [
        {
            'code': 'WELCOME20',
            'name': 'Welcome Discount',
            'description': 'New customer discount - 20% off first purchase',
            'discount_type': 'PERCENTAGE',
            'discount_value': 20,
            'max_discount_amount': 1000,
            'min_purchase_amount': 500,
            'usage_limit': 100,
            'used_count': 15,
            'valid_from': datetime.utcnow() - timedelta(days=30),
            'valid_until': datetime.utcnow() + timedelta(days=60),
            'is_active': True,
            'applicable_plans': [],  # All plans
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'code': 'FLAT500',
            'name': 'Flat ₹500 Off',
            'description': 'Get flat ₹500 off on any plan',
            'discount_type': 'FIXED',
            'discount_value': 500,
            'min_purchase_amount': 2000,
            'usage_limit': 50,
            'used_count': 10,
            'valid_from': datetime.utcnow(),
            'valid_until': datetime.utcnow() + timedelta(days=90),
            'is_active': True,
            'applicable_plans': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'code': 'PARTNER30',
            'name': 'Partner Special',
            'description': 'Special 30% discount for partner agents',
            'discount_type': 'PERCENTAGE',
            'discount_value': 30,
            'max_discount_amount': 2000,
            'min_purchase_amount': 1000,
            'usage_limit': None,  # Unlimited
            'used_count': 25,
            'valid_from': datetime.utcnow(),
            'valid_until': datetime.utcnow() + timedelta(days=180),
            'is_active': True,
            'applicable_plans': [],
            'partner_limits': {},  # Will be updated with partner IDs
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'code': 'EXPIRED10',
            'name': 'Expired Offer',
            'description': 'This offer has expired',
            'discount_type': 'PERCENTAGE',
            'discount_value': 10,
            'min_purchase_amount': 0,
            'usage_limit': 10,
            'used_count': 10,
            'valid_from': datetime.utcnow() - timedelta(days=60),
            'valid_until': datetime.utcnow() - timedelta(days=1),
            'is_active': True,
            'applicable_plans': [],
            'created_at': datetime.utcnow() - timedelta(days=60),
            'updated_at': datetime.utcnow()
        }
    ]
    
    coupon_ids = []
    for coupon_data in coupons:
        result = db.coupons.insert_one(coupon_data)
        coupon_ids.append(result.inserted_id)
        print(f"  Created coupon: {coupon_data['code']} - {coupon_data['name']}")
    
    return coupon_ids

def create_partners(db, plan_ids, coupon_ids):
    """Create sample partners"""
    print("Creating partners...")
    
    partners = [
        {
            'username': 'partner1',
            'email': 'partner1@example.com',
            'password': User.hash_password('partner123'),
            'full_name': 'John Smith',
            'phone': '+91 98765 43210',
            'role': 'PARTNER',
            'is_active': True,
            'approval_status': 'APPROVED',
            'requires_double_approval': True,
            'pdf_limit': 1000,
            'pdf_generated': 250,
            'assigned_plans': plan_ids[:3],  # First 3 plans
            'assigned_coupons': coupon_ids[:3],  # First 3 coupons
            'super_admin_approved': True,
            'super_admin_approved_at': datetime.utcnow(),
            'created_at': datetime.utcnow() - timedelta(days=90),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'partner2',
            'email': 'partner2@example.com',
            'password': User.hash_password('partner123'),
            'full_name': 'Sarah Johnson',
            'phone': '+91 98765 43211',
            'role': 'PARTNER',
            'is_active': True,
            'approval_status': 'APPROVED',
            'requires_double_approval': False,
            'pdf_limit': 2000,
            'pdf_generated': 750,
            'assigned_plans': plan_ids,  # All plans
            'assigned_coupons': coupon_ids,  # All coupons
            'super_admin_approved': True,
            'super_admin_approved_at': datetime.utcnow(),
            'created_at': datetime.utcnow() - timedelta(days=60),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'partner3',
            'email': 'partner3@example.com',
            'password': User.hash_password('partner123'),
            'full_name': 'Michael Brown',
            'phone': '+91 98765 43212',
            'role': 'PARTNER',
            'is_active': True,
            'approval_status': 'PENDING',
            'requires_double_approval': True,
            'pdf_limit': 500,
            'pdf_generated': 0,
            'assigned_plans': plan_ids[1:3],  # Professional and Enterprise plans
            'assigned_coupons': coupon_ids[1:3],  # Some coupons
            'created_at': datetime.utcnow() - timedelta(days=5),
            'updated_at': datetime.utcnow()
        }
    ]
    
    partner_ids = []
    for partner_data in partners:
        result = db.users.insert_one(partner_data)
        partner_ids.append(result.inserted_id)
        print(f"  Created partner: {partner_data['username']} - {partner_data['full_name']}")
    
    # Update partner limits for PARTNER30 coupon
    db.coupons.update_one(
        {'code': 'PARTNER30'},
        {
            '$set': {
                'partner_limits': {
                    str(partner_ids[0]): {'limit': 50, 'used': 5},
                    str(partner_ids[1]): {'limit': 100, 'used': 20}
                }
            }
        }
    )
    
    return partner_ids

def create_agents(db, partner_ids, plan_ids):
    """Create sample agents"""
    print("Creating agents...")
    
    agents = [
        # Partner 1's agents
        {
            'username': 'agent1',
            'email': 'agent1@example.com',
            'password': User.hash_password('agent123'),
            'full_name': 'David Wilson',
            'phone': '+91 98765 43220',
            'role': 'AGENT',
            'partner_id': partner_ids[0],
            'is_active': True,
            'approval_status': 'APPROVED',
            'requires_double_approval': True,
            'partner_approved': True,
            'partner_approved_at': datetime.utcnow() - timedelta(days=20),
            'super_admin_approved': True,
            'super_admin_approved_at': datetime.utcnow() - timedelta(days=19),
            'plan_id': plan_ids[1],  # Professional Plan
            'plan_start_date': datetime.utcnow() - timedelta(days=15),
            'plan_expiry_date': datetime.utcnow() + timedelta(days=15),
            'agent_pdf_limit': 200,
            'agent_pdf_generated': 75,
            'created_at': datetime.utcnow() - timedelta(days=30),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'agent2',
            'email': 'agent2@example.com',
            'password': User.hash_password('agent123'),
            'full_name': 'Emily Davis',
            'phone': '+91 98765 43221',
            'role': 'AGENT',
            'partner_id': partner_ids[0],
            'is_active': True,
            'approval_status': 'PARTNER_APPROVED',
            'requires_double_approval': True,
            'partner_approved': True,
            'partner_approved_at': datetime.utcnow() - timedelta(days=2),
            'agent_pdf_limit': 0,
            'agent_pdf_generated': 0,
            'created_at': datetime.utcnow() - timedelta(days=5),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'agent3',
            'email': 'agent3@example.com',
            'password': User.hash_password('agent123'),
            'full_name': 'James Taylor',
            'phone': '+91 98765 43222',
            'role': 'AGENT',
            'partner_id': partner_ids[0],
            'is_active': True,
            'approval_status': 'PENDING',
            'requires_double_approval': True,
            'agent_pdf_limit': 0,
            'agent_pdf_generated': 0,
            'created_at': datetime.utcnow() - timedelta(days=1),
            'updated_at': datetime.utcnow()
        },
        
        # Partner 2's agents
        {
            'username': 'agent4',
            'email': 'agent4@example.com',
            'password': User.hash_password('agent123'),
            'full_name': 'Lisa Anderson',
            'phone': '+91 98765 43223',
            'role': 'AGENT',
            'partner_id': partner_ids[1],
            'is_active': True,
            'approval_status': 'APPROVED',
            'requires_double_approval': False,
            'partner_approved': True,
            'partner_approved_at': datetime.utcnow() - timedelta(days=45),
            'plan_id': plan_ids[2],  # Enterprise Plan
            'plan_start_date': datetime.utcnow() - timedelta(days=30),
            'plan_expiry_date': datetime.utcnow() + timedelta(days=335),
            'agent_pdf_limit': 5000,
            'agent_pdf_generated': 450,
            'created_at': datetime.utcnow() - timedelta(days=50),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'agent5',
            'email': 'agent5@example.com',
            'password': User.hash_password('agent123'),
            'full_name': 'Robert Martinez',
            'phone': '+91 98765 43224',
            'role': 'AGENT',
            'partner_id': partner_ids[1],
            'is_active': True,
            'approval_status': 'APPROVED',
            'requires_double_approval': False,
            'partner_approved': True,
            'partner_approved_at': datetime.utcnow() - timedelta(days=25),
            'plan_id': plan_ids[0],  # Basic Plan
            'plan_start_date': datetime.utcnow() - timedelta(days=20),
            'plan_expiry_date': datetime.utcnow() + timedelta(days=10),
            'agent_pdf_limit': 50,
            'agent_pdf_generated': 40,
            'created_at': datetime.utcnow() - timedelta(days=30),
            'updated_at': datetime.utcnow()
        },
        {
            'username': 'agent6',
            'email': 'agent6@example.com',
            'password': User.hash_password('agent123'),
            'full_name': 'Jennifer White',
            'phone': '+91 98765 43225',
            'role': 'AGENT',
            'partner_id': partner_ids[1],
            'is_active': False,
            'approval_status': 'REJECTED',
            'rejection_reason': 'Invalid documentation provided',
            'requires_double_approval': False,
            'agent_pdf_limit': 0,
            'agent_pdf_generated': 0,
            'created_at': datetime.utcnow() - timedelta(days=10),
            'updated_at': datetime.utcnow()
        }
    ]
    
    agent_ids = []
    for agent_data in agents:
        result = db.users.insert_one(agent_data)
        agent_ids.append(result.inserted_id)
        print(f"  Created agent: {agent_data['username']} - {agent_data['full_name']} (Partner: {agent_data['partner_id']})")
    
    return agent_ids

def create_activities(db, partner_ids, agent_ids, plan_ids):
    """Create sample activities"""
    print("Creating sample activities...")
    
    activities = [
        {
            'user_id': partner_ids[0],
            'activity_type': 'LOGIN',
            'description': 'Partner John Smith logged in',
            'metadata': {},
            'created_at': datetime.utcnow() - timedelta(hours=2)
        },
        {
            'user_id': agent_ids[0],
            'activity_type': 'PDF_GENERATED',
            'description': 'Generated financial plan PDF for client',
            'metadata': {'client_name': 'ABC Corp', 'plan_type': 'Investment'},
            'created_at': datetime.utcnow() - timedelta(hours=5)
        },
        {
            'user_id': partner_ids[1],
            'activity_type': 'AGENT_APPROVED',
            'description': 'Approved agent Lisa Anderson',
            'metadata': {'agent_id': str(agent_ids[3])},
            'created_at': datetime.utcnow() - timedelta(days=1)
        },
        {
            'user_id': agent_ids[4],
            'activity_type': 'PLAN_RENEWED',
            'description': 'Renewed Basic Plan subscription',
            'metadata': {'plan_id': str(plan_ids[0]), 'amount': 999},
            'created_at': datetime.utcnow() - timedelta(days=2)
        }
    ]
    
    for activity in activities:
        db.activities.insert_one(activity)
    
    print(f"  Created {len(activities)} sample activities")

def main():
    """Main seeder function"""
    print("Starting database seeding...")
    
    # Connect to MongoDB
    config_name = os.getenv('FLASK_ENV', 'development')
    app_config = config[config_name]
    client = MongoClient(app_config.MONGO_URI)
    db_name = app_config.MONGO_URI.split('/')[-1]
    db = client[db_name]
    
    # Clear existing data
    clear_existing_data(db)
    
    # Create data
    plan_ids = create_plans(db)
    coupon_ids = create_coupons(db)
    partner_ids = create_partners(db, plan_ids, coupon_ids)
    agent_ids = create_agents(db, partner_ids, plan_ids)
    create_activities(db, partner_ids, agent_ids, plan_ids)
    
    print("\nDatabase seeding completed successfully!")
    print("\n" + "="*50)
    print("LOGIN CREDENTIALS:")
    print("="*50)
    print("\nSUPER ADMIN:")
    print("  Username: superadmin")
    print("  Password: superadmin123")
    print("\nPARTNERS:")
    print("  Partner 1: partner1 / partner123 (Active, Double Approval)")
    print("  Partner 2: partner2 / partner123 (Active, Single Approval)")
    print("  Partner 3: partner3 / partner123 (Pending Approval)")
    print("\nAGENTS:")
    print("  Agent 1: agent1 / agent123 (Active with Professional Plan)")
    print("  Agent 2: agent2 / agent123 (Partner Approved, awaiting Super Admin)")
    print("  Agent 3: agent3 / agent123 (Pending Approval)")
    print("  Agent 4: agent4 / agent123 (Active with Enterprise Plan)")
    print("  Agent 5: agent5 / agent123 (Active with Basic Plan)")
    print("  Agent 6: agent6 / agent123 (Rejected)")
    print("\nCOUPONS:")
    print("  WELCOME20 - 20% off (max ₹1000)")
    print("  FLAT500 - Flat ₹500 off")
    print("  PARTNER30 - 30% partner special")
    print("  EXPIRED10 - Expired coupon")
    print("="*50)
    
    client.close()

if __name__ == '__main__':
    main()