#!/bin/bash

# Create base folders
mkdir -p models controllers services templates/{auth,dashboard,users,plans,coupons} static/uploads/profiles static/css utils

# Create top-level files
touch app.py config.py requirements.txt

# Create __init__.py for Python packages
touch models/__init__.py
touch controllers/__init__.py
touch services/__init__.py
touch utils/__init__.py

# Create model files
touch models/user.py
touch models/plan.py
touch models/coupon.py

# Create controller files
touch controllers/auth_controller.py
touch controllers/user_controller.py
touch controllers/plan_controller.py
touch controllers/coupon_controller.py

# Create service files
touch services/auth_service.py
touch services/user_service.py
touch services/plan_service.py
touch services/coupon_service.py

# Create utility files
touch utils/decorators.py
touch utils/helpers.py

# Create template files
touch templates/base.html

# Auth templates
touch templates/auth/login.html
touch templates/auth/change_password.html

# Dashboard templates
touch templates/dashboard/admin_dashboard.html
touch templates/dashboard/agent_dashboard.html

# User templates
touch templates/users/list.html
touch templates/users/create.html
touch templates/users/profile.html

# Plan templates
touch templates/plans/list.html
touch templates/plans/create.html

# Coupon templates
touch templates/coupons/list.html
touch templates/coupons/create.html

# Static CSS file
touch static/css/custom.css

echo "✅ Project structure created successfully!"
