from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flasgger import Swagger

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this in production!

    db.init_app(app)
    jwt.init_app(app)
    Swagger(app)

    with app.app_context():
        from .database.models import User, ServiceProvider, Availability, Appointment, Message, Feedback
        from .routes import init_routes
        
        init_routes(app)
        db.create_all()

    return app
