from flask import Flask
from config import Config
from flask_cors import CORS
from flask import g

from app.routes import info, process_code, files

def create_app(config_class = Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    @app.before_request
    def before_request():
        g.variables_dict = {}

    app.register_blueprint(info)
    app.register_blueprint(process_code)
    app.register_blueprint(files)

    return app
