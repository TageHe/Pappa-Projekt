from os import path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)

    # Set the path to the database in the website folder
    app.config['SECRET_KEY'] = 'magnus eskate'
    
    # Define absolute path for the database file inside the website folder
    database_path = path.join(path.dirname(__file__), DB_NAME)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # Register blueprints
    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    create_database(app)

    return app

def create_database(app):
    # Check if the database exists inside the website folder
    database_path = path.join(path.dirname(__file__), DB_NAME)
    if not path.exists(database_path):
        # Ensure the app context is available before creating the database
        with app.app_context():
            db.create_all()
        print(f"Created Database in the 'website' folder at {database_path}!")
