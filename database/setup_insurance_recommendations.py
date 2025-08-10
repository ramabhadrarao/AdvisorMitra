#!/usr/bin/env python3
# database/setup_insurance_recommendations.py
# Setup script for insurance recommendations collection

from pymongo import MongoClient

def setup_recommendations():
    """Setup insurance recommendations collection with base data"""
    
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/advisormitra')
    db = client.advisormitra
    
    # Clear existing recommendations
    db.insurance_recommendations.drop()
    
    # Insert recommendation data
    recommendations = [
        # Tier 1 Cities - No Pre-existing
        {'age_group': '25-35', 'city_tier': 'Tier 1', 'pre_existing_condition': 'No', 'recommendation_amount': 10},
        {'age_group': '36-45', 'city_tier': 'Tier 1', 'pre_existing_condition': 'No', 'recommendation_amount': 15},
        {'age_group': '45+', 'city_tier': 'Tier 1', 'pre_existing_condition': 'No', 'recommendation_amount': 20},
        
        # Tier 1 Cities - With Pre-existing
        {'age_group': '25-35', 'city_tier': 'Tier 1', 'pre_existing_condition': 'Yes', 'recommendation_amount': 15},
        {'age_group': '36-45', 'city_tier': 'Tier 1', 'pre_existing_condition': 'Yes', 'recommendation_amount': 20},
        {'age_group': '45+', 'city_tier': 'Tier 1', 'pre_existing_condition': 'Yes', 'recommendation_amount': 25},
        
        # Other Cities - No Pre-existing
        {'age_group': '25-35', 'city_tier': 'Others', 'pre_existing_condition': 'No', 'recommendation_amount': 7},
        {'age_group': '36-45', 'city_tier': 'Others', 'pre_existing_condition': 'No', 'recommendation_amount': 10},
        {'age_group': '45+', 'city_tier': 'Others', 'pre_existing_condition': 'No', 'recommendation_amount': 15},
        
        # Other Cities - With Pre-existing
        {'age_group': '25-35', 'city_tier': 'Others', 'pre_existing_condition': 'Yes', 'recommendation_amount': 10},
        {'age_group': '36-45', 'city_tier': 'Others', 'pre_existing_condition': 'Yes', 'recommendation_amount': 15},
        {'age_group': '45+', 'city_tier': 'Others', 'pre_existing_condition': 'Yes', 'recommendation_amount': 20},
    ]
    
    db.insurance_recommendations.insert_many(recommendations)
    print(f"Inserted {len(recommendations)} recommendations")
    
    # Create indexes
    db.insurance_recommendations.create_index([
        ('age_group', 1),
        ('city_tier', 1),
        ('pre_existing_condition', 1)
    ])
    print("Created indexes on recommendations collection")

if __name__ == "__main__":
    setup_recommendations()
    print("Insurance recommendations setup complete!")