import os
import logging
from flask import Flask, render_template
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from backend.config import config


def create_app() -> Flask:
    app = Flask(__name__, template_folder='../templates')
    
    CORS(app)
    
    app.config['UPLOAD_FOLDER'] = config.upload_folder
    app.config['MAX_CONTENT_LENGTH'] = config.max_upload_size
    app.config['DEBUG'] = config.debug

    logging.basicConfig(
        level=getattr(logging, config.get('logging.level', 'INFO')),
        format=config.get('logging.format')
    )

    from backend.routes.summarize import summarize_bp
    app.register_blueprint(summarize_bp, url_prefix='/api/v1')

    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host=config.host, port=config.port, debug=config.debug)