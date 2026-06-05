from flask import Flask
import os
from datetime import timedelta

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dinex-super-secret-key-change-in-production')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session lasts 7 days
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    return app

