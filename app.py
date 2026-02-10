import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///college_events.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models and routes
    import models  # noqa: F401
    import routes  # noqa: F401
    
    # Create all tables
    db.create_all()
    
    # Create default admin if not exists
    from models import Admin
    from werkzeug.security import generate_password_hash
    
    if not Admin.query.filter_by(username='admin').first():
        default_admin = Admin(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(default_admin)
        db.session.commit()
        logging.info("Default admin created: username='admin', password='admin123'")

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='127.0.0.1', port=5000, debug=True)

