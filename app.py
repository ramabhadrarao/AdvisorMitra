import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from config import config
from models.user import User
from models import get_users_collection

# Import controllers
from controllers.auth_controller import auth_bp
from controllers.user_controller import users_bp
from controllers.plan_controller import plans_bp
from controllers.coupon_controller import coupons_bp

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
        
        if current_user.is_owner() or current_user.is_admin():
            return render_template('dashboard/admin_dashboard.html')
        else:
            return render_template('dashboard/agent_dashboard.html')
    
    # Create dashboard blueprint
    from flask import Blueprint
    dashboard_bp = Blueprint('dashboard', __name__)
    
    @dashboard_bp.route('/')
    def index():
        if current_user.is_owner() or current_user.is_admin():
            return render_template('dashboard/admin_dashboard.html')
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
        return dict(current_user=current_user)
    
    with app.app_context():
        # Create initial owner account
        auth_service = AuthService()
        auth_service.create_initial_owner()
    
    return app

# Import ObjectId here to avoid circular imports
from bson import ObjectId

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    app.run(debug=True, host='0.0.0.0', port=5000)