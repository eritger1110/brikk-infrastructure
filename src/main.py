import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models.agent import db
from src.routes.user import user_bp
from src.routes.coordination import coordination_bp
from src.routes.security import security_bp
from src.routes.provision import provision_bp
from src.models.customer_profile import CustomerProfile
from src.routes.welcome import welcome_bp
app.register_blueprint(welcome_bp)

app = Flask(__name__, 
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))

# Enterprise configuration
app.config['SECRET_KEY'] = 'brikk_enterprise_secret_key_2024_production'
app.config['JWT_SECRET_KEY'] = 'brikk_jwt_secret_key_enterprise_2024'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # For demo purposes
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app, origins="*")  # Allow all origins for demo
jwt = JWTManager(app)
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(coordination_bp, url_prefix='/api')
app.register_blueprint(security_bp, url_prefix='/api')
app.register_blueprint(provision_bp)

# Health check endpoint
@app.route('/health')
def health_check():
    return {
        'service': 'Brikk Enterprise AI Agent Coordination Platform',
        'status': 'healthy',
        'version': '2.0.0',
        'environment': 'production',
        'features': [
            'Multi-language agent coordination',
            'Enterprise security & HIPAA compliance',
            'Real-time performance monitoring',
            'Comprehensive audit logging'
        ]
    }

# Main route - serve dark theme template
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Serve the dark theme template for the main page
    if path == '' or path == 'index.html':
        return render_template('index.html')
    
    # Serve static files for other paths
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        # Default to the dark theme template
        return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

