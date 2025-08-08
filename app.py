# app.py
# Main application file with enhanced routing for three-tier system

import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from config import config
from models.user import User
from models import get_users_collection
from datetime import datetime

# Import controllers
from controllers.auth_controller import auth_bp
from controllers.user_controller import users_bp
from controllers.plan_controller import plans_bp
from controllers.coupon_controller import coupons_bp
from controllers.dashboard_controller import dashboard_bp as dashboard_api_bp

# Import services
from services.auth_service import AuthService

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Create upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROFILE_UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        users = get_users_collection()
        user_data = users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(plans_bp, url_prefix='/plans')
    app.register_blueprint(coupons_bp, url_prefix='/coupons')
    # Register dashboard API blueprint without prefix for API routes
    app.register_blueprint(dashboard_api_bp)
    
    # Dashboard route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    @app.route('/dashboard')
    def dashboard():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Route to appropriate dashboard based on role
        if current_user.is_super_admin():
            return render_template('dashboard/super_admin_dashboard.html')
        elif current_user.is_partner():
            return render_template('dashboard/partner_dashboard.html')
        else:
            return render_template('dashboard/agent_dashboard.html')
    
    # Create dashboard blueprint for template routes
    from flask import Blueprint
    dashboard_bp = Blueprint('dashboard', __name__)
    
    @dashboard_bp.route('/')
    def index():
        if current_user.is_super_admin():
            return render_template('dashboard/super_admin_dashboard.html')
        elif current_user.is_partner():
            return render_template('dashboard/partner_dashboard.html')
        else:
            return render_template('dashboard/agent_dashboard.html')
    
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    # Context processor
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user, datetime=datetime)
    
    with app.app_context():
        # Create initial super admin account
        auth_service = AuthService()
        auth_service.create_initial_super_admin()
    
    return app

# Import ObjectId here to avoid circular imports
from bson import ObjectId

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    app.run(debug=True, host='0.0.0.0', port=5006)