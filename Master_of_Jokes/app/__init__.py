from flask import Flask, render_template
from .auth import auth_bp
from .jokes import jokes_bp
from . import models

def register_commands(app):
    from .auth import init_moderator
    app.cli.add_command(init_moderator)


def create_app():
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['DATABASE'] = 'app/db.sqlite3'
    app.config['DEBUG'] = True  

    models.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(jokes_bp)

    @app.route('/')
    def index():
        return render_template('index.html')
    
    register_commands(app)

    return app


