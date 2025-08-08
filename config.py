import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # MongoDB Config
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/financial_planning'
    
    # Upload Config
    UPLOAD_FOLDER = 'static/uploads'
    PROFILE_UPLOAD_FOLDER = 'static/uploads/profiles'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Session Config
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # JWT Config
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # App Config
    ITEMS_PER_PAGE = 10
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}